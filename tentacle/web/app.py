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

"""FastAPI Web Application and API for Tentacle V4."""

from __future__ import annotations

import os
from contextlib import asynccontextmanager
from typing import Any, Dict, List, Optional

from fastapi import Body, FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from tentacle.database import Database
from tentacle.downloader.manager import DownloaderManager
from tentacle.engine.scheduler import SchedulerEngine
from tentacle.indexer.presets import INDEXER_PRESETS
from tentacle.models import (
    AppSettings,
    DownloaderConfig,
    DownloadStatus,
    IndexerConfig,
    ShowStatus,
)

# Template and static paths
MODULE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATES_DIR = os.path.join(MODULE_DIR, "templates")
STATIC_DIR = os.path.join(MODULE_DIR, "static")

db = Database("tentacle.db")
scheduler = SchedulerEngine(db)
templates = Jinja2Templates(directory=TEMPLATES_DIR)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI application lifespan manager."""
    # Ensure default indexer presets or settings exist if table empty
    if not db.get_indexers():
        # Add default preset for NZBGeek (disabled by default until key is provided)
        db.save_indexer(
            IndexerConfig(
                name="NZBGeek (Preset)",
                url="https://api.nzbgeek.info",
                api_key="",
                category_id="5000,5030,5040",
                enabled=False,
                priority=1,
            )
        )
    # Start scheduler daemon
    scheduler.start()
    yield
    # Stop scheduler daemon
    scheduler.stop()


app = FastAPI(
    title="Tentacle V4",
    description="Automated TV Show Tracker, Downloader and Media Organizer",
    version="4.0.0",
    lifespan=lifespan,
)

# Static files (create directory if not existing)
os.makedirs(STATIC_DIR, exist_ok=True)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


# --- HTML Page Routes ---


@app.get("/", response_class=HTMLResponse)
async def page_dashboard(request: Request):
    status = scheduler.get_status()
    shows = db.get_shows()
    logs = db.get_logs(limit=25)
    return templates.TemplateResponse(
        request=request,
        name="dashboard.html",
        context={
            "page": "dashboard",
            "status": status,
            "shows": shows,
            "logs": logs,
        },
    )


@app.get("/shows", response_class=HTMLResponse)
async def page_shows(request: Request):
    shows = db.get_shows()
    return templates.TemplateResponse(
        request=request,
        name="shows.html",
        context={
            "page": "shows",
            "shows": shows,
        },
    )


@app.get("/shows/{show_id}", response_class=HTMLResponse)
async def page_show_detail(request: Request, show_id: int):
    show = db.get_show(show_id)
    if not show:
        raise HTTPException(status_code=404, detail="Show not found")
    episodes = db.get_episodes(show_id=show_id)

    # Group episodes cleanly by season
    seasons_map: Dict[int, Dict[str, Any]] = {}
    total_bytes = 0
    for ep in episodes:
        total_bytes += ep.file_size
        if ep.season not in seasons_map:
            seasons_map[ep.season] = {
                "season": ep.season,
                "episodes": [],
                "total_size": 0,
            }
        seasons_map[ep.season]["episodes"].append(ep)
        seasons_map[ep.season]["total_size"] += ep.file_size

    # Sort episodes ascending within each season
    for s_info in seasons_map.values():
        s_info["episodes"].sort(key=lambda x: x.episode)

    # Sort seasons descending (newest season first)
    sorted_seasons = [seasons_map[k] for k in sorted(seasons_map.keys(), reverse=True)]

    return templates.TemplateResponse(
        request=request,
        name="show_detail.html",
        context={
            "page": "shows",
            "show": show,
            "seasons": sorted_seasons,
            "total_size": total_bytes,
            "total_seasons": len(seasons_map),
        },
    )


@app.get("/indexers", response_class=HTMLResponse)
async def page_indexers(request: Request):
    indexers = db.get_indexers()
    return templates.TemplateResponse(
        request=request,
        name="indexers.html",
        context={
            "page": "indexers",
            "indexers": indexers,
            "presets": INDEXER_PRESETS,
        },
    )


@app.get("/downloads", response_class=HTMLResponse)
async def page_downloads(request: Request):
    downloads = db.get_downloads(limit=100)
    return templates.TemplateResponse(
        request=request,
        name="downloads.html",
        context={
            "page": "downloads",
            "downloads": downloads,
        },
    )


@app.get("/settings", response_class=HTMLResponse)
async def page_settings(request: Request):
    settings = db.get_settings()
    return templates.TemplateResponse(
        request=request,
        name="settings.html",
        context={
            "page": "settings",
            "settings": settings,
        },
    )


@app.get("/logs", response_class=HTMLResponse)
async def page_logs(request: Request):
    logs = db.get_logs(limit=150)
    return templates.TemplateResponse(
        request=request,
        name="logs.html",
        context={
            "page": "logs",
            "logs": logs,
        },
    )


# --- REST API Endpoints ---


@app.get("/api/status")
async def api_status():
    return scheduler.get_status().model_dump()


@app.post("/api/scan")
async def api_trigger_scan():
    scheduler.trigger_cycle_now()
    return {"success": True, "message": "Library scan triggered"}


@app.post("/api/search")
async def api_trigger_search():
    count = await scheduler.search_and_queue_missing_episodes()
    return {"success": True, "queued_count": count, "message": f"Queued {count} release(s)"}


@app.post("/api/organize")
async def api_trigger_organize():
    imported = scheduler.organizer.organize_completed()
    return {
        "success": True,
        "imported_count": imported,
        "message": f"Imported {imported} release(s)",
    }


# Shows API
@app.get("/api/shows")
async def api_get_shows():
    return [s.model_dump() for s in db.get_shows()]


@app.post("/api/shows/{show_id}/status")
async def api_set_show_status(show_id: int, payload: Dict[str, str] = Body(...)):
    new_status = payload.get("status", "active")
    try:
        status_enum = ShowStatus(new_status)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid status")
    success = db.set_show_status(show_id, status_enum)
    if not success:
        raise HTTPException(status_code=404, detail="Show not found")
    return {"success": True, "status": new_status}


@app.post("/api/shows/{show_id}/search")
async def api_search_show(show_id: int):
    show = db.get_show(show_id)
    if not show:
        raise HTTPException(status_code=404, detail="Show not found")
    s = show.newest_season or 1
    e = (show.newest_episode or 0) + 1
    results = await scheduler.indexer_manager.search_episode(show.name, s, e)
    if not results and e > 1:
        s = s + 1
        e = 1
        results = await scheduler.indexer_manager.search_episode(show.name, s, e)

    if results:
        best = results[0]
        dispatched = await scheduler._dispatch_release(show.name, s, e, best)
        if dispatched:
            return {
                "success": True,
                "message": f"Queued S{s:02d}E{e:02d}: {best.title}",
            }
        return {"success": False, "message": "Failed to dispatch download to client"}
    return {
        "success": False,
        "message": f"No release found for S{s:02d}E{e:02d}",
    }


@app.delete("/api/shows/{show_id}")
async def api_delete_show(show_id: int):
    success = db.delete_show(show_id)
    if not success:
        raise HTTPException(status_code=404, detail="Show not found")
    return {"success": True}


# Indexers API
@app.get("/api/indexers")
async def api_get_indexers():
    return [i.model_dump() for i in db.get_indexers()]


@app.post("/api/indexers")
async def api_save_indexer(indexer: IndexerConfig):
    saved = db.save_indexer(indexer)
    return saved.model_dump()


@app.post("/api/indexers/{indexer_id}/status")
async def api_toggle_indexer(indexer_id: int, payload: Dict[str, bool] = Body(...)):
    idx = db.get_indexer(indexer_id)
    if not idx:
        raise HTTPException(status_code=404, detail="Indexer not found")
    idx.enabled = payload.get("enabled", True)
    db.save_indexer(idx)
    return {"success": True, "enabled": idx.enabled}


@app.post("/api/indexers/test")
async def api_test_indexer_payload(indexer: IndexerConfig):
    success, msg = await scheduler.indexer_manager.test_indexer(indexer)
    return {"success": success, "message": msg}


@app.post("/api/indexers/{indexer_id}/test")
async def api_test_saved_indexer(indexer_id: int):
    idx = db.get_indexer(indexer_id)
    if not idx:
        raise HTTPException(status_code=404, detail="Indexer not found")
    success, msg = await scheduler.indexer_manager.test_indexer(idx)
    return {"success": success, "message": msg}


@app.delete("/api/indexers/{indexer_id}")
async def api_delete_indexer(indexer_id: int):
    success = db.delete_indexer(indexer_id)
    if not success:
        raise HTTPException(status_code=404, detail="Indexer not found")
    return {"success": True}


# Settings API
@app.get("/api/settings")
async def api_get_settings():
    return db.get_settings().model_dump()


@app.post("/api/settings")
async def api_save_settings(settings: AppSettings):
    settings.normalize_paths()
    db.save_settings(settings)
    return {"success": True, "message": "Settings updated"}


@app.post("/api/downloader/test")
async def api_test_downloader(config: DownloaderConfig):
    success, msg = await DownloaderManager.test_connection(config)
    return {"success": success, "message": msg}


# Downloads API
@app.get("/api/downloads")
async def api_get_downloads(limit: int = 50):
    return [d.model_dump() for d in db.get_downloads(limit=limit)]


@app.post("/api/downloads/{download_id}/retry")
async def api_retry_download(download_id: int):
    d = db.get_download(download_id)
    if not d:
        raise HTTPException(status_code=404, detail="Download not found")
    db.update_download_status(download_id, DownloadStatus.QUEUED, error_message=None)
    scheduler.trigger_cycle_now()
    return {"success": True, "message": "Download re-queued"}


@app.delete("/api/downloads/{download_id}")
async def api_delete_download(download_id: int):
    # Update status to failed or remove from DB
    db.update_download_status(
        download_id, DownloadStatus.FAILED, error_message="Cancelled by user"
    )
    return {"success": True}


# Logs API
@app.get("/api/logs")
async def api_get_logs(limit: int = 100):
    return [l.model_dump() for l in db.get_logs(limit=limit)]
