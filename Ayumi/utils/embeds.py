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

import random
import math

import discord
from discord.ext import commands
from jishaku import codeblocks

from typing import Optional, Tuple


class Embed(discord.Embed):
    def __init__(self, **options):
        super().__init__(**options)
        self.default_inline = options.get('default_inline', True)

        if isinstance(self.colour, discord.Embed.Empty.__class__):
            self.colour = discord.Colour.from_hsv(random.random(), random.uniform(0.75, 0.95), 1)

    def add_field(self, *, name: str, value: str, inline: Optional[bool] = None):
        """Uses a default inline, I guess"""
        inline = self.default_inline if inline is None else inline
        return super().add_field(name=name, value=value, inline=inline)

    def add_fields(self, *fields: Tuple[str, str, Optional[bool]]):
        """Adds multiple fields at once, represented in form of tuples"""
        for field in fields:
            name, *value_and_inline = field

            if len(value_and_inline) == 2:
                value, inline = value_and_inline
                self.add_field(name=name, value=value, inline=inline)

            else:
                self.add_field(name=name, value=value_and_inline[0])

    def fill_fields(self): # This is probably overcomplicated, will check later
        """Fill the remaining fields so they are lined up properly"""
        inlines = len(self.fields[max(i for i, _ in enumerate(self.fields)):]) + 1

        for _ in range(math.ceil(inlines / 3) * 3 - inlines):
            self.add_field(name='\u200b', value='\u200b')

        return self


class LongEmbed(Embed):
    """Long embed used for text that stretches vertically"""
    def remove_codeblocks(self, page: str):
        """Removes the prefix and suffix to replace them properly"""
        _, content = codeblocks.codeblock_converter(page)

        return content.strip()

    def __init__(self, **options):
        super().__init__(**options)
        
        self.prefix = prefix = options.get('prefix', "```")
        self.suffix = suffix = options.get('suffix', "```")

        paginator = commands.Paginator(
            max_size=2048, 
            prefix=prefix,
            suffix=suffix,
        )
       
        # Filling the description first

        if not self.description:
            return
        
        for line in self.description.split('\n'):
            paginator.add_line(line)
        
        self.description, *rest = paginator.pages

        if not rest:
            return

        # Now the fields
        
        paginator.max_size = 1024
        paginator.clear()

        cleaned = map(self.remove_codeblocks, rest)
      
        no_empty = filter(None, cleaned)

        regrouped = ''.join(no_empty)

        for line in regrouped.split('\n'):
            paginator.add_line(line)

        for page in paginator.pages:
            self.add_field(name='\u200b', value=page, inline=False)

