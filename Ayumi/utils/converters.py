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

import operator
import difflib
from typing import List, Tuple, Callable, Optional

from discord.ext import commands

import core


class Literal:
    """
    A converter that tries to match a literal set of values
    """
    @staticmethod
    def get_ratio(left: str, right: str) -> Tuple[float, str]:
        """Avoids having to stick everything in a single line"""
        return difflib.SequenceMatcher(None, left, right).quick_ratio(), left

    def __class_getitem__(cls, values: tuple) -> Callable[[str], Optional[str]]:
        """The converter factory"""
        def actual_converter(arg: str) -> Optional[str]:
            """The converter that we return"""

            arg = arg.casefold()

            # We got a full match

            if arg in values:
                return arg

            # Using it's index (would make sense for months)

            try:
                return values[int(arg) - 1]
            except (IndexError, ValueError):
                pass

            # Difflib

            matches = [cls.get_ratio(compared, arg) for compared in values]
            default = 0, 0
            best_ratio, best_match, = max(matches, key=operator.itemgetter(0), default=default)
            if best_ratio > .75:
                return best_match

            # No match

            message = f'Sorry ! I failed to match {arg} with an item in {values}'

            raise commands.BadArgument(message=message)

        return actual_converter


