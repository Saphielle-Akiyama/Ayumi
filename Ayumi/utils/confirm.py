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
import types

import discord
from discord.ext import commands, menus

class Confirm(menus.Menu):
    """
    An utils class that asks the user to validate a choice
    can be used as a context manager
    """
    def __init__(self, ctx: commands.Context, send_dict: dict, **kwargs):
        super().__init__(**kwargs)
        self.ctx = ctx
        self.send_dict = send_dict
        self.confirmed = False

    async def send_initial_message(self, ctx: commands.Context, channel: discord.abc.Messageable):
        return await channel.send(**self.send_dict)

    async def __aenter__(self):
        await self.start(self.ctx, wait=True)
        return self.confirmed

    async def __aexit__(self, type_: type, value: Exception, traceback: types.TracebackType):
        if type_:
            self.ctx.bot.dispatch("command_error", ctx, value)
    
    @menus.button("\U00002705")  # White heavy check mark
    async def on_check_mark(self, payload: discord.RawReactionActionEvent):
        self.confirmed = True
        self.stop()

    @menus.button("\U0000274c")  # Cross mark
    async def on_cross_mark(self, payload: discord.RawReactionActionEvent):
        self.stop()

