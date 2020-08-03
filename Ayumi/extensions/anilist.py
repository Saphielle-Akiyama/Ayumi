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
import asyncio
import operator
import datetime as dt
import json
from typing import Union, Any, Generator, Tuple, Optional

import asyncpg
import discord
from discord.ext import commands, menus
import humanize
import pycountry

import core
import utils

# This whole code is fucked up
# TODO: -Formatter should return a tuple name, value that will be formatted later on
#       -Keep everything inside their own functions instead of mixing them up together
#       -Redis in make_request
#       -In the add/remove reminders menu, there are some common data to format
#       -Query data before showing menus

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

ALARM_CLOCK_EMOJI = "\U000023f0"
CALENDAR_EMOJI = "\U0001f4c6"

class NoResultsError(commands.CommandError):
    def __init__(self, query: str):
        self.query = query
    
    def __str__(self):
        return f"Sorry ! I couldn't find any results for \"{self.query}\""

class PresetMenuPages(menus.MenuPages):
    def __init__(self, source: menus.ListPageSource, **options):
        super().__init__(source, clear_reactions_after=True, timeout=60)
        self.pages_added_to_calendar = set()
    
    def format_common_data(self, data: dict) -> Tuple[str, dt.datetime, str]:
        """Formats the title, the timestamp, and the natural timestamp"""
        media_title = self.source.format_title(data)
        airing_at, _ = self.source.format_airing_dates(data) 
        aware_reminder_dt = airing_at - dt.timedelta(minutes=5) 
        naive_timestamp = dt.datetime.fromtimestamp(aware_reminder_dt.timestamp()) 
        human_delta = humanize.naturaltime(naive_timestamp)

        return media_title, aware_reminder_dt, human_delta
    
    async def get_user_confirmation(self, menu: menus.Menu) -> bool:
        """Asks the user if they want to confirm or not, returns the result"""
        async with menu as confirmed:
            return confirmed

    async def add_to_remind_list(self, data: dict):
        """A helper function that adds an anime to the user's reminder list"""
        ctx = self.ctx
        if not (next_airing_data := data['nextAiringEpisode']):
            return await ctx.send("Sorry ! I don't have any precise delay until the next release",
                                  delete_after=5)
        
        media_title, aware_reminder_dt, human_delta = self.format_common_data(data)
        info = f"Add a reminder 5 minutes before the airing of `{media_title}` ({human_delta}) ?"
        menu = utils.Confirm(self.ctx, {'content': info}, delete_message_after=True)
        if not await self.get_user_confirmation(menu):
            msg = "Cancelled addition of `{media_title}` in your reminders list"
            return await self.ctx.send(msg)
        
        query = """
INSERT INTO anime_reminders (user_id, trigger_time, anime_name, channel_id)
VALUES ($1, $2, $3, $4); 
"""
        query_args = (ctx.author.id, aware_reminder_dt, media_title, ctx.channel.id)
        async with ctx.bot.pool.acquire() as con:
            await con.execute(query, *query_args)
        
        data['isInReminderList'] = True
        await ctx.send(f"Added a reminder for `{media_title}`", delete_after=5)
        
    async def remove_from_remind_list(self, data: dict):
        """A helper function to remove an anime from an user's list"""
        ctx = self.ctx
        media_title, aware_reminder_dt, human_delta = self.format_common_data(data)
        info = f"Remove your reminder for {media_title} ({human_delta}) ?"
        menu = utils.Confirm(ctx, {'content': info}, delete_message_after=True) 
        
        if not await self.get_user_confirmation(menu):
            return await ctx.send(f"Cancelled removal of `{media_title}` from your reminders list")

        query = """
DELETE FROM anime_reminders
WHERE user_id = $1
      AND anime_name = $2;
"""
        async with ctx.bot.pool.acquire() as con:
            await con.execute(query, ctx.author.id, media_title)

        data['isInReminderList'] = False
        await ctx.send(f"Removed a reminder for `{media_title}`")
    
    # Buttons 

    @menus.button("\U0001f5d3", position=menus.Last(2))  # calendar
    async def on_calendar(self, payload: discord.RawReactionActionEvent):
        """Adds it to the user's remind list"""
        data = await self.source.get_page(self.current_page)
        if data['isInReminderList']:
            await self.remove_from_remind_list(data)
        else:
            await self.add_to_remind_list(data)
        await self.show_page(self.current_page)
    
    # Modified buttons
    
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

    CHECK_USER_LIST_QUERY = """
SELECT * FROM anime_reminders 
WHERE user_id = $1
      AND anime_name = $2;
"""

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
        Returns the next airing as a datetime object (for the embed footer)
        as well as the duration until it in a human datetime (for the embed)
        """
        next_airing_episode = data['nextAiringEpisode']
        if next_airing_episode is None:
            return None, None

        time_until_airing = next_airing_episode['timeUntilAiring']

        airing_at = dt.datetime.now(tz=dt.timezone.utc) + dt.timedelta(seconds=time_until_airing)
        f_airing_time = airing_at.strftime("**Next airing**\n%d %b %Y\n%H:%M UTC")

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
    
    async def check_if_userlist(self, ctx: core.Context, media_title: str) -> bool:
        """Checks if an anime is in an user's list"""
        async with ctx.bot.pool.acquire() as con:
            res = await con.fetchrow(self.CHECK_USER_LIST_QUERY, ctx.author.id, media_title)
        return res

    async def format_page(self, menu: PresetMenuPages, data: dict) -> utils.Embed:
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
        
        # Checking if the anime is in the user's list
        ctx = menu.ctx

        user_data = []

        if data.get('isInReminderList', False) or await self.check_if_userlist(ctx, embed.title):
            user_data.append(f"You can use {ALARM_CLOCK_EMOJI} to remove your current reminder")
            data['isInReminderList'] = True 
        else:
            data['isInReminderList'] = False
            msg = f"You can use {ALARM_CLOCK_EMOJI} to get a message 5 minutes before the next release !"
            user_data.append(msg)
        
        embed.add_field(name='\u200b', value=self.join_data(user_data), inline=False)

        # Some more infos about the author
        dm_channel_url = DM_CHANNEL_URL_TEMPLATE.format(ctx.author.id)
        embed.set_author(name=f"Requested by : {ctx.author}",
                         icon_url=ctx.author.avatar_url,
                         url=dm_channel_url)

        return embed.sort_fields()


class Anilist(commands.Cog):
    def __init__(self, bot: core.Bot):
        self.bot = bot
        self.url = "https://graphql.anilist.co"
        bot.loop.create_task(self.setup_reminders())

    
    DELETE_QUERY = """
DELETE FROM anime_reminders 
WHERE user_id = $1
      AND trigger_time = $2
      AND anime_name = $3
      AND channel_id = $4
"""

    @commands.Cog.listener()
    async def on_anime_reminder(self, record: asyncpg.Record):
        """Sends the reminder to the user, then deletes the record"""
        getter = operator.itemgetter('user_id', 'trigger_time', 'anime_name', 'channel_id')
        user_id, _, anime_name, channel_id = getter(record)

        channel = self.bot.get_channel(channel_id) or await self.bot.fetch_channel(channel_id)
        content = f"<@{user_id}> Here's your reminder for `{anime_name}`"
        try:
            await channel.send(content)
        except discord.HTTPException:
            user_id = record['user_id']
            user = bot.get_user(user_id) or await bot.fetch_user(user_id)
            try:
                await user.send(content)
            except discord.HTTPException:
                pass

        async with self.bot.pool.acquire() as con:
            await con.execute(DELETE_QUERY, *getter(record))

    async def reminder_dispatcher(self, record: asyncpg.Record):
        """Waits until the reminder time, then dispatch an anime_reminder event"""
        await discord.utils.sleep_until(record['trigger_time'])
        self.bot.dispatch("anime_reminder", record)

    async def setup_reminders(self):
        """Fetches all reminders, then dispatches them"""  # might optimize this with a tasks loop
        reminders = await con.fetch("SELECT * FROM anime_reminders")
        for reminder in reminders:
            coro = self.reminder_dispatcher(record)
            self.bot.loop.create_task(coro)

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
        
        return resp['data']['Page']['media']

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

        results = await self.make_request(json_query, variables)

        source = MediaSource(results)
        menu = PresetMenuPages(source)

        try:
            await menu.start(ctx, wait=True)
        except IndexError:
            raise NoResultsError(query)


def setup(bot: core.Bot):
    cog = Anilist(bot)
    bot.add_cog(cog)
