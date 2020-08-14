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
import itertools
import operator
import datetime as dt
from typing import Tuple, Generator, Optional, List

import discord
from discord.ext import commands, menus
import pycountry

import core
import utils

QUERY_TEMPLATE = """
query ($page: Int, $perPage: Int, $asHtml: Boolean, %s) {
    Page (page: $page, perPage: $perPage) {
        media (%s) {
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

        }
    }
}
"""

class NoResultsError(commands.CommandError):
    def __init__(self, query: str):
        self.query = query

    def __str__(self):
        return f"Sorry ! I couldn't find any results for \"{self.query}\""


class MediaPages(menus.MenuPages):
    """
    Our main menu, able to dynamically add buttons according
    to the list of ListPageSource that got provided
    """
    def __init__(self, entries: list, *, extra_sources: Tuple[type],  **options):
        self.initial_source = MediaSourceFront(entries)
        super().__init__(self.initial_source, delete_message_after=True, timeout=60)
        self.extra_sources = {}

        for index, ExtraSource in enumerate(extra_sources, 2):
            source = ExtraSource(entries)
            self.extra_sources[source.emoji] = source

            button = menus.Button(
                source.emoji,
                self._extra_source_button_template,
                position=menus.Last(index),
            )

            self.add_button(button)

    async def _extra_source_button_template(self, payload: discord.RawReactionActionEvent):
        """A template that is used as the callback for all extra buttons"""
        emoji = str(payload.emoji)
        if self.source is self.initial_source:
            source = self.extra_sources[emoji]
        elif self.source is not (new_source := self.extra_sources[emoji]):
            source = new_source
        else:
            source = self.initial_source

        await self.change_source(source)

    async def change_source(self, source: menus.ListPageSource, *,
                            at_index: Optional[int] = None, show_page: bool = True):
        """
        Subclassed to allow being able to display a different index
        and to decide whether to immediatly update or not
        """
        if not isinstance(source, menus.ListPageSource):
            raise TypeError('Expected {0!r} not {1.__class__!r}.'.format(PageSource, source))
        
        at_index = at_index or self.current_page
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


class PresetSource(menus.ListPageSource):
    """The base source that only shows an entry per page"""
    def __init__(self, entries: list):
        super().__init__(entries, per_page=1)


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
        size = "extraLarge" if self.__class__ is TemplateMediaSource else "medium"

        if cover_img := data["coverImage"][size]:
            embed.set_thumbnail(url=cover_img)

        if color_hex := data['coverImage']['color']:
            embed.color = int(color_hex[1:], 16)

        if img_url := data["bannerImage"]:
            embed.set_image(url=img_url)

        footer = [f"Page {menu.current_page + 1} out of {self.get_max_pages()}"]

        if next_airing_ep := data["nextAiringEpisode"]:
            embed.timestamp = dt.datetime.fromtimestamp(next_airing_ep["airingAt"])
            footer.append("Next airing in your timezone")
        
        author = menu.ctx.author
        embed.set_author(
            name=f"Requested by {author}", 
            url=utils.DM_CHANNEL_URL.format(author.id),
            icon_url=author.avatar_url
        )
        
        return embed.set_footer(text=" | ".join(footer))

    # Used by subclasses

    @staticmethod
    def _join_inner_tuples(tup: Tuple[str, str]) -> str:
        """Helper function to join title and info together"""
        return "**{}**\n{}".format(*tup)  # will error out if we miss smth

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
    """
    Page displayed when the user clicks on the calendar
    provides infos about airing
    """
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
            to_join.append(("Source", source.replace('_', ' ').lower().title()))

        return embed(description=self.join_data(to_join) or "No airing data")


class MediaSourceStopwatch(TemplateMediaSource):
    """
    Page displayed when the user clicks on the stopwatch
    provides infos about reading / watching times
    """
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
            to_join.append(("Estimated read time (might be very inaccurate)", human_read_duration))

        return embed(description=self.join_data(to_join) or "No duration data")


class MediaSourceSpeechBubble(TemplateMediaSource):
    """
    Page displayed when the user clicks on the speech bubble
    Displays infos about user ratings
    """
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
    """
    Page displayed when the users clicks on the television 
    Displays information
    """
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
            first_ep, *_, last_ep = streaming_episodes
            
            pos_names = ("First", "Latest")
            eps = (first_ep, last_ep)  
            f_eps = [self.get_ep_line(ep, pos_name) for ep, pos_name in zip(eps, pos_names)]
            to_join.append(("Links to episodes", '\n'.join(f_eps)))

        return embed(description=self.join_data(to_join) or "No watching data")


class Anilist(commands.Cog):
    def __init__(self, bot: core.Bot):
        self.bot = bot
        self.url = "https://graphql.anilist.co"

    async def make_request(self, query: str, variables: dict):
        json_ = {'query': query, 'variables': variables}
        async with self.bot.session.post(self.url, json=json_) as r:
            resp = await r.json()

            if r.status != 200:
                errors = [f"{err['status']}: {err['message']}" for err in data["errors"]]
                formatted_errors = '\n'.join(errors)
                raise commands.BadArgument(formatted_errors)

        return resp['data']['Page']['media']

    @commands.command()
    async def search(self, ctx: core.Context, *, query: str):
        """Looks for infos about an anime or a manga"""
        params = ["$search: String", "$sort: [MediaSort]"]

        variables = {
            "search": query,
            "page": 1,
            "perPage": 10,
            "asHtml": False,
            "sort": "POPULARITY_DESC",
        }

        if not ctx.is_nsfw:  # filters out hentais and stuff
            params.append("$isAdult: Boolean")
            variables['isAdult'] = False

        params = utils.to_graphql_search_param(*params)

        json_query = QUERY_TEMPLATE % params

        if not (results := await self.make_request(json_query, variables)):
            raise NoResultsError(query)
 
        extra_sources = (
            MediaSourceCalendar, 
            MediaSourceStopwatch, 
            MediaSourceSpeechBubble,
            MediaSourceTelevision
        )
        menu = MediaPages(results, extra_sources=extra_sources)

        await menu.start(ctx, wait=True)


def setup(bot: core.Bot):
    cog = Anilist(bot)
    bot.add_cog(cog)
