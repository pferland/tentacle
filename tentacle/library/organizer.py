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

"""Post-processing Media Organizer."""

from __future__ import annotations

import os
import re
import shutil
from typing import List, Optional, Tuple

from tentacle.database import Database
from tentacle.library.parser import (
    is_media_file,
    is_sample_file,
    parse_season_episode,
)
from tentacle.models import DownloadStatus


class MediaOrganizer:
    """Inspects completed downloads, moves media files into library, and cleans up."""

    def __init__(self, db: Database) -> None:
        self.db = db

    def organize_completed(self) -> int:
        """Process all completed downloads in completed_dir."""
        settings = self.db.get_settings()
        completed_dir = os.path.abspath(settings.completed_dir)
        shows_dir = os.path.abspath(settings.shows_dir)

        if not os.path.exists(completed_dir):
            return 0

        imported_count = 0
        try:
            entries = os.listdir(completed_dir)
        except OSError:
            return 0

        for entry in entries:
            # Skip failed marker folders
            if entry.startswith(settings.failed_prefix):
                self.db.log(
                    "WARNING",
                    "organizer",
                    f"Skipping failed download folder: {entry}",
                )
                continue

            entry_path = os.path.join(completed_dir, entry)

            # Case A: Downloaded item is a directory
            if os.path.isdir(entry_path):
                success = self._process_release_dir(entry, entry_path, shows_dir)
                if success:
                    imported_count += 1
            # Case B: Downloaded item is a standalone media file directly in completed_dir
            elif is_media_file(entry) and not is_sample_file(entry_path):
                success = self._process_standalone_file(entry, entry_path, shows_dir)
                if success:
                    imported_count += 1

        return imported_count

    def _process_release_dir(
        self, release_name: str, release_path: str, shows_dir: str
    ) -> bool:
        """Find video file in release directory, move to library, and remove directory."""
        media_file: Optional[str] = None
        max_size = 0

        for root, _, files in os.walk(release_path):
            for file in files:
                if is_media_file(file):
                    fp = os.path.join(root, file)
                    if is_sample_file(fp):
                        continue
                    try:
                        sz = os.path.getsize(fp)
                    except OSError:
                        sz = 0
                    if sz > max_size:
                        max_size = sz
                        media_file = fp

        if not media_file:
            self.db.log(
                "WARNING",
                "organizer",
                f"No valid media file found in release folder: {release_name}",
            )
            return False

        filename = os.path.basename(media_file)
        parsed = parse_season_episode(filename) or parse_season_episode(release_name)
        if not parsed:
            self.db.log(
                "WARNING",
                "organizer",
                f"Cannot determine Season/Episode for {release_name} ({filename})",
            )
            return False

        season, episode = parsed
        show_name = self._detect_show_name(release_name, filename)

        dest_dir = os.path.join(shows_dir, show_name, f"Season {season}")
        dest_path = os.path.join(dest_dir, filename)

        try:
            os.makedirs(dest_dir, exist_ok=True)
            if os.path.exists(dest_path):
                # File already exists, don't overwrite if existing is larger/same
                self.db.log(
                    "INFO",
                    "organizer",
                    f"File already exists in library: {dest_path}. Removing downloaded duplicate.",
                )
            else:
                shutil.move(media_file, dest_path)
                self.db.log(
                    "INFO",
                    "organizer",
                    f"Imported {filename} -> {dest_path}",
                )

            # Safely remove the unpacked release directory
            shutil.rmtree(release_path, ignore_errors=True)

            # Update download records in DB
            self._update_download_record(show_name, season, episode)
            return True
        except Exception as e:
            self.db.log(
                "ERROR",
                "organizer",
                f"Failed organizing release {release_name}: {str(e)}",
            )
            return False

    def _process_standalone_file(
        self, filename: str, filepath: str, shows_dir: str
    ) -> bool:
        """Process a standalone media file directly in completed_dir."""
        parsed = parse_season_episode(filename)
        if not parsed:
            return False

        season, episode = parsed
        show_name = self._detect_show_name(filename, filename)
        dest_dir = os.path.join(shows_dir, show_name, f"Season {season}")
        dest_path = os.path.join(dest_dir, filename)

        try:
            os.makedirs(dest_dir, exist_ok=True)
            shutil.move(filepath, dest_path)
            self.db.log("INFO", "organizer", f"Imported standalone {filename} -> {dest_path}")
            self._update_download_record(show_name, season, episode)
            return True
        except Exception as e:
            self.db.log("ERROR", "organizer", f"Failed organizing file {filename}: {e}")
            return False

    def _detect_show_name(self, release_name: str, filename: str) -> str:
        """Infer show name from release or file string, matching known library shows first."""
        known_shows = {s.name.lower(): s.name for s in self.db.get_shows()}

        # 1. Clean release title
        clean = re.sub(r"[._+]", " ", release_name)
        # Match against known shows
        for lower_name, exact_name in known_shows.items():
            if lower_name in clean.lower():
                return exact_name

        # 2. Extract title before SxxExx
        match = re.search(r"^(.*?)(?:[sS]\d{1,3}[eE]\d{1,3}|\d{1,2}x\d{1,3})", clean)
        if match:
            candidate = match.group(1).strip()
            # Clean common release artifacts (years, resolution)
            candidate = re.sub(r"\b(19\d\d|20\d\d)\b.*", "", candidate).strip()
            if candidate:
                return candidate.title()

        return "Unknown Shows"

    def _update_download_record(self, show_name: str, season: int, episode: int) -> None:
        """Mark corresponding download record as IMPORTED in database."""
        downloads = self.db.get_downloads(limit=50)
        for d in downloads:
            if (
                d.show_name.lower() == show_name.lower()
                and d.season == season
                and d.episode == episode
                and d.status != DownloadStatus.IMPORTED
            ):
                if d.id is not None:
                    self.db.update_download_status(d.id, DownloadStatus.IMPORTED)
                break
