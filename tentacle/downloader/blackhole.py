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

"""Blackhole (Watch Directory) Downloader."""

from __future__ import annotations

import os
import re
from typing import Any, Dict, Optional, Tuple

from tentacle.downloader.base import BaseDownloader
from tentacle.models import DownloaderConfig


class BlackholeDownloader(BaseDownloader):
    """Downloader that saves NZBs to a watch folder for external clients."""

    def __init__(self, config: DownloaderConfig) -> None:
        self.config = config
        self.watch_dir = os.path.abspath(config.watch_dir)
        self.completed_dir = os.path.abspath(config.completed_dir)
        os.makedirs(self.watch_dir, exist_ok=True)
        os.makedirs(self.completed_dir, exist_ok=True)

    async def check_connection(self) -> Tuple[bool, str]:
        """Verify that watch and completed directories exist and are writable."""
        if not os.path.exists(self.watch_dir):
            return False, f"Watch directory does not exist: {self.watch_dir}"
        if not os.access(self.watch_dir, os.W_OK):
            return False, f"Watch directory is not writable: {self.watch_dir}"
        if not os.path.exists(self.completed_dir):
            return False, f"Completed directory does not exist: {self.completed_dir}"
        return True, f"Blackhole directory accessible at {self.watch_dir}"

    async def add_nzb_url(
        self, url: str, title: str, category: str = "tv"
    ) -> Tuple[bool, str, Optional[str]]:
        """Blackhole requires file payload; cannot directly accept raw URL."""
        return False, "Blackhole downloader requires NZB payload bytes, URL not supported directly", None

    async def add_nzb_file(
        self, file_bytes: bytes, filename: str, category: str = "tv"
    ) -> Tuple[bool, str, Optional[str]]:
        """Write NZB file directly to the blackhole watch folder."""
        # Sanitize filename
        safe_name = re.sub(r'[\\/*?:"<>|]', "", filename)
        if not safe_name.lower().endswith(".nzb"):
            safe_name += ".nzb"

        dest_path = os.path.join(self.watch_dir, safe_name)
        try:
            with open(dest_path, "wb") as f:
                f.write(file_bytes)
            return True, f"NZB dropped into watch directory: {safe_name}", safe_name
        except Exception as e:
            return False, f"Failed writing NZB to watch directory: {str(e)}", None

    async def is_idle(self) -> bool:
        """Idle when no .nzb files remain in the watch directory."""
        if not os.path.exists(self.watch_dir):
            return True
        nzb_files = [f for f in os.listdir(self.watch_dir) if f.lower().endswith(".nzb")]
        return len(nzb_files) == 0

    async def get_queue_status(self) -> Dict[str, Any]:
        """Queue status based on pending NZBs in watch directory."""
        if not os.path.exists(self.watch_dir):
            return {"status": "IDLE", "slots": []}
        nzb_files = [f for f in os.listdir(self.watch_dir) if f.lower().endswith(".nzb")]
        return {
            "status": "DOWNLOADING" if nzb_files else "IDLE",
            "slots": [{"filename": f} for f in nzb_files],
        }
