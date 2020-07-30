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

from typing import Optional

import discord
from discord.ext import commands


class Context(commands.Context):
    @property
    def all_args(self) -> list:
        """Retrieves all user input args"""
        args = self.args[2:] if self.command.cog else self.args[1:]
        kwargs = [*self.kwargs.values()]
        return args + kwargs
    
    @property
    def is_nsfw(self) -> bool:
        return self.channel.is_nsfw()
