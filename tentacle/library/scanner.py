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

"""Library Scanner for TV Shows and Episodes."""

from __future__ import annotations

import os
from typing import List, Tuple

from tentacle.database import Database
from tentacle.library.parser import (
    extract_season_from_folder,
    is_media_file,
    is_sample_file,
    parse_season_episode,
)
from tentacle.models import Episode, Show, ShowStatus


class LibraryScanner:
    """Scans local media folders for TV shows and episodes."""

    def __init__(self, db: Database) -> None:
        self.db = db

    def scan_all(self) -> List[Show]:
        """Perform a full scan of the shows directory."""
        settings = self.db.get_settings()
        shows_dir = os.path.abspath(settings.shows_dir)

        if not os.path.exists(shows_dir):
            os.makedirs(shows_dir, exist_ok=True)
            self.db.log("INFO", "scanner", f"Created shows directory at {shows_dir}")
            return []

        self.db.log("INFO", "scanner", f"Starting library scan in {shows_dir}...")
        scanned_shows: List[Show] = []

        try:
            entries = sorted(os.listdir(shows_dir))
        except OSError as e:
            self.db.log("ERROR", "scanner", f"Failed reading shows directory {shows_dir}: {e}")
            return []

        for entry in entries:
            full_path = os.path.join(shows_dir, entry)
            if not os.path.isdir(full_path):
                continue
            if entry.startswith("."):
                continue

            show = self.scan_show_directory(entry, full_path)
            if show:
                scanned_shows.append(show)

        self.db.log(
            "INFO",
            "scanner",
            f"Library scan complete: indexed {len(scanned_shows)} show(s).",
        )
        return scanned_shows

    def scan_show_directory(self, show_name: str, show_path: str) -> Show:
        """Scan a single show directory, detect dead.txt marker, and index episodes."""
        # 1. Check for dead.txt ("hes dead jim")
        dead_marker = os.path.join(show_path, "dead.txt")
        is_dead = os.path.exists(dead_marker)

        # Check existing show status in DB (user might have manually set it to ended in WebUI)
        existing_show = self.db.get_show_by_name(show_name)
        if is_dead:
            status = ShowStatus.ENDED
        elif existing_show and existing_show.status == ShowStatus.ENDED:
            status = ShowStatus.ENDED
        else:
            status = ShowStatus.ACTIVE

        # 2. Walk directory to find media files
        discovered_episodes: List[Episode] = []

        for root, dirs, files in os.walk(show_path):
            # Sort files for deterministic processing
            files.sort()
            for filename in files:
                if not is_media_file(filename):
                    continue

                filepath = os.path.join(root, filename)
                if is_sample_file(filepath):
                    continue

                # Try to parse season & episode
                parsed = parse_season_episode(filename)
                if not parsed:
                    # Check enclosing directory for season (e.g., Season 01/ep01.mkv)
                    parent_dir = os.path.basename(root)
                    s = extract_season_from_folder(parent_dir)
                    if s is not None:
                        # Try to find episode number in filename
                        parsed = parse_season_episode(f"S{s:02d} {filename}")

                if parsed:
                    season, ep = parsed
                    try:
                        size = os.path.getsize(filepath)
                    except OSError:
                        size = 0

                    discovered_episodes.append(
                        Episode(
                            season=season,
                            episode=ep,
                            file_name=filename,
                            file_path=filepath,
                            file_size=size,
                        )
                    )

        # 3. Compute newest episode
        newest_s: int | None = None
        newest_e: int | None = None
        if discovered_episodes:
            sorted_eps = sorted(
                discovered_episodes, key=lambda x: (x.season, x.episode)
            )
            newest_s = sorted_eps[-1].season
            newest_e = sorted_eps[-1].episode

        # 4. Upsert show in database
        show = self.db.upsert_show(
            name=show_name,
            path=show_path,
            status=status,
            newest_season=newest_s,
            newest_episode=newest_e,
            episode_count=len(discovered_episodes),
        )

        # 5. Sync episodes table
        if show.id is not None:
            self.db.sync_episodes_for_show(show.id, discovered_episodes)

        return self.db.get_show(show.id)  # type: ignore
