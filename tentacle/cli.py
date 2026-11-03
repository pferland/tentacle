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

"""Command Line Interface for Tentacle V4."""

from __future__ import annotations

import asyncio
import sys
import click
import uvicorn

from tentacle import __version__
from tentacle.database import Database
from tentacle.engine.scheduler import SchedulerEngine


@click.group()
@click.version_option(__version__, prog_name="Tentacle")
def main():
    """Tentacle V4 - Automated TV Show Tracker, Downloader & Media Organizer."""
    pass


@main.command("web")
@click.option("--host", default=None, help="Host address to bind to (e.g. 0.0.0.0)")
@click.option("--port", default=None, type=int, help="Port to listen on (e.g. 8080)")
@click.option("--reload", is_flag=True, default=False, help="Enable auto-reload for development")
def run_web(host: str | None, port: int | None, reload: bool):
    """Start the Web UI and background daemon server."""
    db = Database("tentacle.db")
    settings = db.get_settings()
    bind_host = host or settings.web_host
    bind_port = port or settings.web_port

    click.echo(f"🐙 Starting Tentacle V4 WebUI & Daemon on http://{bind_host}:{bind_port}")
    uvicorn.run("tentacle.web.app:app", host=bind_host, port=bind_port, reload=reload)


@main.command("scan")
def run_scan():
    """Scan the media directory and print discovered TV shows."""
    db = Database("tentacle.db")
    scheduler = SchedulerEngine(db)
    click.echo("📁 Scanning media library...")
    shows = scheduler.scanner.scan_all()
    click.echo(f"\nIndexed {len(shows)} TV Show(s):")
    for s in shows:
        ep_info = (
            f"S{s.newest_season:02d}E{s.newest_episode:02d}"
            if s.newest_season is not None and s.newest_episode is not None
            else "No episodes"
        )
        status_str = f"[{s.status.value.upper()}]"
        click.echo(f" - {s.name:<30} {status_str:<10} {ep_info:<12} ({s.episode_count} eps)")


@main.command("search")
def run_search():
    """Search enabled UseNet providers for upcoming episodes."""
    db = Database("tentacle.db")
    scheduler = SchedulerEngine(db)
    click.echo("🔍 Searching configured UseNet indexers for next episodes...")
    count = asyncio.run(scheduler.search_and_queue_missing_episodes())
    click.echo(f"Search complete: Queued {count} new release(s).")


@main.command("organize")
def run_organize():
    """Process and organize completed downloads into media library."""
    db = Database("tentacle.db")
    scheduler = SchedulerEngine(db)
    click.echo("📦 Organizing completed downloads...")
    imported = scheduler.organizer.organize_completed()
    click.echo(f"Post-processing complete: Imported {imported} episode(s).")


@main.command("playlist")
def run_playlist():
    """Regenerate ASX and M3U8 playlists."""
    db = Database("tentacle.db")
    scheduler = SchedulerEngine(db)
    click.echo("🎵 Generating playlists...")
    scheduler.playlist.generate_all()
    click.echo("Playlists updated successfully.")


@main.command("run-once")
def run_once():
    """Execute a single complete processing pass (scan -> organize -> search -> playlist) and exit."""
    db = Database("tentacle.db")
    scheduler = SchedulerEngine(db)
    click.echo("🚀 Running complete single pass...")
    asyncio.run(scheduler.run_full_cycle())
    click.echo("Single pass complete.")


if __name__ == "__main__":
    main()
