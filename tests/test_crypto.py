import os
import sqlite3
import stat
import pytest
from tentacle.crypto import CryptoManager, ENCRYPTED_PREFIX
from tentacle.database import Database
from tentacle.models import AppSettings, DownloaderConfig, IndexerConfig, IndexerType


def test_crypto_manager(tmp_path):
    key_file = tmp_path / "tentacle.key"
    crypto = CryptoManager(str(key_file))

    # Verify key was created and has 0600 permissions
    assert os.path.exists(key_file)
    file_stat = os.stat(key_file)
    assert bool(file_stat.st_mode & stat.S_IRUSR)  # user read
    assert bool(file_stat.st_mode & stat.S_IWUSR)  # user write
    assert not bool(file_stat.st_mode & stat.S_IRWXO)  # other no permissions

    # Test encrypt & decrypt
    original = "my_easynews_user:super_secret_password"
    encrypted = crypto.encrypt(original)

    assert encrypted.startswith(ENCRYPTED_PREFIX)
    assert original not in encrypted

    decrypted = crypto.decrypt(encrypted)
    assert decrypted == original

    # Test empty & plaintext fallback
    assert crypto.encrypt("") == ""
    assert crypto.decrypt("") == ""
    assert crypto.decrypt("legacy_plaintext_key") == "legacy_plaintext_key"


def test_database_encryption_at_rest(tmp_path):
    db_file = tmp_path / "tentacle.db"
    key_file = tmp_path / "tentacle.key"

    db = Database(str(db_file), str(key_file))

    # 1. Save indexer with credentials
    raw_creds = "easynews_user:my_secret_pass"
    idx = IndexerConfig(
        name="EasyNews",
        type=IndexerType.EASYNEWS,
        url="https://members.easynews.com/2.0/search/solr-search/advanced",
        api_key=raw_creds,
    )
    saved = db.save_indexer(idx)

    # 2. Inspect raw SQLite table directly
    conn = sqlite3.connect(str(db_file))
    cur = conn.cursor()
    cur.execute("SELECT api_key FROM indexers WHERE id = ?", (saved.id,))
    raw_db_value = cur.fetchone()[0]
    conn.close()

    # Verify value is encrypted on disk
    assert raw_db_value.startswith(ENCRYPTED_PREFIX)
    assert raw_creds not in raw_db_value

    # 3. Verify clean transparent decryption through application layer
    retrieved = db.get_indexer(saved.id)
    assert retrieved.api_key == raw_creds

    # 4. Verify Downloader settings encryption at rest
    settings = db.get_settings()
    settings.downloader.api_key = "sab_super_secret_123"
    db.save_settings(settings)

    # Inspect raw settings table
    conn = sqlite3.connect(str(db_file))
    cur = conn.cursor()
    cur.execute("SELECT value FROM settings WHERE key = 'app_settings'")
    raw_settings_json = cur.fetchone()[0]
    conn.close()

    # Raw DB should NOT contain the secret in plaintext
    assert "sab_super_secret_123" not in raw_settings_json
    assert ENCRYPTED_PREFIX in raw_settings_json

    # Decrypted through get_settings
    loaded_settings = db.get_settings()
    assert loaded_settings.downloader.api_key == "sab_super_secret_123"
