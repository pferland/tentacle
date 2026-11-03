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

"""Downloader Manager."""

from typing import Tuple

from tentacle.downloader.base import BaseDownloader
from tentacle.downloader.blackhole import BlackholeDownloader
from tentacle.downloader.sabnzbd import SabnzbdDownloader
from tentacle.models import DownloaderConfig, DownloaderType


class DownloaderManager:
    """Factory and manager for downloaders."""

    @staticmethod
    def get_downloader(config: DownloaderConfig) -> BaseDownloader:
        if config.type == DownloaderType.BLACKHOLE:
            return BlackholeDownloader(config)
        return SabnzbdDownloader(config)

    @classmethod
    async def test_connection(cls, config: DownloaderConfig) -> Tuple[bool, str]:
        downloader = cls.get_downloader(config)
        return await downloader.check_connection()
