import os
import pytest
from tentacle.database import Database
from tentacle.library.scanner import LibraryScanner
from tentacle.models import ShowStatus


@pytest.fixture
def mock_library(tmp_path):
    db_file = tmp_path / "tentacle.db"
    db = Database(str(db_file))

    shows_dir = tmp_path / "Shows"
    shows_dir.mkdir()

    # Show 1: Active show with Season 1 & 2
    show1 = shows_dir / "Futurama"
    show1.mkdir()
    s1 = show1 / "Season 1"
    s1.mkdir()
    (s1 / "Futurama.S01E01.Space.Pilot.3000.mkv").write_text("dummy")
    (s1 / "Futurama.S01E02.mkv").write_text("dummy")
    s2 = show1 / "Season 2"
    s2.mkdir()
    (s2 / "Futurama.S02E05.mkv").write_text("dummy")

    # Show 2: Dead show with dead.txt ("hes dead jim")
    show2 = shows_dir / "Firefly"
    show2.mkdir()
    (show2 / "dead.txt").write_text("hes dead jim")
    (show2 / "Firefly.S01E01.Serenity.mp4").write_text("dummy")
    (show2 / "Firefly.S01E14.mkv").write_text("dummy")

    settings = db.get_settings()
    settings.shows_dir = str(shows_dir)
    db.save_settings(settings)

    return db, str(shows_dir)


def test_library_scanner(mock_library):
    db, shows_dir = mock_library
    scanner = LibraryScanner(db)
    shows = scanner.scan_all()

    assert len(shows) == 2

    futurama = db.get_show_by_name("Futurama")
    assert futurama is not None
    assert futurama.status == ShowStatus.ACTIVE
    assert futurama.episode_count == 3
    assert futurama.newest_season == 2
    assert futurama.newest_episode == 5

    firefly = db.get_show_by_name("Firefly")
    assert firefly is not None
    # Verified: dead.txt marks the show as ENDED!
    assert firefly.status == ShowStatus.ENDED
    assert firefly.episode_count == 2
    assert firefly.newest_season == 1
    assert firefly.newest_episode == 14
