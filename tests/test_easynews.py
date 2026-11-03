import pytest
from tentacle.indexer.easynews import EasyNewsClient
from tentacle.models import IndexerConfig, IndexerType


def test_easynews_client_init():
    config = IndexerConfig(
        name="EasyNews",
        type=IndexerType.EASYNEWS,
        url="https://members.easynews.com/2.0/search/solr-search/advanced",
        api_key="myuser:mypassword123",
    )
    client = EasyNewsClient(config)
    assert client.username == "myuser"
    assert client.password == "mypassword123"
    assert client._get_auth() == ("myuser", "mypassword123")


def test_easynews_rss_parser():
    mock_rss = """<?xml version="1.0" encoding="UTF-8"?>
    <rss version="2.0">
        <channel>
            <title>Easynews Search</title>
            <item>
                <title>Severance.S02E01.1080p.WEB.H264.mkv</title>
                <link>https://members.easynews.com/dl/abc/Severance.S02E01.mkv</link>
                <enclosure url="https://members.easynews.com/dl/abc/Severance.S02E01.mkv" length="2147483648" type="video/x-matroska" />
                <pubDate>Fri, 17 Jan 2025 03:00:00 GMT</pubDate>
            </item>
        </channel>
    </rss>
    """
    config = IndexerConfig(
        name="EasyNews",
        type=IndexerType.EASYNEWS,
        url="https://members.easynews.com/2.0/search/solr-search/advanced",
        api_key="user:pass",
    )
    client = EasyNewsClient(config)
    results = client._parse_rss_results(mock_rss, season=2, episode=1)

    assert len(results) == 1
    assert results[0].title == "Severance.S02E01.1080p.WEB.H264.mkv"
    assert "https://members.easynews.com/dl/abc" in results[0].link
    assert results[0].size == 2147483648
    assert results[0].season == 2
    assert results[0].episode == 1
