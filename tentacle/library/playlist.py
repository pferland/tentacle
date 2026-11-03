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

"""Playlist Generator (ASX v3.0 and M3U8)."""

from __future__ import annotations

import os
from xml.sax.saxutils import escape
from tentacle.database import Database


class PlaylistGenerator:
    """Generates ASX v3.0 and M3U8 playlists for the entire media library."""

    def __init__(self, db: Database) -> None:
        self.db = db

    def generate_all(self) -> None:
        """Generate both ASX and M3U8 playlists based on current settings."""
        settings = self.db.get_settings()
        episodes = self.db.get_episodes()
        shows = {s.id: s.name for s in self.db.get_shows()}

        if settings.playlist_asx_path:
            self.generate_asx(settings.playlist_asx_path, episodes, shows)
        if settings.playlist_m3u8_path:
            self.generate_m3u8(settings.playlist_m3u8_path, episodes, shows)

    def generate_asx(self, output_path: str, episodes: list, shows: dict) -> None:
        """Generate Windows Media ASX v3.0 playlist."""
        lines = ['<asx version = "3.0" >']
        for ep in episodes:
            show_name = shows.get(ep.show_id, "Show")
            title = f"{show_name} - S{ep.season:02d}E{ep.episode:02d} - {ep.file_name}"
            safe_title = escape(title)
            safe_path = escape(ep.file_path)
            lines.append("\t<entry>")
            lines.append(f"\t\t<title>{safe_title}</title>")
            lines.append(f'\t\t<ref href = "{safe_path}" />')
            lines.append("\t</entry>")
        lines.append("</asx>\n")

        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
        self.db.log("INFO", "playlist", f"Updated ASX playlist: {output_path} ({len(episodes)} items)")

    def generate_m3u8(self, output_path: str, episodes: list, shows: dict) -> None:
        """Generate modern UTF-8 Extended M3U playlist."""
        lines = ["#EXTM3U"]
        for ep in episodes:
            show_name = shows.get(ep.show_id, "Show")
            title = f"{show_name} - S{ep.season:02d}E{ep.episode:02d}"
            lines.append(f"#EXTINF:-1,{title}")
            lines.append(ep.file_path)
        lines.append("")

        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
        self.db.log("INFO", "playlist", f"Updated M3U8 playlist: {output_path} ({len(episodes)} items)")
