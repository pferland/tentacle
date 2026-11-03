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

"""SQLite Database layer for Tentacle V4."""

from __future__ import annotations

import json
import os
import sqlite3
import threading
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from tentacle.models import (
    AppSettings,
    DownloadRecord,
    DownloadStatus,
    Episode,
    IndexerConfig,
    IndexerType,
    LogEntry,
    Show,
    ShowStatus,
)


class Database:
    """Thread-safe SQLite database manager for Tentacle."""

    def __init__(self, db_path: str = "tentacle.db") -> None:
        self.db_path = os.path.abspath(db_path)
        self._local = threading.local()
        self._lock = threading.Lock()
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        """Get thread-local SQLite connection."""
        if not hasattr(self._local, "conn") or self._local.conn is None:
            conn = sqlite3.connect(self.db_path, check_same_thread=False)
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA journal_mode = WAL")
            conn.execute("PRAGMA foreign_keys = ON")
            self._local.conn = conn
        return self._local.conn

    def _init_db(self) -> None:
        """Create tables if they do not exist."""
        with self._lock:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()

            # Settings table
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                )
                """
            )

            # Shows table
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS shows (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE NOT NULL,
                    path TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'active',
                    newest_season INTEGER,
                    newest_episode INTEGER,
                    episode_count INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )

            # Episodes table
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS episodes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    show_id INTEGER NOT NULL,
                    season INTEGER NOT NULL,
                    episode INTEGER NOT NULL,
                    file_name TEXT NOT NULL,
                    file_path TEXT UNIQUE NOT NULL,
                    file_size INTEGER NOT NULL DEFAULT 0,
                    discovered_at TEXT NOT NULL,
                    FOREIGN KEY(show_id) REFERENCES shows(id) ON DELETE CASCADE
                )
                """
            )
            cur.execute(
                "CREATE INDEX IF NOT EXISTS idx_episodes_show_season_ep ON episodes(show_id, season, episode)"
            )

            # Indexers table
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS indexers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    type TEXT NOT NULL DEFAULT 'newznab',
                    url TEXT NOT NULL,
                    api_key TEXT NOT NULL DEFAULT '',
                    category_id TEXT NOT NULL DEFAULT '5000,5030,5040',
                    enabled INTEGER NOT NULL DEFAULT 1,
                    priority INTEGER NOT NULL DEFAULT 1
                )
                """
            )

            # Downloads table
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS downloads (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    show_name TEXT NOT NULL,
                    season INTEGER NOT NULL,
                    episode INTEGER NOT NULL,
                    title TEXT NOT NULL,
                    indexer_name TEXT NOT NULL,
                    nzb_url TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'queued',
                    downloader_id TEXT,
                    error_message TEXT,
                    created_at TEXT NOT NULL,
                    completed_at TEXT
                )
                """
            )
            cur.execute(
                "CREATE INDEX IF NOT EXISTS idx_downloads_status ON downloads(status)"
            )

            # Logs table
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    level TEXT NOT NULL,
                    category TEXT NOT NULL,
                    message TEXT NOT NULL
                )
                """
            )
            cur.execute(
                "CREATE INDEX IF NOT EXISTS idx_logs_timestamp ON logs(timestamp DESC)"
            )

            conn.commit()
            conn.close()

    # --- Settings ---

    def get_settings(self) -> AppSettings:
        """Fetch application settings or return default."""
        conn = self._get_connection()
        cur = conn.cursor()
        cur.execute("SELECT value FROM settings WHERE key = 'app_settings'")
        row = cur.fetchone()
        if row and row["value"]:
            try:
                data = json.loads(row["value"])
                return AppSettings(**data)
            except Exception:
                pass
        # Return and save defaults
        default_settings = AppSettings()
        self.save_settings(default_settings)
        return default_settings

    def save_settings(self, settings: AppSettings) -> None:
        """Persist application settings."""
        with self._lock:
            conn = self._get_connection()
            cur = conn.cursor()
            payload = settings.model_dump_json()
            cur.execute(
                "INSERT INTO settings (key, value) VALUES ('app_settings', ?) "
                "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
                (payload,),
            )
            conn.commit()

    # --- Shows ---

    def get_shows(self) -> List[Show]:
        """Fetch all shows."""
        conn = self._get_connection()
        cur = conn.cursor()
        cur.execute("SELECT * FROM shows ORDER BY name COLLATE NOCASE ASC")
        rows = cur.fetchall()
        return [
            Show(
                id=r["id"],
                name=r["name"],
                path=r["path"],
                status=ShowStatus(r["status"]),
                newest_season=r["newest_season"],
                newest_episode=r["newest_episode"],
                episode_count=r["episode_count"],
                created_at=r["created_at"],
                updated_at=r["updated_at"],
            )
            for r in rows
        ]

    def get_show(self, show_id: int) -> Optional[Show]:
        """Get show by ID."""
        conn = self._get_connection()
        cur = conn.cursor()
        cur.execute("SELECT * FROM shows WHERE id = ?", (show_id,))
        r = cur.fetchone()
        if not r:
            return None
        return Show(
            id=r["id"],
            name=r["name"],
            path=r["path"],
            status=ShowStatus(r["status"]),
            newest_season=r["newest_season"],
            newest_episode=r["newest_episode"],
            episode_count=r["episode_count"],
            created_at=r["created_at"],
            updated_at=r["updated_at"],
        )

    def get_show_by_name(self, name: str) -> Optional[Show]:
        """Get show by exact name."""
        conn = self._get_connection()
        cur = conn.cursor()
        cur.execute("SELECT * FROM shows WHERE name = ? COLLATE NOCASE", (name,))
        r = cur.fetchone()
        if not r:
            return None
        return Show(
            id=r["id"],
            name=r["name"],
            path=r["path"],
            status=ShowStatus(r["status"]),
            newest_season=r["newest_season"],
            newest_episode=r["newest_episode"],
            episode_count=r["episode_count"],
            created_at=r["created_at"],
            updated_at=r["updated_at"],
        )

    def upsert_show(
        self,
        name: str,
        path: str,
        status: ShowStatus = ShowStatus.ACTIVE,
        newest_season: Optional[int] = None,
        newest_episode: Optional[int] = None,
        episode_count: int = 0,
    ) -> Show:
        """Insert or update show."""
        now = datetime.now(timezone.utc).isoformat()
        with self._lock:
            conn = self._get_connection()
            cur = conn.cursor()
            existing = self.get_show_by_name(name)
            if existing:
                cur.execute(
                    """
                    UPDATE shows SET
                        path = ?,
                        status = ?,
                        newest_season = ?,
                        newest_episode = ?,
                        episode_count = ?,
                        updated_at = ?
                    WHERE id = ?
                    """,
                    (
                        path,
                        status.value,
                        newest_season,
                        newest_episode,
                        episode_count,
                        now,
                        existing.id,
                    ),
                )
                show_id = existing.id
            else:
                cur.execute(
                    """
                    INSERT INTO shows (name, path, status, newest_season, newest_episode, episode_count, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        name,
                        path,
                        status.value,
                        newest_season,
                        newest_episode,
                        episode_count,
                        now,
                        now,
                    ),
                )
                show_id = cur.lastrowid
            conn.commit()
            return self.get_show(show_id)

    def set_show_status(self, show_id: int, status: ShowStatus) -> bool:
        """Update active/ended status of a show."""
        now = datetime.now(timezone.utc).isoformat()
        with self._lock:
            conn = self._get_connection()
            cur = conn.cursor()
            cur.execute(
                "UPDATE shows SET status = ?, updated_at = ? WHERE id = ?",
                (status.value, now, show_id),
            )
            conn.commit()
            return cur.rowcount > 0

    def delete_show(self, show_id: int) -> bool:
        """Delete show and its episodes."""
        with self._lock:
            conn = self._get_connection()
            cur = conn.cursor()
            cur.execute("DELETE FROM shows WHERE id = ?", (show_id,))
            conn.commit()
            return cur.rowcount > 0

    # --- Episodes ---

    def get_episodes(self, show_id: Optional[int] = None) -> List[Episode]:
        """Fetch episodes, optionally filtered by show."""
        conn = self._get_connection()
        cur = conn.cursor()
        if show_id is not None:
            cur.execute(
                "SELECT * FROM episodes WHERE show_id = ? ORDER BY season ASC, episode ASC",
                (show_id,),
            )
        else:
            cur.execute(
                "SELECT * FROM episodes ORDER BY show_id ASC, season ASC, episode ASC"
            )
        rows = cur.fetchall()
        return [
            Episode(
                id=r["id"],
                show_id=r["show_id"],
                season=r["season"],
                episode=r["episode"],
                file_name=r["file_name"],
                file_path=r["file_path"],
                file_size=r["file_size"],
                discovered_at=r["discovered_at"],
            )
            for r in rows
        ]

    def sync_episodes_for_show(self, show_id: int, episodes: List[Episode]) -> None:
        """Sync discovered episodes for a given show, adding new ones and pruning removed ones."""
        now = datetime.now(timezone.utc).isoformat()
        with self._lock:
            conn = self._get_connection()
            cur = conn.cursor()

            existing_paths = {ep.file_path for ep in self.get_episodes(show_id)}
            new_paths = {ep.file_path for ep in episodes}

            # Delete removed episodes
            to_delete = existing_paths - new_paths
            if to_delete:
                cur.executemany(
                    "DELETE FROM episodes WHERE show_id = ? AND file_path = ?",
                    [(show_id, p) for p in to_delete],
                )

            # Insert or update new episodes
            for ep in episodes:
                cur.execute(
                    """
                    INSERT INTO episodes (show_id, season, episode, file_name, file_path, file_size, discovered_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(file_path) DO UPDATE SET
                        season = excluded.season,
                        episode = excluded.episode,
                        file_name = excluded.file_name,
                        file_size = excluded.file_size
                    """,
                    (
                        show_id,
                        ep.season,
                        ep.episode,
                        ep.file_name,
                        ep.file_path,
                        ep.file_size,
                        now,
                    ),
                )

            # Update show metadata (total count, newest season, newest episode)
            cur.execute("SELECT COUNT(*) as cnt FROM episodes WHERE show_id = ?", (show_id,))
            cnt = cur.fetchone()["cnt"]

            cur.execute(
                "SELECT season, episode FROM episodes WHERE show_id = ? ORDER BY season DESC, episode DESC LIMIT 1",
                (show_id,),
            )
            newest_row = cur.fetchone()
            newest_s = newest_row["season"] if newest_row else None
            newest_e = newest_row["episode"] if newest_row else None

            cur.execute(
                "UPDATE shows SET episode_count = ?, newest_season = ?, newest_episode = ?, updated_at = ? WHERE id = ?",
                (cnt, newest_s, newest_e, now, show_id),
            )
            conn.commit()

    # --- Indexers ---

    def get_indexers(self, enabled_only: bool = False) -> List[IndexerConfig]:
        """Fetch all configured indexers."""
        conn = self._get_connection()
        cur = conn.cursor()
        if enabled_only:
            cur.execute(
                "SELECT * FROM indexers WHERE enabled = 1 ORDER BY priority ASC, name ASC"
            )
        else:
            cur.execute("SELECT * FROM indexers ORDER BY priority ASC, name ASC")
        rows = cur.fetchall()
        return [
            IndexerConfig(
                id=r["id"],
                name=r["name"],
                type=IndexerType(r["type"]),
                url=r["url"],
                api_key=r["api_key"],
                category_id=r["category_id"],
                enabled=bool(r["enabled"]),
                priority=r["priority"],
            )
            for r in rows
        ]

    def get_indexer(self, indexer_id: int) -> Optional[IndexerConfig]:
        """Fetch indexer by ID."""
        conn = self._get_connection()
        cur = conn.cursor()
        cur.execute("SELECT * FROM indexers WHERE id = ?", (indexer_id,))
        r = cur.fetchone()
        if not r:
            return None
        return IndexerConfig(
            id=r["id"],
            name=r["name"],
            type=IndexerType(r["type"]),
            url=r["url"],
            api_key=r["api_key"],
            category_id=r["category_id"],
            enabled=bool(r["enabled"]),
            priority=r["priority"],
        )

    def save_indexer(self, indexer: IndexerConfig) -> IndexerConfig:
        """Insert or update indexer."""
        with self._lock:
            conn = self._get_connection()
            cur = conn.cursor()
            if indexer.id:
                cur.execute(
                    """
                    UPDATE indexers SET
                        name = ?,
                        type = ?,
                        url = ?,
                        api_key = ?,
                        category_id = ?,
                        enabled = ?,
                        priority = ?
                    WHERE id = ?
                    """,
                    (
                        indexer.name,
                        indexer.type.value,
                        indexer.url,
                        indexer.api_key,
                        indexer.category_id,
                        1 if indexer.enabled else 0,
                        indexer.priority,
                        indexer.id,
                    ),
                )
                indexer_id = indexer.id
            else:
                cur.execute(
                    """
                    INSERT INTO indexers (name, type, url, api_key, category_id, enabled, priority)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        indexer.name,
                        indexer.type.value,
                        indexer.url,
                        indexer.api_key,
                        indexer.category_id,
                        1 if indexer.enabled else 0,
                        indexer.priority,
                    ),
                )
                indexer_id = cur.lastrowid
            conn.commit()
            return self.get_indexer(indexer_id)

    def delete_indexer(self, indexer_id: int) -> bool:
        """Delete an indexer."""
        with self._lock:
            conn = self._get_connection()
            cur = conn.cursor()
            cur.execute("DELETE FROM indexers WHERE id = ?", (indexer_id,))
            conn.commit()
            return cur.rowcount > 0

    # --- Downloads ---

    def record_download(
        self,
        show_name: str,
        season: int,
        episode: int,
        title: str,
        indexer_name: str,
        nzb_url: str,
        downloader_id: Optional[str] = None,
        status: DownloadStatus = DownloadStatus.QUEUED,
    ) -> DownloadRecord:
        """Record a newly queued download."""
        now = datetime.now(timezone.utc).isoformat()
        with self._lock:
            conn = self._get_connection()
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO downloads (show_name, season, episode, title, indexer_name, nzb_url, status, downloader_id, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    show_name,
                    season,
                    episode,
                    title,
                    indexer_name,
                    nzb_url,
                    status.value,
                    downloader_id,
                    now,
                ),
            )
            download_id = cur.lastrowid
            conn.commit()
            return self.get_download(download_id)

    def get_download(self, download_id: int) -> Optional[DownloadRecord]:
        """Get download by ID."""
        conn = self._get_connection()
        cur = conn.cursor()
        cur.execute("SELECT * FROM downloads WHERE id = ?", (download_id,))
        r = cur.fetchone()
        if not r:
            return None
        return DownloadRecord(
            id=r["id"],
            show_name=r["show_name"],
            season=r["season"],
            episode=r["episode"],
            title=r["title"],
            indexer_name=r["indexer_name"],
            nzb_url=r["nzb_url"],
            status=DownloadStatus(r["status"]),
            downloader_id=r["downloader_id"],
            error_message=r["error_message"],
            created_at=r["created_at"],
            completed_at=r["completed_at"],
        )

    def get_downloads(
        self, limit: int = 50, status: Optional[DownloadStatus] = None
    ) -> List[DownloadRecord]:
        """Get downloads with optional status filter."""
        conn = self._get_connection()
        cur = conn.cursor()
        if status:
            cur.execute(
                "SELECT * FROM downloads WHERE status = ? ORDER BY id DESC LIMIT ?",
                (status.value, limit),
            )
        else:
            cur.execute("SELECT * FROM downloads ORDER BY id DESC LIMIT ?", (limit,))
        rows = cur.fetchall()
        return [
            DownloadRecord(
                id=r["id"],
                show_name=r["show_name"],
                season=r["season"],
                episode=r["episode"],
                title=r["title"],
                indexer_name=r["indexer_name"],
                nzb_url=r["nzb_url"],
                status=DownloadStatus(r["status"]),
                downloader_id=r["downloader_id"],
                error_message=r["error_message"],
                created_at=r["created_at"],
                completed_at=r["completed_at"],
            )
            for r in rows
        ]

    def update_download_status(
        self,
        download_id: int,
        status: DownloadStatus,
        downloader_id: Optional[str] = None,
        error_message: Optional[str] = None,
    ) -> bool:
        """Update the state of a download."""
        now = datetime.now(timezone.utc).isoformat()
        completed_at = (
            now if status in (DownloadStatus.IMPORTED, DownloadStatus.COMPLETED) else None
        )
        with self._lock:
            conn = self._get_connection()
            cur = conn.cursor()
            cur.execute(
                """
                UPDATE downloads SET
                    status = ?,
                    downloader_id = COALESCE(?, downloader_id),
                    error_message = ?,
                    completed_at = COALESCE(?, completed_at)
                WHERE id = ?
                """,
                (status.value, downloader_id, error_message, completed_at, download_id),
            )
            conn.commit()
            return cur.rowcount > 0

    # --- Logs ---

    def log(self, level: str, category: str, message: str) -> None:
        """Record an audit or application log entry."""
        now = datetime.now(timezone.utc).isoformat()
        with self._lock:
            conn = self._get_connection()
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO logs (timestamp, level, category, message) VALUES (?, ?, ?, ?)",
                (now, level.upper(), category, message),
            )
            conn.commit()

    def get_logs(
        self, limit: int = 100, level: Optional[str] = None, category: Optional[str] = None
    ) -> List[LogEntry]:
        """Fetch system and audit logs."""
        conn = self._get_connection()
        cur = conn.cursor()
        query = "SELECT * FROM logs"
        params: List[Any] = []
        conditions = []
        if level:
            conditions.append("level = ?")
            params.append(level.upper())
        if category:
            conditions.append("category = ?")
            params.append(category)

        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        query += " ORDER BY id DESC LIMIT ?"
        params.append(limit)

        cur.execute(query, tuple(params))
        rows = cur.fetchall()
        return [
            LogEntry(
                id=r["id"],
                timestamp=r["timestamp"],
                level=r["level"],
                category=r["category"],
                message=r["message"],
            )
            for r in rows
        ]
