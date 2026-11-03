# AGENT.md - Project Knowledge Base for Tentacle

> **Project Identity**: `tentacle` (repository named `tenticle`)  
> **Author**: Phillip Ferland (`Longbow486` <pferland@randomintervals.com>)  
> **Original Development**: ~2010–2011 (PHP 5.2/5.3 era, first Git commit February 2015)  
> **License**: GNU General Public License v2 (with GPL v3 headers in some web files)  
> **Status**: Legacy / Proof of Concept archive requiring significant refactoring for modern use.

---

## 1. Executive Summary & Purpose

Tentacle is an automated, daemonized television show episode manager, downloader, and media organizer written in PHP. It was conceived as an open-source alternative to tools like SickBeard (and precursors to modern Sonarr).

### Core Responsibilities:
1. **Library Scanning**: Recursively indexes existing television show directories and organizes episodes by season (`Show Name/Season X/Episode.ext`).
2. **Episode Gap Detection**: Analyzes current episodes to detect the newest season and episode for each active show.
3. **Usenet Indexer Search**: Queries NZBMatrix (historical Usenet indexer) via its HTTP API for subsequent episodes (`SxxExx`), and if the current season has ended, checks season + 1.
4. **Downloader Integration**: Dispatches found NZBs into SABnzbd's monitored directory and polls SABnzbd's XML API (`qstatus`) until downloads complete or fail.
5. **Post-Processing & Sorting**: Inspects completed download directories, identifies media files (filtering out `.nfo`, `.par2`, `.sfv`, samples, images), moves them to the appropriate `Season X` directory in the library, and cleans up temporary files (`rm -rf`).
6. **Playlist Generation**: Produces an ASX v3.0 XML playlist referencing all media in the library for media player consumption (e.g., VLC, Windows Media Player).
7. **State & History Management**:
   - **v2.0 (`tentacle_old.php`)**: Flat-file serialized PHP data arrays in `arrays/`.
   - **v3.0 (`tentacle.php`)**: Relational database storage (MySQL/PostgreSQL) with audit logging into a `history` table.
8. **Web Dashboard (`www/`)**: Lightweight web monitor using Smarty templates displaying daemon process status and history log entries.

---

## 2. Repository File Tree & Component Inventory

```
.
├── dead.txt                              # Show status marker ("hes dead jim")
├── LICENSE                               # GNU General Public License v3 text
├── settings/
│   ├── shows.php                         # v2 settings with Windows drive paths (Z:/...)
│   ├── shows_lnx.php                     # v2 settings with Linux mount paths (/mnt/...)
│   └── shows_sql.php                     # v3 SQL and SMTP connection credentials
├── SQL/
│   ├── mysql_tentacle_structure.sql      # MySQL schema (tables only)
│   ├── mysql_tentacle_structure_data.sql # MySQL schema + default settings seed row
│   └── postgres_tentacle_struct_data.sql # PostgreSQL schema + sequence + seed row
├── tentacle.php                          # Version 3.0 primary CLI daemon (SQL-backed)
├── tentacle_old.php                      # Version 2.0 legacy CLI daemon (file-backed)
├── todo.txt                              # Original developer task list
└── www/                                  # Web UI dashboard
    ├── img/
    │   ├── off.gif                       # Status icon: daemon stopped
    │   └── on.gif                        # Status icon: daemon running
    ├── index.php                         # Web entry point / page router
    ├── lib/
    │   ├── config.inc.php                # Web constants (DB, PID path, Smarty paths)
    │   └── t3w.class.php                 # Tentacle 3 Web class (t3w)
    ├── smarty/
    │   └── templates/
    │       ├── index.tpl                 # Main dashboard template
    │       └── procview.tpl              # Process view template
    └── template_source/
        ├── index.dwt                     # Dreamweaver template source with ASCII banner
        └── index.html                    # Static HTML mock of index page
```

### Detailed Component Descriptions:

- **`tentacle.php` (v3.0)**: Main executable CLI script. Encapsulates all scanning, downloading, NZBMatrix querying, SABnzbd polling, moving, playlist generation, and database interactions within class `tentacle`.
- **`tentacle_old.php` (v2.0)**: Predecessor script that saved state into flat text files containing serialized PHP arrays (`shows_list.txt`, `Shows_newest.txt`, `downloaded_nzbs.txt`, etc.).
- **`settings/shows_sql.php`**: Default configuration file defining `$default` array with database credentials (`sqlhosttype`, `sqlhost`, `sqluser`, `sqlpwd`, `db`) and SMTP server details.
- **`settings/shows.php` & `settings/shows_lnx.php`**: Legacy configuration files defining file paths, scan intervals, SABnzbd credentials, and NZBMatrix credentials.
- **`SQL/*.sql`**: Database schema dumps for MySQL (using MyISAM engine) and PostgreSQL (using sequences). Defines tables: `settings`, `history`, `shows_list`, `shows_details`, `Shows_newest`, `downloaded_nzbs`, `raw_playlist`, `copy_log`, `failed_copy`.
- **`dead.txt`**: A marker file containing `"hes dead jim"`. When placed in a show's root folder, Tentacle marks the show as cancelled/ended and skips scanning for new episodes.
- **`www/`**: A partial Smarty-based web application to view daemon running status (reading `/var/run/tentacle.pid`) and audit logs from MySQL.

---

## 3. Architecture & Operational Lifecycle

```
                      +-----------------------------+
                      |   CLI Invocation & Args     |
                      | (tentacle.php / $argv)      |
                      +--------------+--------------+
                                     |
                                     v
                      +-----------------------------+
                      |   Database Configuration    |
                      |   (GetSQLSettings from DB)  |
                      +--------------+--------------+
                                     |
                                     v
    +-------------------> [ Main Loop (while 1) ] <-------------------+
    |                                |                                |
    |                                v                                |
    |                 +-----------------------------+                 |
    |                 |   Scan Shows Directory      |                 |
    |                 | (recurs_dir, gen_shows_array)                 |
    |                 +--------------+--------------+                 |
    |                                |                                |
    |                                v                                |
    |                 +-----------------------------+                 |
    |                 | Extract File Types & Stats  |                 |
    |                 |   (run_file_type_stats)     |                 |
    |                 +--------------+--------------+                 |
    |                                |                                |
    |                                v                                |
    |                 +-----------------------------+                 |
    |                 | Identify Newest Episode     |                 |
    |                 |     (get_newest_files)      |                 |
    |                 +--------------+--------------+                 |
    |                                |                                |
    |                                v                                |
    |                 +-----------------------------+                 |
    |                 | Check & Fetch New Episodes  |                 |
    |                 |   (download_new, NZBMatrix) |                 |
    |                 +--------------+--------------+                 |
    |                                |                                |
    |                                v                                |
    |                 +-----------------------------+                 |
    |                 | Monitor SABnzbd Queue       |                 |
    |                 |  (download_wait_and_clean)  |                 |
    |                 +--------------+--------------+                 |
    |                                |                                |
    |                                v                                |
    |                 +-----------------------------+                 |
    |                 | Organize & Move Downloads   |                 |
    |                 |   (clean_up, copy_src_dest) |                 |
    |                 +--------------+--------------+                 |
    |                                |                                |
    +--------- Sleep (scan_int) -----+------ If --run_once: Exit -----+
```

### Main Loop Step-by-Step Breakdown:

1. **Initialization (`__construct`)**:
   - Parses CLI flags via `pars_args($argv)`.
   - Reads DB config file (`settings/shows_sql.php` or CLI `-c`/`--config`).
   - Connects to database in `GetSQLSettings()`, fetches row `id = 1` from `settings` table, and merges DB settings into `$this->settings`.
2. **Library Scan Check (`check_shows_array`)**:
   - Checks if a scan has ever been done, if `last_scan` was longer than `scan_int` (default 9000s = 2.5 hours) ago, or if `dn_flag == 1` (new episodes were downloaded).
   - If needed, invokes `gen_shows_array()`: recursively walks the `shows_dir`, filters out ignored file extensions, checks for `dead.txt`, creates a nested array of `[Show][Season][Episodes]`, serializes it, and saves it into the `shows_file` (`shows_list`) table.
3. **File Type Statistics (`run_file_type_stats`)**:
   - Counts file extensions across all indexed media files (`mkv`, `avi`, `mp4`, etc.) and records statistics in `shows_details`.
4. **Newest Episode Compilation (`get_newest_files`)**:
   - Traverses the nested array to grab the highest season and episode string for every show.
   - Saves serialized map into `Shows_newest` table.
5. **Episode Search & NZB Retrieval (`download_new`)**:
   - For each show in `newest_files`:
     - Skips shows marked dead.
     - Parses episode string matching `(?P<code>\w\d\d\w\d\d)` (e.g. `S02E05`).
     - Extracts `$season` and `$episode`.
     - Loops `$I` from `$episode + 1` to `29` looking for `S{season}E{I}`.
     - Searches NZBMatrix HTTP API:
       `http://api.nzbmatrix.com/v1.1/search.php?search=<query>&catid=41&sort=9&type=asc&username=<user>&apikey=<key>`
     - If not found in current season, loops `$neps` from `1` to `29` for next season `S{season+1}E{neps}`.
     - When found, fetches `.nzb` payload via `http://nzbmatrix.com/api-nzb-download.php?id=<id>` and writes it to:
       * Temporary backup: `$dn_nzb_tmp/<term>.nzb`
       * SABnzbd blackhole/watch directory: `$dn_dir/<term>.nzb`
     - Sets `$this->settings['dn_flag'] = 1`.
6. **Download Monitoring (`download_wait_and_clean`)**:
   - If NZBs were queued:
     - Polls SABnzbd's XML API `http://<host>:<port>/api?mode=qstatus&output=xml&apikey=<key>`.
     - Parses XML using custom parser `xml2ary()`.
     - Waits until queue `state == "IDLE"`.
     - Inspects SABnzbd's completed directory (`done_dir`) using `SAB_check_folders()` to verify output folders exist (checking for expected count and verifying no `_FAILED_` prefixes).
7. **Post-Processing & Sorting (`clean_up` & `copy_src_dest`)**:
   - For each completed folder in `done_dir`:
     - Parses show name and season from folder name (split on `+` and regex match on `SxxExx`).
     - Searches directory for target media file via `get_file()` (ignoring junk files).
     - Ensures target directory exists: `$shows_dir/$show_name/Season $S/`.
     - Copies media file into place, logs action to `copy_log` / `history`, and deletes original downloaded file.
     - Deletes the leftover unpacked download folder using `rm -rf` (`$this->rm_cmd`).
8. **Playlist Generation (`generate_playlist_array` & `generate_playlist`)**:
   - Flattens all media files across all shows into an ASX v3.0 XML playlist saved at `shows_playlist` (`Shows.asx`).

---

## 4. Command Line Interface (CLI)

Execution:
```bash
php tentacle.php [options]
```

### Supported CLI Arguments:

| Short Flag | Long Flag | Description | Default |
|---|---|---|---|
| `-c <file>` | `--config=<file>` | Path to PHP settings file containing `$default` DB config | `settings/shows_sql.php` |
| | `--run_once` | Run a single pass through the cycle and exit | `0` (daemon mode) |
| `-q <host>` | `--sqlhost=<host>` | Override database host IP or hostname | Config file value |
| `-y <user>` | `--sqluser=<user>` | Override database user (prompts for password via stdin) | Config file value |
| `-g <db>` | `--db=<db>` | Override database name | Config file value |
| `-n <sec>` | `--nzb-sleep=<sec>` | Delay in seconds between NZBMatrix API queries | `10` |
| `-s <show>` | `--skipto=<show>` | Skip all shows except this show name (debug filter) | `""` (all shows) |
| `-v` | `--verbose` | Output verbose logs to standard output | `0` (disabled) |
| | `--gen_playlist` | Scan media directory, generate ASX playlist, and exit | Disabled |
| | `--shows_dir=<dir>` | Override shows media root path | Config table value |
| | `--dn_nzb_tmp=<dir>` | Override NZB temporary backup path | Config table value |
| | `--dn_dir=<dir>` | Override SABnzbd watch directory path | Config table value |
| | `--done_dir=<dir>` | Override SABnzbd finished unsorted download path | Config table value |
| | `--failed_copy_file=<file>` | Override failed copy log / table name | Config table value |
| | `--downloaded_nzbs=<file>` | Override downloaded NZBs table name | Config table value |
| | `--shows_playlist=<file>` | Override generated ASX playlist output path | Config table value |
| `-l` | `--license` | Print GPL license and exit | N/A |
| `-h` | `--help` | Print help and argument list and exit | N/A |

---

## 5. Database Schema & State Storage

The system supports MySQL and PostgreSQL. State is loaded during bootstrap from the `settings` table (where `id = 1`).

### Tables Overview:

| Table | Purpose | Storage Pattern |
|---|---|---|
| `settings` | Daemon runtime configuration, credentials, paths, intervals | Relational single row (`id = 1`) |
| `history` | Event and audit logs (`audit`, `failure`, `copy_log`, etc.) | Relational timestamped log |
| `shows_list` | Complete recursive directory index of shows, seasons, and files | PHP `serialize()` string in `data` column |
| `shows_details` | File extension counts and metadata | PHP `serialize()` string in `data` column |
| `Shows_newest` | Array mapping show titles to their highest season/episode string | PHP `serialize()` string in `data` column |
| `downloaded_nzbs` | Active queue of downloads currently pending in SABnzbd | PHP `serialize()` string in `data` column |
| `raw_playlist` | Flattened list of all video file paths | PHP `serialize()` string in `data` column |
| `copy_log` | Records of copied files | PHP `serialize()` or text string |
| `failed_copy` | Records of failed copy operations | PHP `serialize()` or text string |

### `settings` Table Fields:

| Column | Type | Description | Example (Linux) |
|---|---|---|---|
| `id` | `int` | Primary key | `1` |
| `dn_flag` | `tinyint` | Flag indicating new downloads pending/completed | `1` |
| `scan_int` | `int` | Interval between scans in seconds | `9000` (2.5 hrs) |
| `FAILED` | `varchar(255)` | Folder name prefix for failed downloads | `_FAILED_` |
| `shows_dir` | `varchar(255)` | Root directory of media library | `/mnt/media/Shows/` |
| `dn_nzb_tmp` | `varchar(255)` | Directory for temporary NZB storage | `/mnt/data/NZB_TMP/` |
| `dn_dir` | `varchar(255)` | SABnzbd watch / blackhole folder | `/mnt/temp/NZB_AutoDownload/` |
| `done_dir` | `varchar(255)` | SABnzbd completed download folder | `/mnt/temp/NZB_Finished_Unsorted/` |
| `faild_copy_log` | `varchar(255)` | Table/log name for copy failures | `failed_copy` |
| `copy_log` | `varchar(255)` | Table/log name for successful copies | `copy_log` |
| `failed_file` | `varchar(255)` | Table/log name for failed shows | `failed_copy` |
| `failed_copy_file`| `varchar(255)` | Table/log name for failed copies | `failed_copy` |
| `shows_file` | `varchar(255)` | Table name for serialized shows tree | `shows_list` |
| `shows_details` | `varchar(255)` | Table name for file extension details | `shows_details` |
| `shows_newest` | `varchar(255)` | Table name for newest episode map | `Shows_newest` |
| `downloaded_nzbs`| `varchar(255)` | Table name for pending NZBs | `downloaded_nzbs` |
| `raw_playlist` | `varchar(255)` | Table name for raw playlist entries | `raw_playlist` |
| `shows_playlist` | `varchar(255)` | Path to output ASX playlist | `/mnt/media/Shows.asx` |
| `NZB_USER` | `varchar(255)` | NZBMatrix username | (user string) |
| `NZB_API_KEY` | `varchar(255)` | NZBMatrix API key | (32-char hex) |
| `SAB_API_KEY` | `varchar(255)` | SABnzbd API key | (32-char hex) |
| `SAB_Host` | `varchar(255)` | SABnzbd IP or hostname | `192.168.1.15` |
| `SAB_Port` | `int` | SABnzbd port number | `8080` |
| `last_scan` | `int` | Unix timestamp of last media directory scan | `1295934020` |

---

## 6. External Integrations & Data Formats

### 1. NZBMatrix API (Defunct)
- **Status**: **Permanently Defunct** (shut down in December 2012).
- **Search Query**:
  `http://api.nzbmatrix.com/v1.1/search.php?search=<query>&catid=41&sort=9&type=asc&username=<user>&apikey=<key>`
  - `catid=41`: TV shows category.
  - `sort=9`: Sort order.
- **Download Query**:
  `http://nzbmatrix.com/api-nzb-download.php?id=<nzbid>&username=<user>&apikey=<key>`
- **Error Handling**: `check_nzb_error()` parsed strings like `error:invalid_login`, `error:invalid_api`, `error:vip_only`, `error:nothing_found`, `error:API_RATE_LIMIT_REACHED`, `error:please_wait_X`.

### 2. SABnzbd API
- **Endpoint**:
  `http://<host>:<port>/api?mode=qstatus&output=xml&apikey=<key>`
- **Parser**: Handcrafted XML parser function `xml2ary()` parses XML into a nested PHP array structure (`$SAB_Status['queue']['_c']['state']['_v']`).
- **State Check**: Polls until queue status equals `"IDLE"`.
- **Output Inspection**: Checks `$done_dir` for folders matching downloaded release names. If download failed, SABnzbd prepends `_FAILED_`.

### 3. Media Filtering & Skipped Extensions
Function `check_for_skip($file)` explicitly skips non-media extensions:
- Image formats: `tbn`, `jpg`, `png`, `gif`, `db`
- Information & text: `nfo`, `diz`, `txt`, `rtf`, `html`, `htm`
- Metadata & archives: `par2`, `sfv`, `srr`, `srt`, `zip`, `nzb`, `torrent`
- System/OS junk: `ds_store`, `dat`, `lnk`, `vlc media player`

### 4. Playlist Output Format (ASX v3.0)
Generates an XML Advanced Stream Redirector (.asx) file:
```xml
<asx version = "3.0" >
	<entry>
		<title>Show Name S01E01.mkv</title>
		<ref href = "/mnt/media/Shows/Show Name/Season 1/Show Name S01E01.mkv" />
	</entry>
</asx>
```

### 5. Dead Show Marker (`dead.txt`)
- A file named `dead.txt` placed in a show folder indicates the show is finished or cancelled.
- Content: `"hes dead jim"` (Star Trek reference).
- When Tentacle encounters `dead.txt` during directory scanning, it assigns `$array['dead'] = "its dead jim"`.
- `get_newest_files()` checks `if(!@$a['dead'])` and skips downloading new episodes for that show.

---

## 7. Web Dashboard (`www/`) Architecture

The `www/` directory contains an unfinished administrative and monitoring interface:

- **`www/index.php`**:
  - Handles routing via `$_GET['page']`:
    * `index`: Calls `$tw3->grab_index()`
    * `status`: Calls `$tw3->check_proc()`
- **`www/lib/config.inc.php`**:
  - Defines DB connection constants, PID file location (`/var/run/tentacle.pid`), Smarty directory (`/usr/local/lib/php/smarty/`), and Web root (`/var/www/tentacle/`).
- **`www/lib/t3w.class.php`**:
  - Instantiates `mysqli` connection.
  - Instantiates Smarty template engine.
  - Reads `/var/run/tentacle.pid` and runs `exec("ps vp $pid")` to test if the daemon process is active, setting status icon (`on.gif` / `off.gif`).
  - Reads `SELECT * FROM history` to populate audit table on `index.tpl`.

---

## 8. Critical Bugs, Quirks & Technical Debt

Any developer or agent working on this codebase should be aware of several high-priority bugs and inconsistencies:

### 1. Fatal Class Name Mismatch in Web UI
In `www/index.php`:
```php
require('lib/t3w.class.php');
$tw3 = new tentacle_http(); // BUG: Class is defined as `class t3w` in t3w.class.php!
```
Calling `new tentacle_http()` triggers a PHP fatal `Class 'tentacle_http' not found`.

### 2. Broken PDO vs MySQLi Hybrid in `tentacle.php`
`GetSQLSettings()` mixes PDO and MySQLi APIs incompatibly:
```php
$this->conn = new PDO($this->settings['sqlhosttype'].':dbname='.$this->settings['db'].';host='.$this->settings['sqlhost'], $this->settings['sqlpwd'], $this->settings['sqluser']);
// BUG 1: PDO constructor parameter order is ($dsn, $username, $password). Here password and user are reversed!
if(mysqli_connect_errno()) // BUG 2: mysqli_connect_errno() checks mysqli, not PDO!
$result = $this->conn->query("SELECT * FROM `settings` where `id`='1'", 1);
$settings = $result->fetch_array(1); // BUG 3: fetch_array() does not exist on PDOStatement!
```

### 3. Flawed PDO Fetching in `get_data_from_sql()`
```php
$result = $this->conn->query("SELECT * FROM `$table` ORDER BY `id` DESC LIMIT 1", 1);
if(!empty($result)) // BUG: PDO query returns a PDOStatement object, so !empty() is always true!
{
    $error = $this->conn->errorInfo();
    if($this->verbose){echo "Failed to Fetch data from `$table` (".time().")\r\n".$error[2];}
} else {
    return unserialize($result[0]['data']); // BUG: PDOStatement cannot be array-indexed like $result[0]!
}
```

### 4. Malformed Prepared Statement in `log_write()`
```php
$prep = $this->conn->prepare("INSERT INTO `history` (`id` ,`time_stamp` ,`mesg` ,`catagory`) VALUES (NULL , '?', '?', '?')");
// BUG 1: PDO placeholders must not be enclosed in quotes ('?').
$prep->execute( array( date('Y-m-d H:i:s'), $this->conn->quote($mesg), $this->conn->quote($dest) ) );
// BUG 2: Passing $this->conn->quote() into execute parameters double-escapes/quotes the string.
```

### 5. Missing Scope in `nzb_search()`
In `tentacle.php`:
```php
function nzb_search($NZBSearchResult) {
    ...
    $DL_URL = $NZB_DL_URL.$id.$NZB_KEY_URL; // BUG: $NZB_DL_URL and $NZB_KEY_URL are undefined in this scope!
```

### 6. Unscoped Method Calls in `download_new()`
Lines 619, 622, 626, 629 call `set_data_to_sql(...)` as a global function rather than `$this->set_data_to_sql(...)`.

### 7. Database Name Hardcoding
`tentacle.php` hardcodes database name `tentacle`:
```php
$this->conn->query("UPDATE `tentacle`.`settings` SET `dn_flag` = ...");
```
Meanwhile, `shows_sql.php` defaults the database name to `tenticle` (with an `i`).

### 8. Defunct Indexer API
NZBMatrix is permanently offline. Running `download_new()` will always result in network/HTTP request failures.

### 9. Naive Episode Number Increment
The episode search assumes sequential episodes and tests strictly up to `29`:
```php
for($I=$nexte; $I<30; $I++)
```
It does not handle anime, shows with >30 episodes per season, daily shows (`2024-05-01`), or alternative numbering schemes (`1x05`).

---

## 9. Modernization & Replacement Roadmap

If this project is to be revived or refactored:

1. **Replace NZBMatrix with Modern Indexer Standard**:
   - Implement Newznab / Torznab API client compatible with Prowlarr, Jackett, NZBGeek, etc.
   - Support both Usenet (NZBs) and BitTorrent (`.torrent` / magnet links), fulfilling the original goal noted in `todo.txt`.
2. **Modernize SABnzbd Integration**:
   - Switch from legacy `mode=qstatus&output=xml` to SABnzbd's modern JSON API: `mode=queue&output=json` and `mode=history&output=json`.
3. **Refactor Database Layer**:
   - Cleanly standardize on PHP PDO with prepared statements.
   - Normalize the database: replace serialized PHP blob columns (`shows_list`, `Shows_newest`) with proper relational tables:
     * `shows (id, name, path, status, last_scanned)`
     * `episodes (id, show_id, season, episode, file_path, file_size, format)`
4. **Clean OOP & CLI Framework**:
   - Split monolithic `tentacle.php` into clean PSR-4 classes:
     * `Tentacle\Scanner\DirectoryScanner`
     * `Tentacle\Indexer\NewznabClient`
     * `Tentacle\Downloader\SabnzbdClient`
     * `Tentacle\Organizer\MediaOrganizer`
     * `Tentacle\Playlist\AsxGenerator`
5. **Modern PHP Standards**:
   - Upgrade syntax to modern PHP 8.x (typed properties, constructor promotion, strict typing `declare(strict_types=1);`, Composer dependency management).
6. **Web Interface Upgrade**:
   - Replace archaic Smarty 2/3 setup with a clean REST API / modern frontend or lightweight microframework (Slim / Symfony).

---

## 10. Developer Quick Reference

### Running CLI in Test Mode:
```bash
# Print help
php tentacle.php --help

# Generate playlist only and exit
php tentacle.php --gen_playlist

# Run a single scan pass in verbose mode with custom DB config
php tentacle.php --config=settings/shows_sql.php --run_once --verbose
```

### Checking Syntax:
```bash
php -l tentacle.php
php -l tentacle_old.php
php -l www/index.php
php -l www/lib/t3w.class.php
```

### Database Tables Summary:
- `settings`: Configuration
- `history`: Daemon log
- `shows_list`: Serialized directory index
- `Shows_newest`: Serialized newest episode per show
- `downloaded_nzbs`: Serialized pending downloads
- `shows_details`: Serialized file extension breakdown
- `copy_log` / `failed_copy`: Post-processing log
