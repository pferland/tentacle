import os
import pytest
from tentacle.database import Database
from tentacle.library.organizer import MediaOrganizer
from tentacle.models import DownloadStatus


@pytest.fixture
def mock_env(tmp_path):
    db_file = tmp_path / "tentacle.db"
    db = Database(str(db_file))

    shows_dir = tmp_path / "Shows"
    shows_dir.mkdir()
    completed_dir = tmp_path / "completed"
    completed_dir.mkdir()

    # Pre-register show in DB
    db.upsert_show("Futurama", str(shows_dir / "Futurama"))

    # Record download in DB
    db.record_download(
        show_name="Futurama",
        season=3,
        episode=1,
        title="Futurama.S03E01.720p.HDTV",
        indexer_name="NZBGeek",
        nzb_url="http://fake/1",
        status=DownloadStatus.DOWNLOADING,
    )

    settings = db.get_settings()
    settings.shows_dir = str(shows_dir)
    settings.completed_dir = str(completed_dir)
    db.save_settings(settings)

    return db, str(shows_dir), str(completed_dir)


def test_media_organizer(mock_env):
    db, shows_dir, completed_dir = mock_env
    organizer = MediaOrganizer(db)

    # Create completed download release directory with video + junk files
    release_dir = os.path.join(completed_dir, "Futurama.S03E01.720p.HDTV")
    os.makedirs(release_dir, exist_ok=True)
    video_file = os.path.join(release_dir, "Futurama.S03E01.mkv")
    with open(video_file, "wb") as f:
        f.write(b"x" * 1024)
    # Junk files that should be cleaned up
    with open(os.path.join(release_dir, "release.nfo"), "w") as f:
        f.write("junk nfo")
    with open(os.path.join(release_dir, "checksum.sfv"), "w") as f:
        f.write("checksum")

    imported = organizer.organize_completed()
    assert imported == 1

    # Verify video was moved to Season 3
    dest_path = os.path.join(shows_dir, "Futurama", "Season 3", "Futurama.S03E01.mkv")
    assert os.path.exists(dest_path)

    # Verify release directory was removed
    assert not os.path.exists(release_dir)

    # Verify download record marked as IMPORTED
    downloads = db.get_downloads()
    assert len(downloads) == 1
    assert downloads[0].status == DownloadStatus.IMPORTED
