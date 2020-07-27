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
from typing import Union, Any, Generator, Tuple

import discord
from discord.ext import commands, menus
import humanize
import pycountry

import core
import utils

class MalError(commands.CommandError):
    """Base exception for mal related errors"""

class NoResultsError(MalError):
    def __init__(self, query: str):
        self.query = query

    def __str__(self):
        return "Sorry ! I couldn't find any result for the query " + self.query



class PresetMenuPages(menus.MenuPages):
    def __init__(self, source: menus.ListPageSource, **options):
        super().__init__(source, delete_message_after=True, timeout=60)


class PresetSource(menus.ListPageSource):
    def __init__(self, entries: list):
        super().__init__(entries, per_page=1)

class MediaSource(PresetSource):

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
                yield f"**{verb}**: {natural}"
            else:
                yield None

    @staticmethod
    def format_airing_dates(data: int) -> Tuple[dt.datetime, str]:
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


    def format_page(self, menu: PresetMenuPages, data: dict) -> utils.Embed:
        main_title = data['title']['english'] or data['title']['romaji']
        title = f"[{data['format']}] {main_title}"
        description = utils.remove_html_tags(data['description'])
        color = int(data['coverImage']['color'][1:], 16)
        embed = utils.Embed(title=title, description=description, color=color)
        
        # Images
        embed.set_image(url=data['bannerImage'])
        embed.set_thumbnail(url=data['coverImage']['extraLarge'])

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

        country_of_origin = pycountry.countries.get(alpha_2=data['countryOfOrigin'])
        f_country_of_origin = f"**Country**: {country_of_origin.name}"
        dates = [*f_boundary_dates, f_time_until_airing, f_season, f_country_of_origin]
        filtered_dates = filter(None, dates)
        formatted_dates = '- ' + '\n- '.join(filtered_dates)
        embed.add_field(name='Airing', value=formatted_dates)







        return embed



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

    @commands.command()
    async def media(self, ctx: core.Context, *, query: str):

        json_query = '''
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
                    

                }
            }
        }
        '''
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
