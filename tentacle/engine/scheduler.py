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

"""Daemon Scheduler & Background Engine for Tentacle V4."""

from __future__ import annotations

import asyncio
import logging
import threading
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from tentacle.database import Database
from tentacle.downloader.manager import DownloaderManager
from tentacle.indexer.manager import IndexerManager
from tentacle.library.organizer import MediaOrganizer
from tentacle.library.playlist import PlaylistGenerator
from tentacle.library.scanner import LibraryScanner
from tentacle.models import DaemonStatus, DownloadStatus, ShowStatus

logger = logging.getLogger("tentacle.scheduler")


class SchedulerEngine:
    """Coordinates library scanning, missing episode searches, downloads, and post-processing."""

    def __init__(self, db: Database) -> None:
        self.db = db
        self.scanner = LibraryScanner(db)
        self.organizer = MediaOrganizer(db)
        self.playlist = PlaylistGenerator(db)
        self.indexer_manager = IndexerManager(db)

        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._manual_trigger = threading.Event()

        self.current_state = "IDLE"
        self.last_scan_time: Optional[str] = None
        self.next_scan_time: Optional[str] = None

    def start(self) -> None:
        """Start the background daemon loop in a dedicated worker thread."""
        if self._running:
            return
        self._running = True
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run_loop, daemon=True, name="tentacle-daemon")
        self._thread.start()
        self.db.log("INFO", "daemon", "Tentacle V4 background daemon engine started.")

    def stop(self) -> None:
        """Gracefully stop the background daemon."""
        if not self._running:
            return
        self._running = False
        self._stop_event.set()
        self._manual_trigger.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=5.0)
        self.current_state = "STOPPED"
        self.db.log("INFO", "daemon", "Tentacle V4 background daemon stopped.")

    def trigger_cycle_now(self) -> None:
        """Immediately wake the background daemon and run a full cycle."""
        self._manual_trigger.set()

    def get_status(self) -> DaemonStatus:
        """Fetch current daemon runtime health and stats."""
        shows = self.db.get_shows()
        active_shows = [s for s in shows if s.status == ShowStatus.ACTIVE]
        episodes = self.db.get_episodes()
        pending = self.db.get_downloads(status=DownloadStatus.QUEUED)
        indexers = self.db.get_indexers(enabled_only=True)

        return DaemonStatus(
            running=self._running,
            state=self.current_state,
            last_scan=self.last_scan_time,
            next_scan=self.next_scan_time,
            total_shows=len(shows),
            active_shows=len(active_shows),
            total_episodes=len(episodes),
            pending_downloads=len(pending),
            configured_indexers=len(indexers),
        )

    def _run_loop(self) -> None:
        """Daemon worker thread event loop."""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        while not self._stop_event.is_set():
            try:
                loop.run_until_complete(self.run_full_cycle())
            except Exception as e:
                self.db.log("ERROR", "daemon", f"Unhandled error in daemon cycle: {e}")

            settings = self.db.get_settings()
            interval = max(60, settings.scan_interval)
            next_ts = time.time() + interval
            self.next_scan_time = datetime.fromtimestamp(next_ts, tz=timezone.utc).isoformat()
            self.current_state = "IDLE"

            # Sleep until interval expires or manual trigger received
            triggered = self._manual_trigger.wait(timeout=interval)
            if triggered:
                self._manual_trigger.clear()

        loop.close()

    async def run_full_cycle(self) -> None:
        """Execute one complete processing pass."""
        now_str = datetime.now(timezone.utc).isoformat()
        self.last_scan_time = now_str

        # 1. Scan Library
        self.current_state = "SCANNING"
        self.db.log("INFO", "engine", "Step 1/5: Scanning media library...")
        self.scanner.scan_all()

        # 2. Organize any already completed downloads
        self.current_state = "ORGANIZING"
        self.db.log("INFO", "engine", "Step 2/5: Processing completed downloads...")
        self.organizer.organize_completed()

        # 3. Check for missing episodes and search Usenet indexers
        settings = self.db.get_settings()
        if settings.auto_search_missing:
            self.current_state = "SEARCHING"
            self.db.log("INFO", "engine", "Step 3/5: Searching indexers for upcoming episodes...")
            await self.search_and_queue_missing_episodes()

        # 4. Monitor active downloader & post-process
        self.current_state = "DOWNLOADING"
        self.db.log("INFO", "engine", "Step 4/5: Checking downloader status...")
        await self.monitor_downloader_and_clean()

        # 5. Refresh playlists
        self.current_state = "PLAYLIST"
        self.db.log("INFO", "engine", "Step 5/5: Updating playlists...")
        self.playlist.generate_all()

        self.current_state = "IDLE"
        self.db.log("INFO", "engine", "Cycle completed successfully.")

    async def search_and_queue_missing_episodes(self) -> int:
        """For all active shows, search for the next episode(s)."""
        shows = self.db.get_shows()
        active_shows = [s for s in shows if s.status == ShowStatus.ACTIVE]
        queued_count = 0

        for show in active_shows:
            # If show has no episodes yet, start from S01E01
            current_s = show.newest_season if show.newest_season is not None else 1
            current_e = show.newest_episode if show.newest_episode is not None else 0

            # Target next episode in current season
            target_s = current_s
            target_e = current_e + 1

            # Check if this episode is already queued or imported
            existing = [
                d
                for d in self.db.get_downloads(limit=50)
                if d.show_name.lower() == show.name.lower()
                and d.season == target_s
                and d.episode == target_e
                and d.status in (DownloadStatus.QUEUED, DownloadStatus.DOWNLOADING, DownloadStatus.IMPORTED)
            ]
            if existing:
                continue

            results = await self.indexer_manager.search_episode(show.name, target_s, target_e)
            if not results and target_e > 1:
                # If next episode in current season wasn't found, check if new season started (S{s+1}E01)
                next_season_s = current_s + 1
                next_season_e = 1
                results = await self.indexer_manager.search_episode(
                    show.name, next_season_s, next_season_e
                )
                if results:
                    target_s = next_season_s
                    target_e = next_season_e

            if results:
                best_release = results[0]
                success = await self._dispatch_release(show.name, target_s, target_e, best_release)
                if success:
                    queued_count += 1

        return queued_count

    async def _dispatch_release(
        self, show_name: str, season: int, episode: int, release: Any
    ) -> bool:
        """Send release to configured downloader."""
        settings = self.db.get_settings()
        downloader = DownloaderManager.get_downloader(settings.downloader)

        # Record download in DB
        download_rec = self.db.record_download(
            show_name=show_name,
            season=season,
            episode=episode,
            title=release.title,
            indexer_name=release.indexer_name,
            nzb_url=release.link,
            status=DownloadStatus.QUEUED,
        )

        # Attempt sending by URL
        success, msg, job_id = await downloader.add_nzb_url(release.link, release.title)

        if not success:
            # Fallback: Download NZB bytes directly and upload/drop file
            nzb_bytes = await self.indexer_manager.download_nzb_bytes(
                release.link, release.indexer_name
            )
            if nzb_bytes:
                filename = f"{show_name} S{season:02d}E{episode:02d}.nzb"
                success, msg, job_id = await downloader.add_nzb_file(nzb_bytes, filename)

        if success and download_rec.id is not None:
            self.db.update_download_status(
                download_rec.id, DownloadStatus.DOWNLOADING, downloader_id=job_id
            )
            self.db.log(
                "INFO",
                "downloader",
                f"Queued download for {show_name} S{season:02d}E{episode:02d} ({release.title}): {msg}",
            )
            return True
        elif download_rec.id is not None:
            self.db.update_download_status(
                download_rec.id, DownloadStatus.FAILED, error_message=msg
            )
            self.db.log(
                "ERROR",
                "downloader",
                f"Failed dispatching {show_name} S{season:02d}E{episode:02d}: {msg}",
            )
            return False
        return False

    async def monitor_downloader_and_clean(self) -> None:
        """Wait briefly for downloader to finish active jobs, then organize."""
        settings = self.db.get_settings()
        downloader = DownloaderManager.get_downloader(settings.downloader)

        # Check if idle
        try:
            is_idle = await downloader.is_idle()
            if is_idle:
                self.organizer.organize_completed()
        except Exception as e:
            self.db.log("ERROR", "downloader", f"Error checking downloader status: {e}")
