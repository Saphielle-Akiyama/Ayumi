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

import core
from discord.ext import commands

class AyumiCommand(commands.Command):
    """A subclassed command with some extra utils attributes"""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.example_args = kwargs.get('example_args', None)
        self.differs_in_nsfw = kwargs.get('differs_in_nsfw', False)

    def get_example(self, ctx: core.Context):

        for annotation in self.clean_params.values():

            pass
