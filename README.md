# Tentacle V4 🐙

> **Automated TV Show Tracker, UseNet Downloader & Media Organizer**  
> *Completely re-written in Python with a modern WebUI and configurable UseNet providers.*

Tentacle monitors your television library, tracks upcoming and missing episodes, searches configured UseNet indexers (via the Newznab/Torznab standard), sends releases to your downloader (SABnzbd or Blackhole watch directory), organizes completed video files into clean `Show/Season X/Episode.ext` folder structures, and generates playlists (ASX and M3U8).

---

## What's New in V4

- **Complete Python Rewrite**: Modern, typed, asynchronous Python codebase replacing legacy PHP5 and flat files.
- **Configurable UseNet Providers**: NZBMatrix is permanently defunct; V4 supports any Newznab-compatible indexer with built-in presets (NZBGeek, NZBPlanet, DogNZB, DrunkenSlug, Tabula Rasa, Prowlarr) and custom API endpoints.
- **Modern Responsive WebUI**: Manage shows, trigger scans, configure providers, monitor downloads, and inspect system logs with a dark-mode interface built on FastAPI and Tailwind CSS.
- **Downloader Flexibility**: Supports modern SABnzbd JSON API and directory-based Blackhole watch folders.
- **Robust Media Organizing**: Intelligent episode parsing (`S01E02`, `1x02`, multi-part), junk file filtering (`.nfo`, `.par2`, `.sfv`, samples), safe post-processing, and automatic cleanup.
- **Star Trek "dead.txt" Support**: Preserves the classic marker file (`dead.txt` containing `"hes dead jim"`) to mark finished or cancelled shows, plus UI-based status toggling.
- **Dual Playlists**: Generates both Windows Media ASX v3.0 and modern extended M3U8 playlists for media players like VLC, Infuse, and Kodi.

---

## Quick Start

### 1. Requirements
- Python 3.10 or newer

### 2. Installation
```bash
# Clone the repository
git clone https://github.com/pferland/tenticle.git
cd tenticle
git checkout v4

# Create virtual environment and install dependencies
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 3. Launching the Web UI & Daemon
```bash
# Run web interface and background daemon (default port 8080)
python3 -m tentacle web --host 0.0.0.0 --port 8080
```
Open [http://localhost:8080](http://localhost:8080) in your browser.

---

## CLI Commands

You can run Tentacle headless or trigger manual operations from the terminal:

```bash
# Start Web UI and background scheduler
python -m tentacle web

# Scan media directory and list detected shows & episodes
python -m tentacle scan

# Search configured UseNet providers for upcoming episodes
python -m tentacle search

# Process and organize completed downloads
python -m tentacle organize

# Re-generate ASX and M3U8 playlists
python -m tentacle playlist

# Run a single complete cycle and exit
python -m tentacle run-once
```

---

## Configuration & UseNet Providers

From the **UseNet Providers** tab in the WebUI:
1. Click **Add Provider**.
2. Select a preset (e.g. *NZBGeek*, *NZBPlanet*, *DogNZB*, *DrunkenSlug*, *Prowlarr*) or select *Custom Newznab Provider*.
3. Enter your provider API Key.
4. Click **Test Connection** to verify credentials.
5. Save the provider.

From the **Settings** tab:
- **Shows Media Directory**: Root folder containing your television shows.
- **Completed Downloads Directory**: Directory where your downloader saves finished files.
- **Watch Directory**: Folder monitored for `.nzb` files (if using Blackhole).
- **Downloader**: Choose between SABnzbd (enter Host, Port, and API Key) or Blackhole.
- **Scan Interval**: Frequency of background library checks (default 3600 seconds).

---

## Running as a Systemd Service

Tentacle includes a pre-configured unit file [`tentacle.service`](tentacle.service) for continuous background execution:

```bash
# 1. Copy the service unit to systemd directory
sudo cp tentacle.service /etc/systemd/system/

# 2. Reload systemd daemon
sudo systemctl daemon-reload

# 3. Enable service to start automatically on boot and start it now
sudo systemctl enable --now tentacle.service

# 4. Check status
sudo systemctl status tentacle.service

# 5. View live logs
journalctl -u tentacle.service -f
```

---

## License

This project is licensed under the **GNU General Public License v3 (GPLv3)**. See [LICENSE](LICENSE) for details.
