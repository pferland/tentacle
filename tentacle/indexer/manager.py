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

"""Indexer Manager coordinating searches across configured Usenet providers."""

from __future__ import annotations

import logging
from typing import List, Optional, Tuple

from tentacle.database import Database
from tentacle.indexer.newznab import NewznabClient
from tentacle.models import IndexerConfig, IndexerSearchResult

logger = logging.getLogger("tentacle.indexer")


class IndexerManager:
    """Manages searches across multiple Usenet indexers."""

    def __init__(self, db: Database) -> None:
        self.db = db

    def get_client(self, config: IndexerConfig) -> NewznabClient:
        """Create a client for the given indexer."""
        return NewznabClient(config)

    async def test_indexer(self, config: IndexerConfig) -> Tuple[bool, str]:
        """Test connection for a specific indexer config."""
        client = self.get_client(config)
        return await client.test_connection()

    async def search_episode(
        self, show_name: str, season: int, episode: int
    ) -> List[IndexerSearchResult]:
        """Search all enabled indexers for an episode, returning aggregated results."""
        indexers = self.db.get_indexers(enabled_only=True)
        if not indexers:
            self.db.log(
                "WARNING",
                "indexer",
                f"No enabled indexers configured! Cannot search for {show_name} S{season:02d}E{episode:02d}.",
            )
            return []

        all_results: List[IndexerSearchResult] = []
        for indexer in indexers:
            try:
                client = self.get_client(indexer)
                results = await client.search_episode(show_name, season, episode)
                if results:
                    self.db.log(
                        "INFO",
                        "indexer",
                        f"Found {len(results)} release(s) on {indexer.name} for {show_name} S{season:02d}E{episode:02d}.",
                    )
                    all_results.extend(results)
            except Exception as e:
                self.db.log(
                    "ERROR",
                    "indexer",
                    f"Error searching {indexer.name} for {show_name} S{season:02d}E{episode:02d}: {str(e)}",
                )

        # Deduplicate results by title
        seen_titles = set()
        deduped = []
        for res in all_results:
            clean_title = res.title.strip().lower()
            if clean_title not in seen_titles:
                seen_titles.add(clean_title)
                deduped.append(res)

        return deduped

    async def download_nzb_bytes(self, nzb_url: str, indexer_name: str) -> Optional[bytes]:
        """Download NZB file content from the relevant indexer."""
        indexers = {idx.name: idx for idx in self.db.get_indexers()}
        indexer = indexers.get(indexer_name)
        if not indexer:
            # Fallback to any enabled indexer or standard client
            enabled = self.db.get_indexers(enabled_only=True)
            indexer = enabled[0] if enabled else None

        if not indexer:
            return None

        client = self.get_client(indexer)
        try:
            return await client.download_nzb(nzb_url)
        except Exception as e:
            self.db.log("ERROR", "indexer", f"Failed downloading NZB from {indexer.name}: {e}")
            return None
