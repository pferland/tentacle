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

"""EasyNews Global Web Search Client."""

from __future__ import annotations

import base64
import xml.etree.ElementTree as ET
from typing import Any, Dict, List, Optional, Tuple
import httpx

from tentacle.models import IndexerConfig, IndexerSearchResult


class EasyNewsClient:
    """Client for EasyNews Web Search (Solr backend / RSS sS=5)."""

    def __init__(self, config: IndexerConfig, timeout: float = 20.0) -> None:
        self.config = config
        self.timeout = timeout
        self.api_url = config.url.rstrip("/")
        if not self.api_url or self.api_url == "https://":
            self.api_url = "https://members.easynews.com/2.0/search/solr-search/advanced"

        # Parse username and password from api_key field (format: "username:password")
        credentials = config.api_key.strip()
        if ":" in credentials:
            self.username, self.password = credentials.split(":", 1)
        else:
            self.username = credentials
            self.password = ""

    def _get_auth(self) -> Optional[Tuple[str, str]]:
        """Return HTTP Basic Auth tuple if credentials provided."""
        if self.username and self.password:
            return (self.username, self.password)
        return None

    async def test_connection(self) -> Tuple[bool, str]:
        """Test EasyNews credentials and connectivity."""
        if not self.username or not self.password:
            return (
                False,
                "EasyNews requires credentials. Enter your account details as 'username:password' in the API Key field.",
            )

        test_params = {
            "st": "adv",
            "safeO": "1",
            "pby": "1",
            "sS": "5",
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=True) as client:
                resp = await client.get(
                    self.api_url, params=test_params, auth=self._get_auth()
                )
                if resp.status_code == 200:
                    text = resp.text.lower()
                    if "<rss" in text or "<channel>" in text or "<html" in text:
                        return True, f"Successfully authenticated with EasyNews as '{self.username}'."
                    return False, f"Unexpected response from EasyNews: {resp.text[:120]}"
                elif resp.status_code in (401, 403):
                    return False, "EasyNews authentication failed: Invalid username or password."
                else:
                    return False, f"EasyNews returned HTTP {resp.status_code}: {resp.text[:100]}"
        except httpx.ConnectError:
            return False, f"Cannot connect to EasyNews host: {self.api_url}"
        except httpx.TimeoutException:
            return False, f"Connection to EasyNews timed out after {self.timeout}s"
        except Exception as e:
            return False, f"EasyNews connection error: {str(e)}"

    async def search_episode(
        self, show_name: str, season: int, episode: int
    ) -> List[IndexerSearchResult]:
        """Search EasyNews for a specific TV episode."""
        if not self.username or not self.password:
            return []

        # Formulate search queries: SxxExx and alternative
        query = f"{show_name} S{season:02d}E{episode:02d}"

        params = {
            "st": "adv",
            "safeO": "1",
            "sb": "1",  # search in subject
            "sS": "5",  # RSS XML output format
            "fex": "mkv,mp4,avi",  # filter by video extensions
            "fty[]": "VIDEO",  # file type video
            "pby": "50",  # limit
            "s1": "dsize",  # sort by size descending
            "s1d": "-",
            "q": query,
        }

        results: List[IndexerSearchResult] = []
        try:
            async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=True) as client:
                resp = await client.get(self.api_url, params=params, auth=self._get_auth())
                if resp.status_code == 200:
                    results = self._parse_rss_results(resp.text, season, episode)
        except Exception:
            results = []

        # Fallback search if SxxExx query returns empty: try without leading zeroes (e.g. S1E2 or 1x02)
        if not results:
            alt_query = f"{show_name} {season}x{episode:02d}"
            params["q"] = alt_query
            try:
                async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=True) as client:
                    resp = await client.get(self.api_url, params=params, auth=self._get_auth())
                    if resp.status_code == 200:
                        results = self._parse_rss_results(resp.text, season, episode)
            except Exception:
                pass

        return results

    async def download_file(self, url: str) -> bytes:
        """Download file content from EasyNews with Basic Auth."""
        async with httpx.AsyncClient(timeout=self.timeout * 3, follow_redirects=True) as client:
            resp = await client.get(url, auth=self._get_auth())
            resp.raise_for_status()
            return resp.content

    def _parse_rss_results(
        self, xml_text: str, season: int, episode: int
    ) -> List[IndexerSearchResult]:
        """Parse EasyNews RSS (sS=5) XML feed."""
        results: List[IndexerSearchResult] = []
        try:
            root = ET.fromstring(xml_text)
            for item in root.findall(".//item"):
                title_elem = item.find("title")
                link_elem = item.find("link")
                enclosure_elem = item.find("enclosure")
                pub_date_elem = item.find("pubDate")
                guid_elem = item.find("guid")

                title = title_elem.text.strip() if title_elem is not None and title_elem.text else ""
                link = ""
                size = 0

                if enclosure_elem is not None and "url" in enclosure_elem.attrib:
                    link = enclosure_elem.attrib["url"]
                    try:
                        size = int(enclosure_elem.attrib.get("length", 0))
                    except (ValueError, TypeError):
                        size = 0
                elif link_elem is not None and link_elem.text:
                    link = link_elem.text.strip()

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
