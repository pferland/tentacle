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

"""Abstract Base Class for Downloaders."""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Tuple


class BaseDownloader(ABC):
    """Abstract downloader interface."""

    @abstractmethod
    async def check_connection(self) -> Tuple[bool, str]:
        """Test downloader connectivity."""
        pass

    @abstractmethod
    async def add_nzb_url(
        self, url: str, title: str, category: str = "tv"
    ) -> Tuple[bool, str, Optional[str]]:
        """Add NZB by URL. Returns (success, message, downloader_job_id)."""
        pass

    @abstractmethod
    async def add_nzb_file(
        self, file_bytes: bytes, filename: str, category: str = "tv"
    ) -> Tuple[bool, str, Optional[str]]:
        """Add NZB by file payload. Returns (success, message, downloader_job_id)."""
        pass

    @abstractmethod
    async def is_idle(self) -> bool:
        """Check if downloader queue is idle/finished."""
        pass

    @abstractmethod
    async def get_queue_status(self) -> Dict[str, Any]:
        """Retrieve queue information."""
        pass
