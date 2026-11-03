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

"""SABnzbd Downloader Client."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple
import httpx

from tentacle.downloader.base import BaseDownloader
from tentacle.models import DownloaderConfig


class SabnzbdDownloader(BaseDownloader):
    """Client for SABnzbd JSON API."""

    def __init__(self, config: DownloaderConfig, timeout: float = 15.0) -> None:
        self.config = config
        self.timeout = timeout
        proto = "https" if config.use_ssl else "http"
        base_path = config.url_base.strip("/")
        if base_path:
            self.api_url = f"{proto}://{config.host}:{config.port}/{base_path}/api"
        else:
            self.api_url = f"{proto}://{config.host}:{config.port}/api"

    async def check_connection(self) -> Tuple[bool, str]:
        """Verify connection to SABnzbd."""
        params = {
            "mode": "version",
            "output": "json",
            "apikey": self.config.api_key,
        }
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.get(self.api_url, params=params)
                if resp.status_code == 200:
                    data = resp.json()
                    version = data.get("version", "Unknown")
                    return True, f"Connected to SABnzbd v{version}"
                elif resp.status_code in (401, 403):
                    return False, "SABnzbd authentication failed: Invalid API key"
                else:
                    return False, f"SABnzbd returned HTTP {resp.status_code}"
        except httpx.ConnectError:
            return False, f"Cannot connect to SABnzbd at {self.api_url}"
        except Exception as e:
            return False, f"Connection error: {str(e)}"

    async def add_nzb_url(
        self, url: str, title: str, category: str = "tv"
    ) -> Tuple[bool, str, Optional[str]]:
        """Submit NZB download URL to SABnzbd."""
        params = {
            "mode": "addurl",
            "name": url,
            "nzbname": title,
            "cat": category,
            "output": "json",
            "apikey": self.config.api_key,
        }
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.get(self.api_url, params=params)
                if resp.status_code == 200:
                    data = resp.json()
                    if data.get("status") is True or "nzo_ids" in data:
                        nzo_ids = data.get("nzo_ids", [])
                        nzo_id = nzo_ids[0] if nzo_ids else None
                        return True, "NZB URL added to SABnzbd queue", nzo_id
                    return False, f"SABnzbd rejected NZB: {data}", None
                return False, f"SABnzbd error HTTP {resp.status_code}", None
        except Exception as e:
            return False, f"Error adding NZB URL to SABnzbd: {str(e)}", None

    async def add_nzb_file(
        self, file_bytes: bytes, filename: str, category: str = "tv"
    ) -> Tuple[bool, str, Optional[str]]:
        """Upload NZB file to SABnzbd."""
        params = {
            "mode": "addfile",
            "cat": category,
            "output": "json",
            "apikey": self.config.api_key,
        }
        files = {"nzbfile": (filename, file_bytes, "application/x-nzb")}
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.post(self.api_url, params=params, files=files)
                if resp.status_code == 200:
                    data = resp.json()
                    if data.get("status") is True or "nzo_ids" in data:
                        nzo_ids = data.get("nzo_ids", [])
                        nzo_id = nzo_ids[0] if nzo_ids else None
                        return True, "NZB file uploaded to SABnzbd", nzo_id
                    return False, f"SABnzbd rejected file: {data}", None
                return False, f"SABnzbd error HTTP {resp.status_code}", None
        except Exception as e:
            return False, f"Error uploading NZB to SABnzbd: {str(e)}", None

    async def is_idle(self) -> bool:
        """Check if SABnzbd has finished all queued downloads."""
        status = await self.get_queue_status()
        state = status.get("status", "").upper()
        slots = status.get("slots", [])
        return state in ("IDLE", "") and len(slots) == 0

    async def get_queue_status(self) -> Dict[str, Any]:
        """Fetch queue status from SABnzbd."""
        params = {
            "mode": "queue",
            "output": "json",
            "apikey": self.config.api_key,
        }
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.get(self.api_url, params=params)
                if resp.status_code == 200:
                    data = resp.json()
                    return data.get("queue", {})
        except Exception:
            pass
        return {"status": "UNKNOWN", "slots": []}

    async def get_history(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Fetch history of completed downloads from SABnzbd."""
        params = {
            "mode": "history",
            "output": "json",
            "limit": str(limit),
            "apikey": self.config.api_key,
        }
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.get(self.api_url, params=params)
                if resp.status_code == 200:
                    data = resp.json()
                    return data.get("history", {}).get("slots", [])
        except Exception:
            pass
        return []
