"""
Ayumi - Anime discord bot
Copyright (C) - 2020 | Saphielle Akiyama - saphielle.akiyama@gmail.com

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as published
by the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""

from dataclasses import dataclass

NoneType = None.__class__

@dataclass
class AnimeResponse:
    request_hash: str
    request_cached: bool
    request_cache_expiry: int
    mal_id: int
    url: str
    image_url: str
    trailer_url: str
    title: str
    title_english: NoneType
    title_japanese: str
    title_synonyms: list
    type: str
    source: str
    episodes: int
    status: str
    airing: bool
    aired: dict
    duration: str
    rating: str
    score: float
    scored_by: int
    rank: int
    popularity: int
    members: int
    favorites: int
    synopsis: str
    background: NoneType
    premiered: str
    broadcast: str
    related: dict
    producers: list
    licensors: list
    studios: list
    genres: list
    opening_themes: list
    ending_themes: list
    jikan_url: str
    headers: dict

@dataclass
class CharacterResponse:
    request_hash: str
    request_cached: bool
    request_cache_expiry: int
    mal_id: int
    url: str
    name: str
    name_kanji: str
    nicknames: list
    about: str
    member_favorites: int
    image_url: str
    animeography: list
    mangaography: list
    voice_actors: list
    jikan_url: str
    headers: dict

@dataclass
class ClubResponse:
    request_hash: str
    request_cached: bool
    request_cache_expiry: int
    mal_id: int
    url: str
    image_url: str
    title: str
    members_count: int
    pictures_count: int
    category: str
    created: str
    type: str
    staff: list
    anime_relations: list
    manga_relations: list
    character_relations: list
    jikan_url: str
    headers: dict

@dataclass
class GenreAnimeResponse:
    request_hash: str
    request_cached: bool
    request_cache_expiry: int
    mal_url: dict
    item_count: int
    anime: list
    jikan_url: str
    headers: dict

@dataclass
class GenreMangaResponse:
    request_hash: str
    request_cached: bool
    request_cache_expiry: int
    mal_url: dict
    item_count: int
    manga: list
    jikan_url: str
    headers: dict

@dataclass
class PersonResponse:
    request_hash: str
    request_cached: bool
    request_cache_expiry: int
    mal_id: int
    url: str
    image_url: str
    website_url: NoneType
    name: str
    given_name: str
    family_name: str
    alternate_names: list
    birthday: str
    member_favorites: int
    about: str
    voice_acting_roles: list
    anime_staff_positions: list
    published_manga: list
    jikan_url: str
    headers: dict

@dataclass
class ProducerResponse:
    request_hash: str
    request_cached: bool
    request_cache_expiry: int
    meta: dict
    anime: list
    jikan_url: str
    headers: dict

@dataclass
class ScheduleResponse:
    request_hash: str
    request_cached: bool
    request_cache_expiry: int
    monday: list
    jikan_url: str
    headers: dict

@dataclass
class ScheduleNoneResponse:
    request_hash: str
    request_cached: bool
    request_cache_expiry: int
    monday: list
    tuesday: list
    wednesday: list
    thursday: list
    friday: list
    saturday: list
    sunday: list
    other: list
    unknown: list
    jikan_url: str
    headers: dict

@dataclass
class SearchAnimeResponse:
    request_hash: str
    request_cached: bool
    request_cache_expiry: int
    results: list
    last_page: int
    jikan_url: str
    headers: dict

@dataclass
class SearchCharacterResponse:
    request_hash: str
    request_cached: bool
    request_cache_expiry: int
    results: list
    last_page: int
    jikan_url: str
    headers: dict

@dataclass
class SearchMangaResponse:
    request_hash: str
    request_cached: bool
    request_cache_expiry: int
    results: list
    last_page: int
    jikan_url: str
    headers: dict

@dataclass
class SearchPersonResponse:
    request_hash: str
    request_cached: bool
    request_cache_expiry: int
    results: list
    last_page: int
    jikan_url: str
    headers: dict

@dataclass
class SeasonResponse:
    request_hash: str
    request_cached: bool
    request_cache_expiry: int
    season_name: str
    season_year: int
    anime: list
    jikan_url: str
    headers: dict

@dataclass
class SeasonArchiveResponse:
    request_hash: str
    request_cached: bool
    request_cache_expiry: int
    archive: list
    jikan_url: str
    headers: dict

@dataclass
class SeasonLaterResponse:
    request_hash: str
    request_cached: bool
    request_cache_expiry: int
    season_name: str
    season_year: NoneType
    anime: list
    jikan_url: str
    headers: dict

@dataclass
class TopAnimeResponse:
    request_hash: str
    request_cached: bool
    request_cache_expiry: int
    top: list
    jikan_url: str
    headers: dict

@dataclass
class TopMangaResponse:
    request_hash: str
    request_cached: bool
    request_cache_expiry: int
    top: list
    jikan_url: str
    headers: dict