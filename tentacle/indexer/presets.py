#    Tentacle V4 - The Automated TV Show Tracker, Downloader & Media Organizer
#    Copyright (C) 2010-2026
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""Built-in UseNet Indexer Presets."""

from typing import Dict, List
from pydantic import BaseModel


class PresetIndexer(BaseModel):
    id: str
    name: str
    default_url: str
    description: str
    requires_api_key: bool = True
    default_categories: str = "5000,5030,5040"


INDEXER_PRESETS: List[PresetIndexer] = [
    PresetIndexer(
        id="nzbgeek",
        name="NZBGeek",
        default_url="https://api.nzbgeek.info",
        description="Popular community-driven VIP Newznab indexer.",
        requires_api_key=True,
    ),
    PresetIndexer(
        id="nzbplanet",
        name="NZBPlanet",
        default_url="https://api.nzbplanet.net",
        description="Large automated Newznab indexer with extensive retention.",
        requires_api_key=True,
    ),
    PresetIndexer(
        id="drunkenslug",
        name="DrunkenSlug",
        default_url="https://api.drunkenslug.com",
        description="Reliable Usenet indexer with Newznab API access.",
        requires_api_key=True,
    ),
    PresetIndexer(
        id="dognzb",
        name="DogNZB",
        default_url="https://api.dognzb.cr",
        description="VIP Usenet indexer with custom Newznab implementation.",
        requires_api_key=True,
    ),
    PresetIndexer(
        id="tabularasa",
        name="Tabula Rasa",
        default_url="https://www.tabula-rasa.info",
        description="Community Usenet indexer supporting Newznab standard.",
        requires_api_key=True,
    ),
    PresetIndexer(
        id="prowlarr",
        name="Prowlarr (Local Proxy)",
        default_url="http://127.0.0.1:9696",
        description="Aggregated indexer proxy supporting all configured providers.",
        requires_api_key=True,
    ),
    PresetIndexer(
        id="custom",
        name="Custom Newznab Provider",
        default_url="https://",
        description="Any Newznab or Torznab compatible API endpoint.",
        requires_api_key=True,
    ),
]


def get_preset_by_id(preset_id: str) -> PresetIndexer | None:
    for p in INDEXER_PRESETS:
        if p.id.lower() == preset_id.lower():
            return p
    return None
