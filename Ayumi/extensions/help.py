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

from typing import List

import discord
from discord.ext import commands, menus

import core
import utils

class HelpSource(menus.ListPageSource):
    def __init__(self, entries: List[str]):
        super().__init__(entries, per_page=1)
    
    async def format_page(self, menu: menus.MenuPages, entry: str):
        return utils.Embed(description=entry)


class Help(commands.MinimalHelpCommand):
    async def send_pages(self):
        """Starts a menu session with the pages (there should be only one)"""
        source = HelpSource(self.paginator.pages)
        menu = menus.MenuPages(source, delete_message_after=True)
        await menu.start(self.context, channel=self.get_destination(), wait=True)
    

class Meta(commands.Cog):
    def __init__(self, bot: core.Bot):
        self.bot = bot
        self.original_help_command = bot.help_command
        bot.help_command = Help()
        bot.help_command.cog = self
    
    def cog_unload(self):
        self.bot.help_command = self.original_help_command
        
def setup(bot: core.Bot):
    cog = Meta(bot)
    bot.add_cog(cog)

