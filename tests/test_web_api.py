import pytest
import httpx
from tentacle.web.app import app, db
from tentacle.models import IndexerConfig, ShowStatus


@pytest.mark.asyncio
async def test_api_status():
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.get("/api/status")
        assert resp.status_code == 200
        data = resp.json()
        assert "state" in data
        assert "total_shows" in data


@pytest.mark.asyncio
async def test_api_shows():
    # Insert dummy show
    db.upsert_show("The Mandalorian", "/media/Mandalorian", ShowStatus.ACTIVE)

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.get("/api/shows")
        assert resp.status_code == 200
        shows = resp.json()
        assert any(s["name"] == "The Mandalorian" for s in shows)


@pytest.mark.asyncio
async def test_api_indexers():
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        # Create
        new_idx = {
            "name": "API Test Indexer",
            "url": "https://api.testindex.com",
            "api_key": "abc12345",
            "category_id": "5000",
            "enabled": True,
            "priority": 2,
        }
        post_resp = await client.post("/api/indexers", json=new_idx)
        assert post_resp.status_code == 200
        created = post_resp.json()
        idx_id = created["id"]

        # List
        get_resp = await client.get("/api/indexers")
        assert get_resp.status_code == 200
        assert any(i["id"] == idx_id for i in get_resp.json())

        # Toggle status
        toggle_resp = await client.post(
            f"/api/indexers/{idx_id}/status", json={"enabled": False}
        )
        assert toggle_resp.status_code == 200
        assert toggle_resp.json()["enabled"] is False

        # Delete
        del_resp = await client.delete(f"/api/indexers/{idx_id}")
        assert del_resp.status_code == 200


@pytest.mark.asyncio
async def test_api_settings():
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.get("/api/settings")
        assert resp.status_code == 200
        data = resp.json()
        assert "shows_dir" in data
        assert "downloader" in data
