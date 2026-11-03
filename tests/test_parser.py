import os
import pytest
from tentacle.library.parser import (
    extract_season_from_folder,
    is_media_file,
    is_sample_file,
    parse_season_episode,
)


def test_is_media_file():
    assert is_media_file("show.s01e01.mkv") is True
    assert is_media_file("episode.mp4") is True
    assert is_media_file("video.avi") is True
    assert is_media_file("info.nfo") is False
    assert is_media_file("archive.par2") is False
    assert is_media_file("checksum.sfv") is False
    assert is_media_file("sample.jpg") is False


def test_parse_season_episode():
    # Standard SxxExx
    assert parse_season_episode("Breaking.Bad.S05E14.Ozymandias.720p.mkv") == (5, 14)
    assert parse_season_episode("show.s1e2.avi") == (1, 2)

    # 1x02 format
    assert parse_season_episode("The.Office.02x05.mp4") == (2, 5)
    assert parse_season_episode("Show 1x12.mkv") == (1, 12)

    # Long Season/Episode format
    assert parse_season_episode("Firefly Season 1 Episode 4.mkv") == (1, 4)

    # Invalid or non-episode
    assert parse_season_episode("Movie.Title.2024.1080p.mkv") is None


def test_extract_season_from_folder():
    assert extract_season_from_folder("Season 1") == 1
    assert extract_season_from_folder("Season 02") == 2
    assert extract_season_from_folder("Season.03") == 3
    assert extract_season_from_folder("S4") == 4
    assert extract_season_from_folder("Specials") is None
