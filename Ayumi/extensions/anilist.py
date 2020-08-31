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
import textwrap
import itertools
import operator
import datetime as dt
from typing import Tuple, Generator, Optional, List, Union

import discord
from discord.ext import commands, menus
import pycountry

import core
import utils

class AnilistError(commands.CommandError):
    """Base class for anilist related errors"""


class NoResultsError(AnilistError):
    def __init__(self, query: str):
        self.query = query

    def __str__(self):
        return f"Sorry ! I couldn't find any results for \"{self.query}\""


class NoScheduleError(AnilistError):
    def __str__(self):
        return f"Sorry ! I couldn't find today's schedule"


class MediaPages(menus.MenuPages):
    """
    Our main menu, able to dynamically add buttons according
    to the list of ListPageSource that got provided
    """
    def __init__(
        self,
        *, 
        main_source: menus.ListPageSource,
        extra_sources: Union[Tuple[menus.ListPageSource], tuple] = (), 
        **options
    ):

        self.initial_source = main_source
        super().__init__(self.initial_source, delete_message_after=True, timeout=60)
        self.extra_sources = {}

        for index, source in enumerate(extra_sources, 3):
            self.extra_sources[source.emoji] = source
            position = menus.Last(index)
            button = menus.Button(source.emoji, self._extra_source_button, position=position)
            self.add_button(button)

    async def _extra_source_button(self, payload: discord.RawReactionActionEvent):
        """A template that is used as the callback for all extra buttons"""
        emoji = str(payload.emoji)
        new_source = self.extra_sources[emoji]
        if self.source is self.initial_source or self.source is not new_source:
            return await self.change_source(new_source)
        else:
            return await self.change_source(self.initial_source)

    async def change_source(self, source: menus.ListPageSource, *,
                            at_index: Optional[int] = None, show_page: bool = True):
        """
        Subclassed to allow being able to display a different index
        and to decide whether to immediatly update or not
        """
        if not isinstance(source, menus.ListPageSource):
            raise TypeError('Expected {0!r} not {1.__class__!r}.'.format(PageSource, source))

        at_index = (at_index, self.current_page)[at_index is None]
        self._source = source
        self.current_page = at_index

        if self.message and show_page:
            await source._prepare_once()
            await self.show_page(at_index)

    async def update(self, payload: discord.RawReactionActionEvent):
        """Returns to the main page everytime a movement button is pressed"""
        if str(payload.emoji) not in self.extra_sources:
            await self.change_source(self.initial_source, show_page=False)
        return await super().update(payload)

    def _skip_single_triangle_buttons(self) -> bool:
        """Skips single triangle buttons if we have only 1 page or less"""
        return self.source.get_max_pages() < 2

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

    @menus.button("clock emoji", position=menus.Last(2))
    async def toggle_reminder(self, payload: discord.RawReactionActionEvent):
        pass




class PresetSource(menus.ListPageSource):
    """A base source that only shows an entry per page"""
    def __init__(self, entries: list):
        super().__init__(entries, per_page=1)

# Media search

MEDIA_SEARCH = """
query ($page: Int, $perPage: Int, $asHtml: Boolean, $characterSort: [CharacterSort], %s) {
    Page (page: $page, perPage: $perPage) {
        media (%s) {
            id
            isAdult
            bannerImage
            coverImage {
                medium
                extraLarge
                color
            }
            title {
                english
                romaji
                native
            }
            seasonYear
            format
            description (asHtml: $asHtml)
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
            }
            season
            countryOfOrigin
            status
            source
            episodes
            duration
            chapters
            volumes
            averageScore
            popularity
            favourites
            hashtag
            idMal
            type
            siteUrl
            trailer {
                site
                id
            }
            streamingEpisodes {
                title
                site
                url
            }
            characters (sort: $characterSort) {
                nodes {
                    name {
                        full
                        native
                    }
                    siteUrl
                }
            }
        }
    }
}
"""

class InformationSource(PresetSource):
    """Provides informations on how to use the menu's buttons"""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.emoji = "\U00002753"

    async def format_page(self, menu: MediaPages, _):

        embed = utils.Embed(title="Help on how to navigate around")

        extra_emojis = [
            f"{emoji} {source.__doc__}"
            for emoji, source
            in menu.extra_sources.items()
            if emoji != self.emoji
        ]
        
        text = (
            f"You left on page {menu.current_page + 1}, "
            "I'll take you back there if you press any button"
        )
        embed.set_footer(text=text)
        return embed(description='\n\n'.join(extra_emojis))


class TemplateMediaSource(PresetSource):
    """Main body that will always be there (title, images, timestamp)"""
    def __init__(self, *args, **kwargs):
        """
        Template, subclasses that aren't the front page
        must have an emoji attribute
        """
        super().__init__(*args, **kwargs)
        self.emoji = None

    def is_paginating(self) -> True:
        """Forcing pagination to always have buttons"""
        return True

    @staticmethod
    def format_title(data: dict) -> str:
        """Formats the title used for the menu source"""
        titles = operator.itemgetter("english", "romaji", "native")(data["title"])
        main_title = next(filter(None, titles))
        f_is_adult = "18+ " if data['isAdult'] else ''
        f_season_year = f"({season_year})" if (season_year := data["seasonYear"]) else ''
        return f"[{f_is_adult}{data['format']}] {main_title} {f_season_year}"

    async def format_page(self, menu: MediaPages, data: dict) -> utils.Embed:
        """Formats the media into a embed showing the main informations"""
        embed = utils.Embed(title=self.format_title(data))
        size = ("medium", "extraLarge")[self.__class__ is TemplateMediaSource]
        if cover_img := data["coverImage"][size]:
            embed.set_thumbnail(url=cover_img)

        if color_hex := data['coverImage']['color']:
            embed.color = int(color_hex[1:], 16)

        if img_url := data["bannerImage"]:
            embed.set_image(url=img_url)

        footer = [f"Page {menu.current_page + 1} out of {self.get_max_pages()}"]

        if next_airing_ep := data["nextAiringEpisode"]:
            embed.timestamp = dt.datetime.fromtimestamp(
                next_airing_ep["airingAt"], 
                tz=dt.timezone.utc
            )
            footer.append("Next airing in your timezone")

        author = menu.ctx.author
        embed.set_author(
            name=f"Requested by {author}",
            url=utils.DM_CHANNEL_URL.format(author.id),
            icon_url=author.avatar_url
        )
        f_footer = " | ".join(footer)
        return embed.set_footer(text=f_footer)

    # Used by subclasses

    @staticmethod
    def _join_inner_tuples(tup: Tuple[str, str]) -> str:
        """Helper function to join title and info together"""
        name, info = tup # making sure that we have 2 values
        return f"**{name}**\n{info}"

    def join_data(self, data: List[Tuple[str, str]]) -> str:
        """Formats all data in the required format"""
        return '\n\n'.join(map(self._join_inner_tuples, data))


class MediaSourceFront(TemplateMediaSource):
    """Main page that is shown to the user"""

    def is_paginating(self) -> True:
        """Forcing pagination to always have buttons"""
        return True

    async def format_page(self, menu: MediaPages, data: dict) -> utils.Embed:
        """Formats the media into a embed showing the main informations"""
        embed = await super().format_page(menu, data)

        if desc := data["description"]:
            return embed(description=utils.remove_html_tags(desc))

        return embed(description="No description provided")


class MediaSourceCalendar(TemplateMediaSource):
    """Airing informations, such as start and end date"""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.emoji = "\U0001f4c6"  # calendar

    @staticmethod
    def format_boundary_dates(data: dict) -> Generator[Tuple[Tuple[str, str]], None, None]:
        prefixes = 'Start', 'End'
        date_info_getter = operator.itemgetter("year", "month", "day")

        for prefix, boundary in zip(prefixes, (data['startDate'], data['endDate'])):
            date_info = date_info_getter(boundary)

            if all(date_info):
                date = dt.datetime(*date_info)
                yield prefix, date.strftime("%A, %d %B %Y")

            elif any(date_info):
                filtered = [f"{d:02}" if d else '00' for d in reversed(date_info)]
                yield prefix, '/'.join(filtered)

            else:
                yield prefix, '?'

    async def format_page(self, menu: MediaPages, data: dict) -> utils.Embed:
        """Adds informations about airing"""
        embed = await super().format_page(menu, data)
        to_join = [*self.format_boundary_dates(data)]

        if next_airing_ep := data["nextAiringEpisode"]:
            airing_at = dt.datetime.fromtimestamp(next_airing_ep["airingAt"])
            f_airing_at = airing_at.strftime("%d %b %Y\n%H:%M UTC")
            to_join.append(("Next airing", f_airing_at))

        if country_of_origin := data["countryOfOrigin"]:
            country = pycountry.countries.get(alpha_2=country_of_origin)
            f_country = getattr(country, "official_name", country.name)
            to_join.append(("Country of origin", f_country))

        if season := data["season"]:
            to_join.append(("Season", season.lower().title()))

        if airing_status := data["status"]:
            to_join.append(("Airing status", airing_status.lower().title()))

        if source := data["source"]:
            f_source = source.replace('_', ' ').lower().title()
            to_join.append(("Source", f_source))

        return embed(description=self.join_data(to_join) or "No airing data")


class MediaSourceStopwatch(TemplateMediaSource):
    """Estimate time to read / watch the media"""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.emoji = "\U000023f1"

    @staticmethod
    def human_duration(duration: int) -> str:
        """Converts a duration in minutes into hours + minutes"""
        hours, minutes = divmod(duration, 60)
        f_hours = f"{hours} hour{'s' if hours > 1 else ''}" if hours else ''
        f_minutes = f"{minutes} minute{'s' if minutes > 1 else ''}" if minutes else ''
        time_components = filter(None, (f_hours, f_minutes))
        return " and ".join(time_components)

    async def format_page(self, menu: MediaPages, data: dict) -> utils.Embed:
        """Adds infos about reading / watching time"""
        embed = await super().format_page(menu, data)
        to_join = []

        watch_flag = 0
        read_flag = 0

        if (episodes := data["episodes"]) and episodes > 1:
            to_join.append(("Episodes", episodes))
            watch_flag += 1

        if duration := data["duration"]:
            to_join.append(("Duration", self.human_duration(duration)))
            watch_flag += 1

        for item_name in ("chapters", "volumes"):
            if item := data[item_name]:
                to_join.append((item_name.title(), item))
                read_flag += 1

        if watch_flag == 2 and episodes > 1:
            human_watch_duration = self.human_duration(episodes * duration)
            to_join.append(("Total watch duration", human_watch_duration))

        elif read_flag == 2:
            # average word amount in a novel / average words read per min => 200 min / vol
            human_read_duration = self.human_duration(item * 200)
            tup = ("Estimated reading time (might be very inaccurate)", human_read_duration)
            to_join.append(tup)

        description = self.join_data(to_join) or "No duration data"
        return embed(description=description)


class MediaSourceSpeechBubble(TemplateMediaSource):
    """Shows user ratings"""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.emoji = "\U0001f4ac"

    @staticmethod
    def to_markdown_twitter_url(hashtag: str) -> str:
        """Transforms a hashtag into a clickable link going to the twitter search page"""
        url = utils.TWITTER_HASHTAG_URL.format(hashtag[1:])
        return f"[{hashtag}]({url})"

    async def format_page(self, menu: MediaPages, data: dict):
        embed = await super().format_page(menu, data)
        to_join = []

        if avg_score := data["averageScore"]:
            to_join.append(("Average score", f"{avg_score}/100"))

        if pop := data["popularity"]:
            to_join.append(("Popularity", f"{pop} users have it on their list"))

        if fav := data["favourites"]:
            to_join.append(("Favourites", f"{fav} users favourited it"))

        if hashtags := data["hashtag"]:
            hashtag_list = hashtags.split()
            mapped = map(self.to_markdown_twitter_url, hashtag_list)
            to_join.append(("Hashtags", ' '.join(mapped)))

        return embed(description=self.join_data(to_join) or "No community data")


class MediaSourceTelevision(TemplateMediaSource):
    """Links to watch / read the media"""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.emoji = "\U0001f4fa"

    @staticmethod
    def get_ep_line(ep: dict, pos_name: str):
        """A helper function to format episodes links"""
        return "[{0} episode - {1[site]}]({1[url]})".format(pos_name, ep)

    async def format_page(self, menu: MediaPages, data: dict):
        embed = await super().format_page(menu, data)
        to_join = []

        if (media_type := data["type"]) and (mal_id := data["idMal"]):
            url = utils.MAL_ANIME_ID_URL.format(media_type.lower(), mal_id)
            to_join.append(("MyAnimeList", f"[Jump url]({url})"))

        if site_url := data["siteUrl"]:
            to_join.append(("Anilist", f"[Jump url]({url})"))

        if trailer := data["trailer"]:
            id_ = trailer["id"]
            site = trailer["site"]
            if site == "youtube":
                url = utils.YOUTUBE_VIDEO_URL.format(id_)
            else:
                url = utils.DAILYMOTION_VIDEO_URL.format(id_)

            to_join.append(("Trailer", f"[{site}]({url})"))

        if streaming_episodes := data["streamingEpisodes"]:
            last_ep, *_, first_ep = streaming_episodes
            pos_names = ("First", "Latest")
            eps = (first_ep, last_ep)
            f_eps = [self.get_ep_line(ep, pos_name) for ep, pos_name in zip(eps, pos_names)]
            to_join.append(("Links to episodes", '\n'.join(f_eps)))

        return embed(description=self.join_data(to_join) or "No watching data")


class MediaSourceFamily(TemplateMediaSource):
    """Links to this show's characters"""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.emoji = "\U0001f46a"

    @staticmethod
    def format_characters(data: dict):
        name = data["name"]
        f_name = name["full"] or name["native"]
        return f"[{f_name}]({data['siteUrl']})"

    async def format_page(self, menu: MediaPages, data: dict):
        embed = await super().format_page(menu, data)
        joined = '\n'.join(map(self.format_characters, data["characters"]["nodes"]))
        to_join = (("Characters", joined),)
        return embed(description=self.join_data(to_join) or "No characters data")


# This isn't dry at all, but it won't be fixed to keep readability up 

SCHEDULE_SEARCH = """
query ($page: Int, $perPage: Int, $asHtml: Boolean, $airingSort: [AiringSort], $airingAfter: Int, \
       $characterSort: [CharacterSort]) {
    Page (page: $page, perPage: $perPage) {
        airingSchedules (airingAt_greater: $airingAfter, sort: $airingSort) {
            media {
                id
                isAdult
                bannerImage
                coverImage {
                    medium
                    extraLarge
                    color
                }
                title {
                    english
                    romaji
                    native
                }
                seasonYear
                format
                description (asHtml: $asHtml)
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
                }
                season
                countryOfOrigin
                status
                source
                episodes
                duration
                chapters
                volumes
                averageScore
                popularity
                favourites
                hashtag
                idMal
                type
                siteUrl
                trailer {
                    site
                    id
                }
                streamingEpisodes {
                    title
                    site
                    url
                }
                characters (sort: $characterSort) {
                    nodes {
                        name {
                            full
                            native
                        }
                        siteUrl
                    }
                }
            }
        }
    }
}
"""

class Anilist(commands.Cog):
    def __init__(self, bot: core.Bot):
        self.bot = bot
        self.url = "https://graphql.anilist.co"
        self.cooldown = commands.CooldownMapping.from_cooldown(1, 10, commands.BucketType.user)
        self.default_variables = {
            "page": 1,
            "perPage": 10,
            "asHtml": False,
            "characterSort": "FAVOURITES_DESC"
        }
        self.sources = (
            MediaSourceFront,
            InformationSource,
            MediaSourceCalendar,
            MediaSourceStopwatch,
            MediaSourceSpeechBubble,
            MediaSourceTelevision,
            MediaSourceFamily,
        )

    async def make_request(self, query: str, variables: dict):
        json_ = {'query': query, 'variables': variables}
        async with self.bot.session.post(self.url, json=json_) as r:
            resp = await r.json()

            if r.status == 200:
                return resp

        errors = [f"{err['status']}: {err['message']}" for err in resp["errors"]]
        formatted_errors = '\n'.join(errors)
        raise commands.BadArgument(formatted_errors)
    
    async def cog_before_invoke(self, ctx: core.Context):
        bucket = self.cooldown.get_bucket(ctx.message)
        if retry_after := bucket.update_rate_limit():
            raise commands.CommandOnCooldown(bucket, retry_after)

    @commands.command()
    async def search(self, ctx: core.Context, *, query: str):
        """Looks for infos about an anime or a manga"""
        params = ["$search: String", "$sort: [MediaSort]",]
        variables = self.default_variables.copy()
        extra_variables = {
            "search": query,
            "sort": "POPULARITY_DESC", 
            "characterSort": "FAVOURITES_DESC"
        }
        variables.update(extra_variables)
             
        if not ctx.is_nsfw:
            params.append("$isAdult: Boolean")
            variables['isAdult'] = False

        params = utils.to_graphql_search_param(*params)
        json_query = MEDIA_SEARCH % params

        response = await self.make_request(json_query, variables)
        if not (results := response['data']['Page']['media']):
            raise NoResultsError(query)

        main_source, *extra_sources = [Source(results) for Source in self.sources]
        menu = MediaPages(main_source=main_source, extra_sources=extra_sources)
        await menu.start(ctx, wait=True)

    @commands.command()
    async def schedule(self, ctx: core.Context):
        """Gives the schedule for upcoming medias"""
        params = ["$airingSort: [AiringSort]"]
        variables = self.default_variables.copy()

        float_timestamp =  dt.datetime.now(tz=dt.timezone.utc).timestamp()
        curr_timestamp = int(float_timestamp)
        extra_variables = {
            "airingSort": "TIME",
            "airingAfter": curr_timestamp
        }
        variables.update(extra_variables)
        params = utils.to_graphql_search_param(*params)
        response = await self.make_request(SCHEDULE_SEARCH, variables)
        if not (nested_results := response["data"]["Page"]["airingSchedules"]):
            raise NoScheduleError()

        unfiltered_results = [res["media"] for res in nested_results]
        results = [res for res in unfiltered_results if not res["isAdult"] or ctx.is_nsfw]
        main_source, *extra_sources = [Source(results) for Source in self.sources]
        
        menu = MediaPages(main_source=main_source, extra_sources=extra_sources)
        await menu.start(ctx, wait=True)




def setup(bot: core.Bot):
    cog = Anilist(bot)
    bot.add_cog(cog)
