#    Tentacle V4 - The Automated TV Show Tracker, Downloader & Media Organizer
#    Copyright (C) 2010-2026
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""Newznab API Client for Usenet Indexers."""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from typing import Any, Dict, List, Optional, Tuple
import httpx

from tentacle.models import IndexerConfig, IndexerSearchResult


class NewznabClient:
    """Client for Newznab-compatible indexers."""

    def __init__(self, config: IndexerConfig, timeout: float = 15.0) -> None:
        self.config = config
        self.timeout = timeout
        self.base_url = config.url.rstrip("/")
        if not self.base_url.endswith("/api"):
            # If user provided base domain without /api, append it
            self.api_url = f"{self.base_url}/api"
        else:
            self.api_url = self.base_url

    async def test_connection(self) -> Tuple[bool, str]:
        """Test indexer connectivity and API key validity."""
        params = {
            "t": "caps",
            "apikey": self.config.api_key,
        }
        try:
            async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=True) as client:
                resp = await client.get(self.api_url, params=params)
                if resp.status_code == 200:
                    text = resp.text.lower()
                    if "error code" in text or "incorrect user credentials" in text:
                        return False, f"API Key rejected: {resp.text[:120]}"
                    return True, "Connection successful! Server responded with capabilities."
                elif resp.status_code == 401 or resp.status_code == 403:
                    return False, f"Authentication failed (HTTP {resp.status_code}): Invalid API Key."
                else:
                    return False, f"HTTP Error {resp.status_code}: {resp.text[:100]}"
        except httpx.ConnectError:
            return False, f"Cannot connect to host: {self.api_url}"
        except httpx.TimeoutException:
            return False, f"Connection timed out after {self.timeout}s"
        except Exception as e:
            return False, f"Connection error: {str(e)}"

    async def search_episode(
        self, show_name: str, season: int, episode: int
    ) -> List[IndexerSearchResult]:
        """Search for a specific episode using tvsearch and text search fallback."""
        results: List[IndexerSearchResult] = []

        # 1. First attempt: dedicated tvsearch
        params = {
            "t": "tvsearch",
            "q": show_name,
            "season": str(season),
            "ep": str(episode),
            "cat": self.config.category_id,
            "apikey": self.config.api_key,
            "o": "json",
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=True) as client:
                resp = await client.get(self.api_url, params=params)
                if resp.status_code == 200:
                    results = self._parse_json_or_xml(resp.text, season, episode)
        except Exception:
            results = []

        if results:
            return results

        # 2. Second attempt: standard search with formatted query (e.g., "Show S01E02")
        query_str = f"{show_name} S{season:02d}E{episode:02d}"
        fallback_params = {
            "t": "search",
            "q": query_str,
            "cat": self.config.category_id,
            "apikey": self.config.api_key,
            "o": "json",
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=True) as client:
                resp = await client.get(self.api_url, params=fallback_params)
                if resp.status_code == 200:
                    results = self._parse_json_or_xml(resp.text, season, episode)
        except Exception:
            results = []

        return results

    async def download_nzb(self, url: str) -> bytes:
        """Download NZB payload bytes from the given link."""
        # Ensure apikey is appended if link points to indexer API without it
        dl_url = url
        if self.config.api_key and "apikey=" not in dl_url and self.base_url in dl_url:
            separator = "&" if "?" in dl_url else "?"
            dl_url = f"{dl_url}{separator}apikey={self.config.api_key}"

        async with httpx.AsyncClient(timeout=self.timeout * 2, follow_redirects=True) as client:
            resp = await client.get(dl_url)
            resp.raise_for_status()
            return resp.content

    def _parse_json_or_xml(
        self, text: str, season: int, episode: int
    ) -> List[IndexerSearchResult]:
        """Attempt to parse response as JSON; fallback to XML RSS."""
        results: List[IndexerSearchResult] = []
        text = text.strip()

        # Try JSON first
        if text.startswith("{"):
            try:
                import json

                data = json.loads(text)
                channel = data.get("channel", {})
                items = channel.get("item", [])
                if isinstance(items, dict):
                    items = [items]
                for item in items:
                    title = item.get("title", "")
                    link = item.get("link", "") or item.get("enclosure", {}).get(
                        "@attributes", {}
                    ).get("url", "")
                    size = int(
                        item.get("size", 0)
                        or item.get("enclosure", {}).get("@attributes", {}).get("length", 0)
                        or 0
                    )
                    if title and link:
                        results.append(
                            IndexerSearchResult(
                                title=title,
                                link=link,
                                indexer_name=self.config.name,
                                size=size,
                                pub_date=item.get("pubDate"),
                                season=season,
                                episode=episode,
                                guid=str(item.get("guid")),
                            )
                        )
                if results:
                    return results
            except Exception:
                pass

        # Try XML RSS / Newznab
        try:
            root = ET.fromstring(text)
            for item in root.findall(".//item"):
                title_elem = item.find("title")
                link_elem = item.find("link")
                enclosure_elem = item.find("enclosure")
                pub_date_elem = item.find("pubDate")
                guid_elem = item.find("guid")

                title = title_elem.text if title_elem is not None and title_elem.text else ""
                link = ""
                size = 0

                if link_elem is not None and link_elem.text:
                    link = link_elem.text
                elif enclosure_elem is not None and "url" in enclosure_elem.attrib:
                    link = enclosure_elem.attrib["url"]

                if enclosure_elem is not None and "length" in enclosure_elem.attrib:
                    try:
                        size = int(enclosure_elem.attrib.get("length", 0))
                    except (ValueError, TypeError):
                        pass

                # Check newznab:attr tags for size
                for attr in item.findall(
                    "{http://www.newznab.com/DTD/2010/feeds/attributes/}attr"
                ):
                    if attr.attrib.get("name") == "size":
                        try:
                            size = int(attr.attrib.get("value", 0))
                        except Exception:
                            pass

                if title and link:
                    results.append(
                        IndexerSearchResult(
                            title=title,
                            link=link,
                            indexer_name=self.config.name,
                            size=size,
                            pub_date=pub_date_elem.text if pub_date_elem is not None else None,
                            season=season,
                            episode=episode,
                            guid=guid_elem.text if guid_elem is not None else None,
                        )
                    )
        except Exception:
            pass

        return results
