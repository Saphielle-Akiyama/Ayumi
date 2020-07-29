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

import operator
import datetime as dt
import json
from typing import Union, Any, Generator, Tuple, Optional

import discord
from discord.ext import commands, menus
import humanize
import pycountry

import core
import utils


class PresetMenuPages(menus.MenuPages):
    def __init__(self, source: menus.ListPageSource, **options):
        super().__init__(source, delete_message_after=True, timeout=60)


class PresetSource(menus.ListPageSource):
    def __init__(self, entries: list):
        super().__init__(entries, per_page=1)

class MediaSource(PresetSource):
    
    @staticmethod
    def join_data(data: list) -> Optional[str]:
        """Jons the data or returns none if there isn't any"""
        return '\n'.join(data) or None

    # Airing info

    @staticmethod
    def format_boundary_dates(data: Tuple[dict]) -> str:
        """Formats the date into something nicer"""
        verbs = ('Started', 'Finished')

        for verb, boundary in zip(verbs, data):
            if not all(v for v in boundary.items()):
                yield None

            date_info = operator.itemgetter('year', 'month', 'day')(boundary)

            if all(date_info):
                date = dt.datetime(*date_info)
                natural = humanize.naturaldate(date)

            else:
                filtered = [str(d) for d in date_info if d]
                natural = '/'.join(filtered)

            if natural:
                yield f"**{verb}**\n{natural}"

    @staticmethod
    def format_airing_dates(data: dict) -> Tuple[dt.datetime, str]:
        """
        Returns the next airing as a datetime object
        as well as the duration until it in a human datetime
        """
        getter = operator.itemgetter('airingAt', 'timeUntilAiring')

        next_airing_episode = data['nextAiringEpisode']
        if next_airing_episode is None:
            return None, None

        airing_at, time_until_airing = getter(next_airing_episode)

        airing_at = dt.datetime.fromtimestamp(airing_at)

        time_until_airing = dt.timedelta(seconds=time_until_airing)
        natural_time_until_airing = humanize.naturaldelta(time_until_airing)
        f_time_until_airing = f"**Next airing**: {natural_time_until_airing}"
        return airing_at, f_time_until_airing
    
    @staticmethod
    def format_meta(data: dict) -> Generator[str, None, None]:
        """Formats metrics"""
        to_get = ('episodes', 'duration', 'chapters', 'volumes', 'source')
        infos = operator.itemgetter(*to_get)(data)
        
        for name, info in zip(to_get, infos):
            if info:
                name = name.lower().title()
                info = info.lower().title() if isinstance(info, str) else info
                line = f"**{name}**: {info}"

                if name == 'duration':
                    line += ' min'

                yield line
    
    @staticmethod
    def format_community(data: dict):
        """Formats community ratings"""
        to_get = ('averageScore', 'popularity', 'favourites')

        avg_score, popularity, favourites = operator.itemgetter(*to_get)(data)
        
        if avg_score:
            yield f"**Score**: {avg_score}/100"

        if popularity:
            yield f"**Watchlists**: {popularity}"

        if favourites:
            yield f"**Favourites**: {favourites}"


    def format_page(self, menu: PresetMenuPages, data: dict) -> utils.Embed:
        main_title = data['title']['english'] or data['title']['romaji']
        title = f"[{data['format']}] {main_title}"
        description = utils.remove_html_tags(data['description'])
        embed = utils.Embed(title=title, description=description)
        
        color_hex = data['coverImage']['color']
        if color_hex:
            embed.color = int(color_hex[1:], 16)

        # Images
        img_url = data['bannerImage']
        if img_url is not None:
            embed.set_image(url=img_url)

        thumbnail_url = data['coverImage']['extraLarge']

        if thumbnail_url is not None:
            embed.set_thumbnail(url=thumbnail_url)
        
        # Airing infos
        boundary_dates = operator.itemgetter('startDate', 'endDate')(data)
        f_boundary_dates = self.format_boundary_dates(boundary_dates)
        airing_at, f_time_until_airing = self.format_airing_dates(data)

        if airing_at is not None:
            embed.set_footer(text="The next airing releases on :")
            embed.timestamp = airing_at

        f_season = data['season']
        if f_season:
            cap_season = f_season.lower().title()
            f_season = f"**Season**: {cap_season}"
        
        status = data['status'].lower().replace('_', ' ').title()
        f_status = f"**Status**: {status}"
        dates = [*f_boundary_dates, f_time_until_airing, f_season, f_status]
        filtered_dates = filter(None, dates)
        formatted_dates = self.join_data(filtered_dates)
        if formatted_dates:
            embed.add_field(name='Airing', value=formatted_dates)

        # Some meta info
        country_of_origin = pycountry.countries.get(alpha_2=data['countryOfOrigin'])
        f_country_of_origin = f"**Origin**: {country_of_origin.name}"
 
        meta = [*self.format_meta(data), f_country_of_origin]
        f_meta = self.join_data(meta)
        if f_meta is not None:
            embed.add_field(name='Meta', value=f_meta)
        
        # Community 
        community = self.format_community(data)
        f_community = self.join_data(community)
        if f_community is not None:
            embed.add_field(name='Community', value=f_community)
        
        return embed.sort_fields()


class Anilist(commands.Cog):
    def __init__(self, bot: core.Bot):
        self.bot = bot
        self.url = "https://graphql.anilist.co"

    @staticmethod
    def get_response_errors(data: dict) -> Generator[str, None, None]:
        for err in data['errors']:
            yield f"{err['status']}: {err['message']}"

    async def make_request(self, query: str, variables: dict):
        json_ = {'query': query, 'variables': variables}
        async with self.bot.session.post(self.url, json=json_) as r:
            resp = await r.json()

            if r.status != 200:
                errors = self.get_response_errors(resp)
                formatted_errors = '\n'.join(errors)
                raise commands.BadArgument(formatted_errors)

            return resp

    @commands.command(aliases=['anime', 'manga'])
    async def media(self, ctx: core.Context, *, query: str):
        """Looks for infos about an anime or a manga"""
        json_query = """
        query ($page: Int, $perPage: Int, $search: String, $asHtml: Boolean) {
            Page (page: $page, perPage: $perPage) {
                media (search: $search) {
                    bannerImage
                    coverImage {
                        extraLarge
                        color
                    }
                    title {
                        english
                        romaji
                    }
                    format
                    description(asHtml: $asHtml)

                    startDate {
                        day
                        month
                        year
                    }
                    endDate {
                        day
                        month
                        year
                    }
                    nextAiringEpisode {
                        airingAt
                        timeUntilAiring
                    }
                    season
                    countryOfOrigin
                    status
                    
                    episodes 
                    duration
                    chapters
                    volumes
                    source

                    averageScore
                    popularity
                    favourites
                }
            }
        }
        """ 
        variables = {
            'search': query,
            'pag': 1,
            'perPage': 3,
            'asHtml': False
        }

        resp = await self.make_request(json_query, variables)

        source = MediaSource(resp['data']['Page']['media'])
        menu = PresetMenuPages(source)
        await menu.start(ctx)


def setup(bot: core.Bot):
    cog = Anilist(bot)
    bot.add_cog(cog)
