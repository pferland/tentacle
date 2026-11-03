import os
import pytest
from tentacle.database import Database
from tentacle.library.playlist import PlaylistGenerator
from tentacle.models import Episode


@pytest.fixture
def mock_db_with_episodes(tmp_path):
    db_file = tmp_path / "tentacle.db"
    db = Database(str(db_file))

    show = db.upsert_show("The Expanse", "/media/The Expanse")
    episodes = [
        Episode(season=1, episode=1, file_name="S01E01.mkv", file_path="/media/The Expanse/Season 1/S01E01.mkv"),
        Episode(season=1, episode=2, file_name="S01E02.mkv", file_path="/media/The Expanse/Season 1/S01E02.mkv"),
    ]
    db.sync_episodes_for_show(show.id, episodes)

    asx_file = tmp_path / "Shows.asx"
    m3u8_file = tmp_path / "Shows.m3u8"

    settings = db.get_settings()
    settings.playlist_asx_path = str(asx_file)
    settings.playlist_m3u8_path = str(m3u8_file)
    db.save_settings(settings)

    return db, str(asx_file), str(m3u8_file)


def test_playlist_generator(mock_db_with_episodes):
    db, asx_path, m3u8_path = mock_db_with_episodes
    generator = PlaylistGenerator(db)
    generator.generate_all()

    # Verify ASX
    assert os.path.exists(asx_path)
    with open(asx_path, "r", encoding="utf-8") as f:
        asx_content = f.read()
    assert '<asx version = "3.0" >' in asx_content
    assert "The Expanse - S01E01" in asx_content
    assert "</asx>" in asx_content

    # Verify M3U8
    assert os.path.exists(m3u8_path)
    with open(m3u8_path, "r", encoding="utf-8") as f:
        m3u8_content = f.read()
    assert "#EXTM3U" in m3u8_content
    assert "#EXTINF:-1,The Expanse - S01E01" in m3u8_content
    assert "/media/The Expanse/Season 1/S01E01.mkv" in m3u8_content
