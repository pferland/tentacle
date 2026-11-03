import os
import pytest
from tentacle.downloader.blackhole import BlackholeDownloader
from tentacle.downloader.manager import DownloaderManager
from tentacle.downloader.sabnzbd import SabnzbdDownloader
from tentacle.models import DownloaderConfig, DownloaderType


@pytest.mark.asyncio
async def test_blackhole_downloader(tmp_path):
    watch = tmp_path / "watch"
    completed = tmp_path / "completed"

    config = DownloaderConfig(
        type=DownloaderType.BLACKHOLE,
        watch_dir=str(watch),
        completed_dir=str(completed),
    )
    downloader = DownloaderManager.get_downloader(config)
    assert isinstance(downloader, BlackholeDownloader)

    ok, msg = await downloader.check_connection()
    assert ok is True

    # Test adding NZB file
    nzb_content = b"<nzb>mock xml payload</nzb>"
    success, res_msg, job_id = await downloader.add_nzb_file(nzb_content, "Show.S01E01.nzb")
    assert success is True
    assert os.path.exists(watch / "Show.S01E01.nzb")

    # Queue should not be idle while file is present
    idle = await downloader.is_idle()
    assert idle is False

    # Remove file, now idle
    os.remove(watch / "Show.S01E01.nzb")
    assert (await downloader.is_idle()) is True


def test_sabnzbd_instance():
    config = DownloaderConfig(
        type=DownloaderType.SABNZBD,
        host="127.0.0.1",
        port=8080,
        api_key="sab_key_123",
    )
    downloader = DownloaderManager.get_downloader(config)
    assert isinstance(downloader, SabnzbdDownloader)
    assert "http://127.0.0.1:8080/api" in downloader.api_url
