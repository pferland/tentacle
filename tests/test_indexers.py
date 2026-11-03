import pytest
from tentacle.database import Database
from tentacle.indexer.newznab import NewznabClient
from tentacle.indexer.presets import INDEXER_PRESETS, get_preset_by_id
from tentacle.models import IndexerConfig


def test_presets():
    assert len(INDEXER_PRESETS) >= 6
    geek = get_preset_by_id("nzbgeek")
    assert geek is not None
    assert "nzbgeek.info" in geek.default_url

    custom = get_preset_by_id("custom")
    assert custom is not None


def test_newznab_xml_parser():
    xml_data = """<?xml version="1.0" encoding="UTF-8"?>
    <rss version="2.0" xmlns:newznab="http://www.newznab.com/DTD/2010/feeds/attributes/">
        <channel>
            <title>NZBGeek</title>
            <item>
                <title>Show.Name.S01E02.720p.HDTV</title>
                <link>https://api.nzbgeek.info/api?t=get&amp;id=12345</link>
                <pubDate>Mon, 15 Jan 2024 20:00:00 +0000</pubDate>
                <enclosure url="https://api.nzbgeek.info/api?t=get&amp;id=12345" length="524288000" type="application/x-nzb" />
            </item>
        </channel>
    </rss>
    """
    config = IndexerConfig(name="NZBGeek", url="https://api.nzbgeek.info", api_key="test")
    client = NewznabClient(config)
    results = client._parse_json_or_xml(xml_data, season=1, episode=2)

    assert len(results) == 1
    assert results[0].title == "Show.Name.S01E02.720p.HDTV"
    assert "id=12345" in results[0].link
    assert results[0].size == 524288000


def test_newznab_json_parser():
    json_data = """{
        "channel": {
            "title": "NZBPlanet",
            "item": [
                {
                    "title": "Show.Name.S01E02.1080p.WEB",
                    "link": "https://api.nzbplanet.net/get?id=999",
                    "size": 1048576000
                }
            ]
        }
    }"""
    config = IndexerConfig(name="NZBPlanet", url="https://api.nzbplanet.net", api_key="test")
    client = NewznabClient(config)
    results = client._parse_json_or_xml(json_data, season=1, episode=2)

    assert len(results) == 1
    assert results[0].title == "Show.Name.S01E02.1080p.WEB"
    assert results[0].size == 1048576000
