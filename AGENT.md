# AGENT.md - Project Knowledge Base for Tentacle

> **Project Identity**: `tentacle` (repository named `tenticle`)  
> **Author**: Phillip Ferland (`Longbow486` <pferland@randomintervals.com>)  
> **Current Version**: **V4.0 (Python Rewrite with WebUI)**  
> **Branch**: `v4`  
> **License**: GNU General Public License v3 (GPLv3)  
> **Status**: Active Modern Rewrite. Legacy PHP5/SQL code preserved in `legacy/`.

---

## 1. Executive Summary: Tentacle V4

Tentacle V4 is a complete rewrite of the application in Python 3, replacing the obsolete PHP5 codebase, defunct NZBMatrix indexer, and archaic SQL/Smarty setup. It provides an automated media lifecycle for television series:

1. **TV Library Tracking**: Recursively indexes television show directories (`Show Name/Season X/Episode.ext`), detecting season and episode numbers (`SxxExx`, `1x02`, etc.) and tracking the newest episode for each series.
2. **Star Trek `dead.txt` Support**: Preserves the classic marker file (`dead.txt` containing `"hes dead jim"`). When dropped into a show's directory, Tentacle flags the show as ended/cancelled and stops searching for new episodes. Status can also be toggled directly in the WebUI.
3. **Configurable UseNet Indexers**: Full Newznab/Torznab standard support. Features built-in presets (NZBGeek, NZBPlanet, DogNZB, DrunkenSlug, Tabula Rasa, Prowlarr) and custom API endpoints, with priority ordering and real-time connection testing.
4. **Flexible Downloader Integration**: Dispatches NZBs via modern SABnzbd JSON API (`addurl` / `addfile`, queue & history monitoring) or directory-based Blackhole watch folders.
5. **Post-Processing & Organizing**: Detects completed downloads, extracts video files, skips junk (`.nfo`, `.sfv`, `.par2`, samples), moves media into target `Season X` folders, and safely cleans up unpack directories.
6. **Dual Playlist Generation**: Generates both Windows Media ASX v3.0 (`Shows.asx`) and modern extended UTF-8 M3U8 (`Shows.m3u8`) playlists.
7. **Modern Web Interface**: Responsive dark-mode dashboard built with FastAPI, Jinja2, and Tailwind CSS.
8. **Relational SQLite Database**: Clean, normalized SQLite database (`tentacle.db`) with zero heavy ORM baggage, replacing serialized PHP blobs.

---

## 2. V4 Architecture & Repository Structure

```
.
├── AGENT.md                        # Project knowledge base (this file)
├── LICENSE                         # GNU General Public License v3
├── README.md                       # User documentation and setup guide
├── pyproject.toml                  # Python package configuration and metadata
├── requirements.txt                # Production dependencies
├── dead.txt                        # Classic marker file ("hes dead jim")
├── legacy/                         # Preserved legacy PHP 5.2/5.3 & SQL code (V2 & V3)
│   ├── SQL/                        # Legacy MySQL and PostgreSQL dumps
│   ├── settings/                   # Legacy PHP configuration arrays
│   ├── tentacle.php                # Legacy V3.0 CLI daemon
│   ├── tentacle_old.php            # Legacy V2.0 CLI daemon
│   ├── todo.txt                    # Original historical notes
│   └── www/                        # Legacy Smarty/PHP web UI
├── tentacle/                       # Python V4 Package Root
│   ├── __init__.py                 # Package version (4.0.0) & metadata
│   ├── __main__.py                 # Entry point (`python -m tentacle`)
│   ├── cli.py                      # Click CLI commands (web, scan, search, organize, playlist, run-once)
│   ├── models.py                   # Pydantic schemas, Enums, and DTOs
│   ├── database.py                 # SQLite database layer (shows, episodes, indexers, downloads, logs)
│   ├── downloader/                 # Downloader subsystem
│   │   ├── base.py                 # Abstract BaseDownloader
│   │   ├── sabnzbd.py              # SABnzbd JSON API client
│   │   ├── blackhole.py            # Watch directory blackhole client
│   │   └── manager.py              # Downloader factory & connectivity tester
│   ├── indexer/                    # UseNet Indexer subsystem
│   │   ├── presets.py              # Pre-configured providers (NZBGeek, Planet, Dog, Slug, etc.)
│   │   ├── newznab.py              # Newznab API client (XML & JSON search, NZB download)
│   │   └── manager.py              # Multi-indexer coordinator & search dispatcher
│   ├── library/                    # Media Library & File System subsystem
│   │   ├── parser.py               # Regex episode parser & media/sample filter
│   │   ├── scanner.py              # TV show directory scanner & dead.txt detector
│   │   ├── organizer.py            # Post-processing completed downloads importer
│   │   └── playlist.py             # ASX v3.0 & M3U8 playlist generator
│   ├── engine/                     # Background Daemon subsystem
│   │   └── scheduler.py            # SchedulerEngine coordinating periodic runs
│   └── web/                        # Web Dashboard & REST API
│       ├── app.py                  # FastAPI application & router
│       ├── static/                 # Static web assets
│       └── templates/              # Jinja2 templates (Tailwind CSS)
│           ├── base.html           # Layout shell & responsive navigation
│           ├── dashboard.html      # Overview, stats, quick action buttons, recent activity
│           ├── shows.html          # Shows library table with search & status toggle
│           ├── show_detail.html    # Detailed show view with indexed episodes & direct search
│           ├── indexers.html       # UseNet providers manager with presets & test connection
│           ├── downloads.html      # Download queue and post-processing history
│           ├── settings.html       # Path settings, downloader credentials, scan interval
│           └── logs.html           # Live event and audit logs viewer
└── tests/                          # Automated Pytest Suite
    ├── test_database.py            # Database CRUD tests
    ├── test_downloader.py          # SABnzbd & Blackhole downloader tests
    ├── test_indexers.py            # Newznab client & preset tests
    ├── test_organizer.py           # Media importer & junk cleanup tests
    ├── test_parser.py              # Episode parsing & media filter tests
    ├── test_playlist.py            # ASX and M3U8 generation tests
    ├── test_scanner.py             # Library scanner & dead.txt tests
    └── test_web_api.py             # FastAPI REST endpoints tests
```

---

## 3. Database Schema (SQLite: `tentacle.db`)

V4 replaces serialized PHP blobs with a normalized relational schema:

### Tables:
1. **`settings`**:
   - `key TEXT PRIMARY KEY`, `value TEXT NOT NULL` (JSON-serialized `AppSettings`).
2. **`shows`**:
   - `id INTEGER PRIMARY KEY AUTOINCREMENT`
   - `name TEXT UNIQUE NOT NULL`
   - `path TEXT NOT NULL`
   - `status TEXT NOT NULL DEFAULT 'active'` (`active` / `ended`)
   - `newest_season INTEGER`, `newest_episode INTEGER`
   - `episode_count INTEGER NOT NULL DEFAULT 0`
   - `created_at TEXT`, `updated_at TEXT`
3. **`episodes`**:
   - `id INTEGER PRIMARY KEY AUTOINCREMENT`
   - `show_id INTEGER NOT NULL REFERENCES shows(id) ON DELETE CASCADE`
   - `season INTEGER NOT NULL`, `episode INTEGER NOT NULL`
   - `file_name TEXT NOT NULL`, `file_path TEXT UNIQUE NOT NULL`
   - `file_size INTEGER NOT NULL DEFAULT 0`
   - `discovered_at TEXT NOT NULL`
4. **`indexers`**:
   - `id INTEGER PRIMARY KEY AUTOINCREMENT`
   - `name TEXT NOT NULL`, `type TEXT NOT NULL DEFAULT 'newznab'`
   - `url TEXT NOT NULL`, `api_key TEXT NOT NULL`
   - `category_id TEXT NOT NULL DEFAULT '5000,5030,5040'`
   - `enabled INTEGER NOT NULL DEFAULT 1`, `priority INTEGER NOT NULL DEFAULT 1`
5. **`downloads`**:
   - `id INTEGER PRIMARY KEY AUTOINCREMENT`
   - `show_name TEXT NOT NULL`, `season INTEGER NOT NULL`, `episode INTEGER NOT NULL`
   - `title TEXT NOT NULL`, `indexer_name TEXT NOT NULL`, `nzb_url TEXT NOT NULL`
   - `status TEXT NOT NULL DEFAULT 'queued'` (`queued`, `downloading`, `completed`, `imported`, `failed`)
   - `downloader_id TEXT`, `error_message TEXT`
   - `created_at TEXT`, `completed_at TEXT`
6. **`logs`**:
   - `id INTEGER PRIMARY KEY AUTOINCREMENT`
   - `timestamp TEXT NOT NULL`, `level TEXT NOT NULL`, `category TEXT NOT NULL`, `message TEXT NOT NULL`

---

## 4. UseNet Providers & Indexer Subsystem

NZBMatrix is permanently offline. V4 implements the modern **Newznab/Torznab specification**:

- **Pre-configured Provider Presets**:
  - `NZBGeek`: `https://api.nzbgeek.info`
  - `NZBPlanet`: `https://api.nzbplanet.net`
  - `DogNZB`: `https://api.dognzb.cr`
  - `DrunkenSlug`: `https://api.drunkenslug.com`
  - `Tabula Rasa`: `https://www.tabula-rasa.info`
  - `Prowlarr (Local Proxy)`: `http://127.0.0.1:9696`
  - `Custom Provider`: Any URL supporting `/api?t=...&apikey=...`
- **Capabilities & Connection Testing**:
  - Queries `t=caps&apikey=...` to verify credentials before saving.
- **Search Routine**:
  - Dedicated TV Search: `t=tvsearch&q={show}&season={season}&ep={episode}&apikey={key}&o=json`
  - Fallback Query Search: `t=search&q={show}+S{season:02d}E{episode:02d}`
  - Parses both modern JSON output and standard RSS XML with Newznab attributes.
  - Multi-indexer dispatch sorted by priority, deduplicating release titles.

---

## 5. Downloader Subsystem

Supports two downloader modes selectable in Settings:
1. **SABnzbd (JSON API)**:
   - Connects to modern SABnzbd API (`mode=version`, `mode=addurl`, `mode=addfile`, `mode=queue`, `mode=history`).
   - Supports HTTP and HTTPS, custom sub-paths, and API key auth.
   - Monitors queue until idle, then automatically triggers the media organizer.
2. **Blackhole (Watch Directory)**:
   - Drops `.nzb` files into `watch_dir` for external clients (e.g. NZBGet, NAS down-loaders).
   - Monitors `completed_dir` for finished folders and files.

---

## 6. CLI Command Reference

The command-line interface is available via `tentacle` (or `python -m tentacle`):

| Command | Description |
|---|---|
| `tentacle web` | Starts FastAPI WebUI & daemon background scheduler |
| `tentacle scan` | Scans media library and outputs detected shows & episode counts |
| `tentacle search` | Searches configured UseNet providers for missing episodes |
| `tentacle organize` | Post-processes completed downloads and moves them to library |
| `tentacle playlist` | Regenerates ASX and M3U8 playlists |
| `tentacle run-once` | Executes a single full lifecycle pass and exits |

---

## 7. Systemd Service Management

Tentacle includes a pre-configured unit file [`tentacle.service`](tentacle.service):

```ini
[Unit]
Description=Tentacle V4 - TV Show Tracker, Downloader & Media Organizer
After=network.target

[Service]
Type=simple
User=pferland
WorkingDirectory=/storage/files/GitHub/tenticle
ExecStart=/storage/files/GitHub/tenticle/.venv/bin/python3 -m tentacle web --host 0.0.0.0 --port 8080
Restart=always
RestartSec=10
```

Commands to manage:
```bash
sudo cp tentacle.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now tentacle.service
sudo systemctl status tentacle.service
journalctl -u tentacle.service -f
```

---

## 8. Unit & Integration Test Coverage

The automated test suite in `tests/` covers all core subsystems:

1. **`test_parser.py`**:
   - `test_is_media_file`: Confirms video extension detection (`.mkv`, `.mp4`, `.avi`) and rejection of junk metadata (`.nfo`, `.par2`, `.sfv`, images).
   - `test_parse_season_episode`: Tests regex parsing of season/episode numbers across varied formats (`S01E02`, `1x02`, `Season 1 Episode 4`) and verifies non-episode titles are rejected.
   - `test_extract_season_from_folder`: Tests extracting season numbers from parent folders (`Season 1`, `Season 02`, `S4`).

2. **`test_database.py`**:
   - `test_settings_crud`: Validates SQLite JSON serialization and retrieval of application settings.
   - `test_shows_and_episodes`: Validates show upsert, episode sync, automated resolution of newest season/episode, and status toggles (`active` vs `ended`).
   - `test_indexers_crud`: Tests CRUD operations on UseNet indexer records.
   - `test_downloads_and_logs`: Tests tracking download records through their lifecycle and querying audit logs.

3. **`test_scanner.py`**:
   - `test_library_scanner`: Scans a simulated filesystem containing multiple shows. Validates episode indexing, latest episode identification, and verifies that encountering `dead.txt` ("hes dead jim") automatically marks the show as `ENDED`.

4. **`test_organizer.py`**:
   - `test_media_organizer`: Simulates post-processing an unpacked download release directory with video and junk files (`.nfo`, `.sfv`). Verifies moving the video into `Shows/Show/Season X/`, safely deleting the temporary unpacked directory, and updating the download record status to `IMPORTED`.

5. **`test_playlist.py`**:
   - `test_playlist_generator`: Tests generating both Windows Media ASX v3.0 XML (`Shows.asx`) and modern extended M3U8 (`Shows.m3u8`) playlists.

6. **`test_indexers.py`**:
   - `test_presets`: Verifies provider preset definitions (NZBGeek, DogNZB, DrunkenSlug, Prowlarr, etc.).
   - `test_newznab_xml_parser` & `test_newznab_json_parser`: Verifies parsing of Newznab XML/RSS and JSON payloads for title, release size, and download link.

7. **`test_downloader.py`**:
   - `test_blackhole_downloader`: Verifies writing NZB payloads to watch folders, checking queue busy state while files are pending, and reporting idle once files are picked up.
   - `test_sabnzbd_instance`: Verifies SABnzbd client construction and parameter formatting.

8. **`test_web_api.py`**:
   - `test_api_status`: Tests `/api/status` endpoint for daemon status and counts.
   - `test_api_shows`: Tests `/api/shows` listing.
   - `test_api_indexers`: Tests creating, listing, toggling, and deleting indexers via the REST API.
   - `test_api_settings`: Tests `/api/settings` endpoint.

---

## 9. Historical Context & Legacy Architecture (V2 / V3)

The legacy PHP code has been organized into `legacy/` for historical reference:
- **`legacy/tentacle_old.php`** (v2.0): File-based state in `arrays/*.txt`.
- **`legacy/tentacle.php`** (v3.0): Mixed MySQLi/PDO attempt connecting to MySQL/Postgres. Hardcoded defunct NZBMatrix API queries.
- **`legacy/www/`**: Unfinished Smarty templates and `t3w` class.
- **`legacy/settings/`**: PHP files containing hardcoded paths and database connections.
