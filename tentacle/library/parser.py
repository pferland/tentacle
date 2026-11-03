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

"""Episode filename parser and media filter."""

import os
import re
from typing import Optional, Tuple

MEDIA_EXTENSIONS = {
    ".mkv",
    ".mp4",
    ".avi",
    ".m4v",
    ".mov",
    ".wmv",
    ".ts",
    ".webm",
    ".flv",
}

IGNORED_EXTENSIONS = {
    ".nfo",
    ".sfv",
    ".par2",
    ".srr",
    ".srt",
    ".sub",
    ".idx",
    ".txt",
    ".jpg",
    ".jpeg",
    ".png",
    ".gif",
    ".tbn",
    ".db",
    ".lnk",
    ".torrent",
    ".nzb",
    ".zip",
    ".rar",
    ".ds_store",
}

EPISODE_PATTERNS = [
    # S01E02 or s1e2 or S01E02-E03
    re.compile(r"[sS](?P<season>\d{1,3})[eE](?P<episode>\d{1,3})"),
    # 1x02 or 01x02
    re.compile(r"(?:^|[\s._\-\[])(?P<season>\d{1,2})x(?P<episode>\d{1,3})(?:[\s._\-\]]|$)"),
    # Season 1 Episode 2
    re.compile(
        r"Season\s*(?P<season>\d{1,3})[^\d]+Episode\s*(?P<episode>\d{1,3})", re.IGNORECASE
    ),
]


def is_media_file(filename: str) -> bool:
    """Return True if filename has a recognized video media extension."""
    _, ext = os.path.splitext(filename)
    return ext.lower() in MEDIA_EXTENSIONS


def is_sample_file(filepath: str) -> bool:
    """Check if file is a video sample (contains 'sample' and is < 50MB)."""
    filename = os.path.basename(filepath).lower()
    if "sample" in filename:
        try:
            if os.path.getsize(filepath) < 50 * 1024 * 1024:
                return True
        except OSError:
            pass
    return False


def parse_season_episode(text: str) -> Optional[Tuple[int, int]]:
    """Extract (season, episode) tuple from filename or directory name."""
    for pattern in EPISODE_PATTERNS:
        match = pattern.search(text)
        if match:
            s = int(match.group("season"))
            e = int(match.group("episode"))
            return s, e
    return None


def extract_season_from_folder(folder_name: str) -> Optional[int]:
    """Parse season number from folder names like 'Season 1', 'Season 02', 'S1'."""
    match = re.search(r"(?:Season|S)[\s._\-]*(\d{1,3})", folder_name, re.IGNORECASE)
    if match:
        return int(match.group(1))
    return None
