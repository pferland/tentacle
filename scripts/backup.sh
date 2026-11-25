#!/usr/bin/env bash
# ==============================================================================
# Tentacle V4 - Application Data & Configuration Backup Script
#
# Creates an atomic, verified snapshot of the SQLite database (handling WAL mode),
# encryption keys, playlist feeds, systemd service units, and Apache vhost configs.
#
# Target Directory Format:
#   /backups/tentacle/<yyyy-mm-dd>/
#
# Usage:
#   ./scripts/backup.sh [OPTIONS]
#
# Options:
#   -d, --base-dir <PATH>   Base directory for backups (default: /backups/tentacle)
#   -k, --keep-days <DAYS>  Prune backup date directories older than N days (default: 14)
#   --dry-run               Simulate backup actions without modifying disk
#   -h, --help              Show this help message and exit
# ==============================================================================

set -euo pipefail

SOURCE="${BASH_SOURCE[0]}"
while [ -h "$SOURCE" ]; do
    DIR="$(cd -P "$(dirname "$SOURCE")" && pwd)"
    SOURCE="$(readlink "$SOURCE")"
    [[ $SOURCE != /* ]] && SOURCE="$DIR/$SOURCE"
done
SCRIPT_DIR="$(cd -P "$(dirname "$SOURCE")" && pwd)"
REPO_ROOT="$(cd -P "${SCRIPT_DIR}/.." && pwd)"

DEFAULT_BASE_DIR="/backups/tentacle"
BASE_DIR="${BACKUP_BASE_DIR:-$DEFAULT_BASE_DIR}"
KEEP_DAYS="${RETENTION_DAYS:-14}"
DRY_RUN=false

DATE_STAMP="$(date +%Y-%m-%d)"
TIME_STAMP="$(date +%Y%m%d_%H%M%S)"

BOLD="\033[1m"
GREEN="\033[0;32m"
YELLOW="\033[0;33m"
RED="\033[0;31m"
CYAN="\033[0;36m"
RESET="\033[0m"

log_info()  { echo -e "[$(date '+%Y-%m-%d %H:%M:%S')] ${CYAN}${BOLD}[INFO]${RESET} $*"; }
log_ok()    { echo -e "[$(date '+%Y-%m-%d %H:%M:%S')] ${GREEN}${BOLD}[OK]${RESET} $*"; }
log_warn()  { echo -e "[$(date '+%Y-%m-%d %H:%M:%S')] ${YELLOW}${BOLD}[WARN]${RESET} $*" >&2; }
log_error() { echo -e "[$(date '+%Y-%m-%d %H:%M:%S')] ${RED}${BOLD}[ERROR]${RESET} $*" >&2; }

usage() {
    cat << HELP
Tentacle V4 - Backup Utility

Usage: $(basename "$0") [OPTIONS]

Options:
  -d, --base-dir <PATH>   Base backup directory (default: /backups/tentacle)
  -k, --keep-days <DAYS>  Delete date directories older than <DAYS> days (default: 14)
  --dry-run               Show what would be backed up without writing files
  -h, --help              Display this help message and exit

Destination format:
  <base-dir>/<yyyy-mm-dd>/tentacle_backup_<timestamp>.tar.gz
HELP
    exit 0
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        -d|--base-dir)
            BASE_DIR="$2"
            shift 2
            ;;
        -k|--keep-days)
            KEEP_DAYS="$2"
            shift 2
            ;;
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        -h|--help)
            usage
            ;;
        *)
            log_error "Unknown argument: $1"
            usage
            ;;
    esac
done

TARGET_DIR="${BASE_DIR}/${DATE_STAMP}"

log_info "Initiating Tentacle V4 backup..."
log_info "Repository root:  ${REPO_ROOT}"
log_info "Target directory: ${TARGET_DIR}"

if [[ "$DRY_RUN" == true ]]; then
    log_warn "Running in --dry-run mode. No files will be created or modified."
fi

PYTHON_BIN=""
if [[ -x "${REPO_ROOT}/.venv/bin/python" ]]; then
    PYTHON_BIN="${REPO_ROOT}/.venv/bin/python"
elif command -v python3 >/dev/null 2>&1; then
    PYTHON_BIN="python3"
else
    log_error "Python interpreter not found."
    exit 1
fi

log_info "Using Python runtime: ${PYTHON_BIN}"

DB_SOURCE="${REPO_ROOT}/tentacle.db"
KEY_SOURCE="${REPO_ROOT}/tentacle.key"

if [[ "$DRY_RUN" == true ]]; then
    log_info "Dry-run plan:"
    log_info "  - Would create destination directory: ${TARGET_DIR}"
    if [[ -f "$DB_SOURCE" ]]; then
        log_info "  - Would backup SQLite DB: ${DB_SOURCE} -> ${TARGET_DIR}/db_${TIME_STAMP}.sqlite3"
    fi
    if [[ -f "$KEY_SOURCE" ]]; then
        log_info "  - Would backup encryption key: ${KEY_SOURCE} -> ${TARGET_DIR}/tentacle_${TIME_STAMP}.key"
    fi
    log_info "  - Would backup playlist feeds: Shows.asx, Shows.m3u8"
    log_info "  - Would backup service configs: systemd unit, Apache vhost"
    log_info "  - Would create tarball: ${TARGET_DIR}/tentacle_backup_${TIME_STAMP}.tar.gz"
    log_info "  - Would generate SHA256 checksums and manifest"
    if [[ -n "$KEEP_DAYS" && "$KEEP_DAYS" -gt 0 ]]; then
        log_info "  - Would prune backups older than ${KEEP_DAYS} days in ${BASE_DIR}"
    fi
    log_ok "Dry-run completed successfully."
    exit 0
fi

mkdir -p "${TARGET_DIR}"
chmod 750 "${TARGET_DIR}"

TEMP_STAGE="$(mktemp -d -p "${TARGET_DIR}" .stage_XXXXXX)"
chmod 700 "${TEMP_STAGE}"
trap 'rm -rf "${TEMP_STAGE}"' EXIT

DB_BACKUP_NAME="db_${TIME_STAMP}.sqlite3"
KEY_BACKUP_NAME="tentacle_${TIME_STAMP}.key"
ASX_BACKUP_NAME="Shows_${TIME_STAMP}.asx"
M3U_BACKUP_NAME="Shows_${TIME_STAMP}.m3u8"
SYSTEMD_BACKUP_NAME="systemd_service_${TIME_STAMP}.backup"
APACHE_BACKUP_NAME="apache_vhost_${TIME_STAMP}.backup"
MANIFEST_NAME="manifest_${TIME_STAMP}.txt"
TARBALL_NAME="tentacle_backup_${TIME_STAMP}.tar.gz"
CHECKSUM_NAME="SHA256SUMS_${TIME_STAMP}.txt"

# 1. SQLite Online Backup & Integrity Verification (WAL-safe)
if [[ -f "$DB_SOURCE" ]]; then
    log_info "Creating consistent SQLite online backup..."
    $PYTHON_BIN - << PYEOF
import sqlite3
import sys

src_path = "${DB_SOURCE}"
dst_path = "${TEMP_STAGE}/${DB_BACKUP_NAME}"

try:
    src = sqlite3.connect(src_path)
    dst = sqlite3.connect(dst_path)
    with dst:
        src.backup(dst, pages=100)
    dst.close()
    src.close()
except Exception as e:
    sys.stderr.write(f"SQLite online backup failed: {e}\\n")
    sys.exit(1)

check_conn = sqlite3.connect(dst_path)
cursor = check_conn.cursor()
cursor.execute("PRAGMA integrity_check;")
res = cursor.fetchone()
check_conn.close()

if not res or res[0] != "ok":
    sys.stderr.write(f"Integrity check failed: {res}\\n")
    sys.exit(2)
PYEOF
    log_ok "SQLite backup passed PRAGMA integrity_check."
fi

# 2. Key file & Playlists
if [[ -f "$KEY_SOURCE" ]]; then
    cp -p "$KEY_SOURCE" "${TEMP_STAGE}/${KEY_BACKUP_NAME}"
    chmod 600 "${TEMP_STAGE}/${KEY_BACKUP_NAME}"
    log_ok "Captured encryption key (mode 0600)"
fi

for feed in Shows.asx Shows.m3u8; do
    if [[ -f "${REPO_ROOT}/$feed" ]]; then
        cp -p "${REPO_ROOT}/$feed" "${TEMP_STAGE}/"
        log_ok "Captured feed: $feed"
    fi
done

# 3. Systemd and Apache configs
SYSTEMD_SRC="/etc/systemd/system/tentacle.service"
if [[ -r "$SYSTEMD_SRC" ]]; then
    cp -p "$SYSTEMD_SRC" "${TEMP_STAGE}/${SYSTEMD_BACKUP_NAME}"
    log_ok "Captured systemd unit: ${SYSTEMD_SRC}"
elif [[ -r "${REPO_ROOT}/tentacle.service" ]]; then
    cp -p "${REPO_ROOT}/tentacle.service" "${TEMP_STAGE}/${SYSTEMD_BACKUP_NAME}"
    log_ok "Captured repository systemd unit"
fi

APACHE_SRC="/etc/apache2/sites-available/050-tenticle.home.randomintervals.com.conf"
if [[ -r "$APACHE_SRC" ]]; then
    cp -p "$APACHE_SRC" "${TEMP_STAGE}/${APACHE_BACKUP_NAME}"
    log_ok "Captured Apache vhost: ${APACHE_SRC}"
fi

if [[ -f "${REPO_ROOT}/pyproject.toml" ]]; then
    cp -p "${REPO_ROOT}/pyproject.toml" "${TEMP_STAGE}/pyproject_${TIME_STAMP}.toml"
fi

# 4. Manifest
GIT_REV="unknown"
GIT_BRANCH="unknown"
GIT_STATUS="clean"
if command -v git >/dev/null 2>&1 && [[ -d "${REPO_ROOT}/.git" ]]; then
    GIT_REV="$(git -C "${REPO_ROOT}" rev-parse HEAD 2>/dev/null || echo "unknown")"
    GIT_BRANCH="$(git -C "${REPO_ROOT}" rev-parse --abbrev-ref HEAD 2>/dev/null || echo "unknown")"
    if [[ -n "$(git -C "${REPO_ROOT}" status --porcelain 2>/dev/null)" ]]; then
        GIT_STATUS="dirty"
    fi
fi

cat << MANIFEST > "${TEMP_STAGE}/${MANIFEST_NAME}"
================================================================================
TENTACLE V4 - BACKUP MANIFEST
================================================================================
Timestamp:         ${TIME_STAMP} (${DATE_STAMP})
Hostname:          $(hostname -f 2>/dev/null || hostname)
Executing User:    $(id -un) (UID: $(id -u), GID: $(id -g))
Repo Root:         ${REPO_ROOT}
Git Branch:        ${GIT_BRANCH}
Git Commit:        ${GIT_REV}
Git Tree:          ${GIT_STATUS}
Python Version:    $($PYTHON_BIN -c "import sys; print(sys.version.split()[0])" 2>/dev/null || echo "unknown")

Included Artifacts:
$(ls -lh "${TEMP_STAGE}" | tail -n +2 | awk '{print "  " $9, "(" $5 ")"}')
================================================================================
MANIFEST

log_ok "Manifest generated."

# 5. Build Tarball and Checksums
(
    cd "${TEMP_STAGE}"
    tar -czf "${TARGET_DIR}/${TARBALL_NAME}" *
    chmod 600 "${TARGET_DIR}/${TARBALL_NAME}"
)
log_ok "Created compressed tarball: ${TARGET_DIR}/${TARBALL_NAME}"

for item in "${TEMP_STAGE}"/*; do
    if [[ -f "$item" ]]; then
        cp -p "$item" "${TARGET_DIR}/"
    fi
done

(
    cd "${TARGET_DIR}"
    ln -sf "${TARBALL_NAME}" "latest_backup.tar.gz"
    [[ -f "${DB_BACKUP_NAME}" ]] && ln -sf "${DB_BACKUP_NAME}" "latest_db.sqlite3"
    [[ -f "${MANIFEST_NAME}" ]] && ln -sf "${MANIFEST_NAME}" "latest_manifest.txt"
)

(
    cd "${TARGET_DIR}"
    sha256sum         "${TARBALL_NAME}"         ${DB_BACKUP_NAME:+"${DB_BACKUP_NAME}"}         ${KEY_BACKUP_NAME:+"${KEY_BACKUP_NAME}"}         "${MANIFEST_NAME}"         > "${CHECKSUM_NAME}" 2>/dev/null || true
    chmod 644 "${CHECKSUM_NAME}"
    ln -sf "${CHECKSUM_NAME}" "latest_SHA256SUMS.txt"
)
log_ok "SHA256 checksums written to ${TARGET_DIR}/${CHECKSUM_NAME}"

# 6. Retention Pruning
if [[ -n "$KEEP_DAYS" && "$KEEP_DAYS" -gt 0 ]]; then
    log_info "Checking for backups older than ${KEEP_DAYS} days in ${BASE_DIR}..."
    find "${BASE_DIR}" -mindepth 1 -maxdepth 1 -type d -name "20[0-9][0-9]-[0-1][0-9]-[0-3][0-9]" -mtime "+${KEEP_DAYS}" | while read -r old_dir; do
        log_info "Pruning expired backup directory: ${old_dir}"
        rm -rf "${old_dir}"
    done
fi

log_ok "======================================================================"
log_ok "Tentacle V4 backup completed successfully!"
log_ok "Destination: ${TARGET_DIR}"
log_ok "Tarball:     ${TARGET_DIR}/${TARBALL_NAME} ($(du -h "${TARGET_DIR}/${TARBALL_NAME}" | cut -f1))"
log_ok "Checksum:    ${TARGET_DIR}/${CHECKSUM_NAME}"
log_ok "======================================================================"
exit 0
