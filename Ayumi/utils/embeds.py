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
import random
import math
import re

import discord
from discord.ext import commands
from jishaku import codeblocks

from typing import Optional, Tuple, Callable, Union


MARKDOWN_URL_REGEX = re.compile(r"\[(?P<visible_name>.+)\]\(.+\)")

ITERABLES = (list, tuple)

def flatten_nested(iterable: Union[ITERABLES]):
    """A helper function that flatten nested iterables"""
    for item in iterable:
        if isinstance(item, ITERABLES):
            yield from flatten_nested(item)
        else:
            yield item

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
   
    @staticmethod
    def return_visible_part(match: re.Match):
        """Returns only the visible name"""
        return match.group('visible_name')

    def default_field_sort_key(self, field: dict) -> int:
        """Returns the field value's visible length, accounts for url markdown"""
        value = field['value']
        cleaned_value = re.sub(MARKDOWN_URL_REGEX, self.return_visible_part, value) 
        return len(cleaned_value) * -1   # we want the biggest one first without using the 
                                         # reversed flag so other keys don't have to do it too

    def sort_fields(self, key: Optional[Callable] = None):
        """
        Sorts the embed's fields according to a key accounting 
        for inlines the callable
        must take a dict containing, the field's name, value and inline state
        returns self for fluid chaining
        """
        if len(self._fields) < 2:
            return self

        key = key or self.default_field_sort_key
        
        grouped_fields = []
        temp = [] 

        last_inline_state = self._fields[0]['inline']
        for field in self._fields:
            if field['inline'] == last_inline_state:
                temp.append(field)
            else:
                grouped_fields.append(temp)
                temp = [field]
                last_inline_state = not last_inline_state
        if temp:
            grouped_fields.append(temp)
        
        sorted_groups = [[*sorted(field_group, key=key)] for field_group in grouped_fields]
        self._fields = [*flatten_nested(sorted_groups)]
            




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
        description = self.description
        paginator = commands.Paginator(
            max_size=2048, 
            prefix=prefix,
            suffix=suffix,
        )
       
        # Filling the description first
        
        if not self.description:
            return
        
        try:
            for line in description.split('\n'):
                paginator.add_line(line)
        except RuntimeError:
            paginator.clear()
            for line in textwrap.wrap(description, width=95):
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

