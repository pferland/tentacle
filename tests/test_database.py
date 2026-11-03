import os
import pytest
from tentacle.database import Database
from tentacle.models import (
    AppSettings,
    DownloadStatus,
    Episode,
    IndexerConfig,
    ShowStatus,
)


@pytest.fixture
def db(tmp_path):
    db_file = tmp_path / "test_tentacle.db"
    return Database(str(db_file))


def test_settings_crud(db):
    settings = db.get_settings()
    assert settings.scan_interval == 3600

    settings.scan_interval = 1800
    settings.shows_dir = "/custom/shows"
    db.save_settings(settings)

    reloaded = db.get_settings()
    assert reloaded.scan_interval == 1800
    assert reloaded.shows_dir == "/custom/shows"


def test_shows_and_episodes(db):
    show = db.upsert_show(
        name="Doctor Who",
        path="/shows/Doctor Who",
        status=ShowStatus.ACTIVE,
    )
    assert show.id is not None
    assert show.name == "Doctor Who"

    episodes = [
        Episode(season=1, episode=1, file_name="ep1.mkv", file_path="/shows/Doctor Who/S01E01.mkv", file_size=1000),
        Episode(season=1, episode=2, file_name="ep2.mkv", file_path="/shows/Doctor Who/S01E02.mkv", file_size=1200),
        Episode(season=2, episode=1, file_name="ep3.mkv", file_path="/shows/Doctor Who/S02E01.mkv", file_size=1400),
    ]
    db.sync_episodes_for_show(show.id, episodes)

    updated_show = db.get_show(show.id)
    assert updated_show.episode_count == 3
    assert updated_show.newest_season == 2
    assert updated_show.newest_episode == 1

    stored_eps = db.get_episodes(show.id)
    assert len(stored_eps) == 3

    # Status toggle
    db.set_show_status(show.id, ShowStatus.ENDED)
    ended_show = db.get_show(show.id)
    assert ended_show.status == ShowStatus.ENDED


def test_indexers_crud(db):
    idx = IndexerConfig(
        name="TestGeek",
        url="https://api.testgeek.info",
        api_key="secret123",
        enabled=True,
        priority=1,
    )
    saved = db.save_indexer(idx)
    assert saved.id is not None
    assert saved.name == "TestGeek"

    indexers = db.get_indexers()
    assert len(indexers) == 1

    db.delete_indexer(saved.id)
    assert len(db.get_indexers()) == 0


def test_downloads_and_logs(db):
    dl = db.record_download(
        show_name="Severance",
        season=2,
        episode=1,
        title="Severance.S02E01.720p",
        indexer_name="NZBGeek",
        nzb_url="https://test/get?id=123",
    )
    assert dl.id is not None
    assert dl.status == DownloadStatus.QUEUED

    db.update_download_status(dl.id, DownloadStatus.IMPORTED)
    updated_dl = db.get_download(dl.id)
    assert updated_dl.status == DownloadStatus.IMPORTED
    assert updated_dl.completed_at is not None

    db.log("INFO", "test", "Hello World audit message")
    logs = db.get_logs()
    assert len(logs) == 1
    assert "Hello World" in logs[0].message
