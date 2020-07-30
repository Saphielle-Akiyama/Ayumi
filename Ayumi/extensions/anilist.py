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

# This whole code is fucked up
# TODO: -Formatter should return a tuple name, value that will be formatted later on
#       -Keep everything inside their own functions instead of mixing them up together
#       - v what the fuck is this doing here

DM_CHANNEL_URL_TEMPLATE = "https://discordapp.com/channels/@me/{}/"

# This should be formatted with %s to avoid fstring or .format issues
QUERY_TEMPLATE = """
query ($page: Int, $perPage: Int, $asHtml: Boolean, %s) {
    Page (page: $page, perPage: $perPage) {
        media (%s) {
            isAdult
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
            trending
        }
    }
}
"""

class PresetMenuPages(menus.MenuPages):

    QUERY = """
INSERT INTO anime_reminders (user_id, trigger_time, anime_name, message_url)
VALUES ($1, $2, $3, $4)
"""

    def __init__(self, source: menus.ListPageSource, **options):
        super().__init__(source, clear_reactions_after=True, timeout=60)
        self.pages_added_to_calendar = set()

    async def add_to_remind_list(self):
        """A helper function that adds an anime to the user's reminder list"""
        ctx = self.ctx
        data = await self.source.get_page(self.current_page)
        next_airing_data = data['nextAiringEpisode']

        if not next_airing_data:
            return await ctx.send("Sorry ! I don't have any precise delay until the next release",
                                  delete_after=5)
        
        media_title = self.source.format_title(data)
        reminder_timestamp = next_airing_data['airingAt'] - 300  # 5m before it
        reminder_dt = dt.datetime.fromtimestamp(reminder_timestamp)
        natural_delta = humanize.naturaltime(reminder_dt) 
        info = f"Add a reminder 5 minutes before the airing of `{media_title}` ? ({natural_delta})"

        menu = utils.Confirm(self.ctx, {'content': info}, delete_message_after=True)
        
        async with menu as confirmed:
            if not confirmed:
                return self.stop()
        
        aware_reminder_dt = reminder_dt.replace(tzinfo=dt.timezone.utc)

        async with ctx.bot.pool.acquire() as con:
            await con.execute(self.QUERY, ctx.author.id, reminder_dt, media_title, self.message.jump_url)

        await ctx.send(f"Successfully added a reminder for `{media_title}`")
        
        self.pages_added_to_calendar.add(self.current_page)

    async def remove_from_remind_list(self):
        pass

    @menus.button("\U0001f5d3", position=menus.Last(2))  # calendar
    async def on_calendar(self, payload: discord.RawReactionActionEvent):
        if self.current_page in self.pages_added_to_calendar:
            return await self.remove_from_remind_list()
        else:
            return await self.add_to_remind_list()
    
    # Overriden buttons
    
    def _skip_single_triangle_buttons(self):
        max_pages = self.source.get_max_pages()
        return max_pages <= 1


    @menus.button('\N{BLACK LEFT-POINTING TRIANGLE}\ufe0f', position=menus.First(1),
                  skip_if=_skip_single_triangle_buttons)
    async def go_to_previous_page(self, payload: discord.RawReactionActionEvent):
        """Overriden to implement skip_if"""
        return await super().go_to_previous_page(payload)


    @menus.button('\N{BLACK RIGHT-POINTING TRIANGLE}\ufe0f', position=menus.Last(0),
                  skip_if=_skip_single_triangle_buttons)
    async def go_to_next_page(self, payload: discord.RawReactionActionEvent):
        """Same as go_to_previous_page"""
        return await super().go_to_next_page(payload)


class PresetSource(menus.ListPageSource):
    def __init__(self, entries: list):
        super().__init__(entries, per_page=1)


class MediaSource(PresetSource):
    """Source that handles the formatting for the responses from the api"""
    def is_paginating(self) -> True:
        """we want to force buttons there"""
        return True

    @staticmethod
    def join_data(data: list) -> Optional[str]:
        """Jons the data or returns none if there isn't any"""
        return '\n\n'.join(data) or None
    
    @staticmethod
    def format_title(data: dict) -> str:
        """Formats the title (used for the menu source"""
        main_title = data['title']['english'] or data['title']['romaji']
        f_is_adult = "18+ " if data['isAdult'] else ''
        return f"[{f_is_adult}{data['format']}] {main_title}"

    # Airing info

    @staticmethod
    def format_boundary_dates(data: Tuple[dict]) -> str:
        """Formats the date into something nicer"""
        verbs = ('Start', 'End')

        for verb, boundary in zip(verbs, data):
            if not all(v for v in boundary.items()):
                yield None

            date_info = operator.itemgetter('year', 'month', 'day')(boundary)

            natural = None

            if all(date_info):
                date = dt.datetime(*date_info)
                natural = date.strftime("%d %b %Y")

            elif any(date_info):
                filtered = [f"{d:02}" if d else '00' for d in reversed(date_info)]
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
        f_airing_time = airing_at.strftime("**Next airing**\n%d %B %Y %H:%M UTC")

        return airing_at, f_airing_time

    @staticmethod
    def format_meta(data: dict) -> Generator[str, None, None]:
        """Formats metrics"""
        to_get = ('episodes', 'duration', 'chapters', 'volumes', 'source')
        infos = operator.itemgetter(*to_get)(data)

        for name, info in zip(to_get, infos):
            if info:
                name = name.lower().title()

                if name == 'Duration':
                    delta = dt.timedelta(minutes=info)
                    info = humanize.naturaldelta(delta)

                elif isinstance(info, str):
                    info = info.lower().replace('_', ' ').title()

                line = f"**{name}**\n{info}"

                yield line

    @staticmethod
    def format_community(data: dict):
        """Formats community ratings"""
        to_get = ('averageScore', 'popularity', 'favourites', 'trending')

        avg_score, popularity, favourites, related_actions = operator.itemgetter(*to_get)(data)

        if avg_score:
            yield f"**Score**\n{avg_score}/100"

        if popularity:
            yield f"**Watchlists**\n{popularity}"

        if favourites:
            yield f"**Favourites**\n{favourites}"

        if related_actions:
            yield f"**Related actions\nin the past hour**\n{related_actions}"

    def format_page(self, menu: PresetMenuPages, data: dict) -> utils.Embed:
        embed = utils.Embed()
        embed.title = self.format_title(data)
        embed.description = utils.remove_html_tags(data['description'] or '')

        if color_hex := data['coverImage']['color']:
            embed.color = int(color_hex[1:], 16)

        # Images
        if img_url := data['bannerImage']:
            embed.set_image(url=img_url)

        if thumbnail_url := data['coverImage']['extraLarge']:
            embed.set_thumbnail(url=thumbnail_url)

        # Airing infos
        boundary_dates = operator.itemgetter('startDate', 'endDate')(data)
        f_boundary_dates = self.format_boundary_dates(boundary_dates)
        airing_at, f_airing_time = self.format_airing_dates(data)

        # special thing for the footer
        max_pages = self.get_max_pages()
        footer = f"Page {menu.current_page + 1} out of {max_pages}"
        if airing_at:
            embed.timestamp = airing_at
            footer += " | Next release in your timezone :"

        embed.set_footer(text=footer)

        if f_season := data['season']:
            cap_season = f_season.lower().title()
            f_season = f"**Season**\n{cap_season}"

        status = data['status'].lower().replace('_', ' ').title()
        f_status = f"**Status**\n{status}"
        dates = [*f_boundary_dates, f_airing_time, f_season, f_status]
        filtered_dates = filter(None, dates)
        formatted_dates = self.join_data(filtered_dates)
        if formatted_dates:
            embed.add_field(name="\u200b", value=formatted_dates)

        # Some meta info
        country_of_origin = pycountry.countries.get(alpha_2=data['countryOfOrigin'])
        f_country_of_origin = f"**Country of origin**\n{country_of_origin.name}"

        meta = [*self.format_meta(data), f_country_of_origin]
        if f_meta := self.join_data(meta):
            embed.add_field(name="\u200b", value=f_meta)

        # Community
        community = self.format_community(data)
        if f_community := self.join_data(community):
            embed.add_field(name="\u200b", value=f_community)

        # Some more infos about the author
        ctx = menu.ctx
        dm_channel_url = DM_CHANNEL_URL_TEMPLATE.format(ctx.author.id)
        embed.set_author(name=f"Requested by : {ctx.author}",
                         icon_url=ctx.author.avatar_url,
                         url=dm_channel_url)

        return embed.sort_fields()


class Anilist(commands.Cog):
    def __init__(self, bot: core.Bot):
        self.bot = bot
        self.url = "https://graphql.anilist.co"

    @staticmethod
    def transform_to_search_param(*data: str):
        media_params = []

        for param in data:
            arg_pointer, _ = param.split(':')

            arg_name = arg_pointer[1:]
            media_params.append(f"{arg_name}: {arg_pointer}")

        return ', '.join(data), ', '.join(media_params)

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
    async def search(self, ctx: core.Context, *, query: str):
        """Looks for infos about an anime or a manga"""
        params = ["$search: String"]
        variables = {
            'search': query,
            'page': 1,
            'perPage': 10,
            'asHtml': False
        }

        if not ctx.is_nsfw:
            params.append("$isAdult: Boolean")
            variables['isAdult'] = False

        params = self.transform_to_search_param(*params)

        json_query = QUERY_TEMPLATE % params

        resp = await self.make_request(json_query, variables)

        source = MediaSource(resp['data']['Page']['media'])
        menu = PresetMenuPages(source)
        await menu.start(ctx)


def setup(bot: core.Bot):
    cog = Anilist(bot)
    bot.add_cog(cog)
