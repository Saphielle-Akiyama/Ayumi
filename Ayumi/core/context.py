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
    """Subclassed context to have a cache key attribute"""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._altered_cache_key = None

    @property
    def all_args(self) -> str:
        """Retrieves all user input args"""
        args = self.args[2:] if self.command.cog else self.args[1:]
        kwargs = list(self.kwargs.values())
        return ' '.join(args + kwargs)

    @property
    def nsfw_key(self) -> Optional[bool]:
        """Checks if the command differs in nsfw channels"""
        if self.command.differs_in_nsfw:
            return self.channel.is_nsfw()
        return None

    @property
    def cache_key(self) -> str:
        """Generates a cache key for every command"""
        return "{0.command.qualified_name} {0.all_args} {0.nsfw_key}".format(self)

    @cache_key.setter
    def cache_key_setter(self, value: str):
        """Provides a way to set a new key, shouldn't be needed"""
        if not isinstance(value, str):
            raise TypeError("New cache key must be a string")

        self._altered_cache_key = value

