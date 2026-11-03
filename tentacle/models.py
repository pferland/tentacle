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

"""Domain models and schemas for Tentacle V4."""

from __future__ import annotations

import os
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ShowStatus(str, Enum):
    ACTIVE = "active"
    ENDED = "ended"


class DownloadStatus(str, Enum):
    QUEUED = "queued"
    DOWNLOADING = "downloading"
    COMPLETED = "completed"
    IMPORTED = "imported"
    FAILED = "failed"


class DownloaderType(str, Enum):
    SABNZBD = "sabnzbd"
    BLACKHOLE = "blackhole"


class IndexerType(str, Enum):
    NEWZNAB = "newznab"
    TORZNAB = "torznab"
    EASYNEWS = "easynews"


class Episode(BaseModel):
    id: Optional[int] = None
    show_id: Optional[int] = None
    season: int
    episode: int
    file_name: str
    file_path: str
    file_size: int = 0
    discovered_at: Optional[str] = None


class Show(BaseModel):
    id: Optional[int] = None
    name: str
    path: str
    status: ShowStatus = ShowStatus.ACTIVE
    newest_season: Optional[int] = None
    newest_episode: Optional[int] = None
    episode_count: int = 0
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class IndexerConfig(BaseModel):
    id: Optional[int] = None
    name: str
    type: IndexerType = IndexerType.NEWZNAB
    url: str
    api_key: str = ""
    category_id: str = "5000,5030,5040"  # Standard TV categories in Newznab
    enabled: bool = True
    priority: int = 1


class IndexerSearchResult(BaseModel):
    title: str
    link: str
    indexer_name: str
    size: int = 0
    pub_date: Optional[str] = None
    season: Optional[int] = None
    episode: Optional[int] = None
    guid: Optional[str] = None


class DownloaderConfig(BaseModel):
    type: DownloaderType = DownloaderType.SABNZBD
    host: str = "127.0.0.1"
    port: int = 8080
    api_key: str = ""
    url_base: str = ""
    use_ssl: bool = False
    watch_dir: str = "./downloads/watch"
    completed_dir: str = "./downloads/completed"


class AppSettings(BaseModel):
    shows_dir: str = "./media/Shows"
    watch_dir: str = "./downloads/watch"
    completed_dir: str = "./downloads/completed"
    temp_dir: str = "./downloads/tmp"
    playlist_asx_path: str = "./Shows.asx"
    playlist_m3u8_path: str = "./Shows.m3u8"
    scan_interval: int = 3600  # seconds between periodic scans (1 hour default)
    failed_prefix: str = "_FAILED_"
    web_host: str = "0.0.0.0"
    web_port: int = 8080
    auto_search_missing: bool = True
    downloader: DownloaderConfig = Field(default_factory=DownloaderConfig)

    def normalize_paths(self) -> None:
        """Resolve absolute paths for directories."""
        self.shows_dir = os.path.abspath(self.shows_dir)
        self.watch_dir = os.path.abspath(self.watch_dir)
        self.completed_dir = os.path.abspath(self.completed_dir)
        self.temp_dir = os.path.abspath(self.temp_dir)
        self.playlist_asx_path = os.path.abspath(self.playlist_asx_path)
        self.playlist_m3u8_path = os.path.abspath(self.playlist_m3u8_path)


class DownloadRecord(BaseModel):
    id: Optional[int] = None
    show_name: str
    season: int
    episode: int
    title: str
    indexer_name: str
    nzb_url: str
    status: DownloadStatus = DownloadStatus.QUEUED
    downloader_id: Optional[str] = None
    error_message: Optional[str] = None
    created_at: Optional[str] = None
    completed_at: Optional[str] = None


class LogEntry(BaseModel):
    id: Optional[int] = None
    timestamp: str
    level: str = "INFO"
    category: str = "system"
    message: str


class DaemonStatus(BaseModel):
    running: bool
    state: str  # IDLE, SCANNING, SEARCHING, DOWNLOADING, ORGANIZING
    last_scan: Optional[str] = None
    next_scan: Optional[str] = None
    total_shows: int = 0
    active_shows: int = 0
    total_episodes: int = 0
    pending_downloads: int = 0
    configured_indexers: int = 0
