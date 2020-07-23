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

import re
import textwrap
import traceback
from typing import Tuple
from types import TracebackType

FILE_PATTERN = re.compile(r"\sFile \"(?P<path>.+)\"")
SLASH_PATTERN = re.compile(r"\\|/")


def to_exc_info(exception: Exception) -> Tuple[type, Exception, TracebackType]:
    """An equivalent of sys.exc_info() that uses an exception"""
    return exception.__class__, exception, exception.__traceback__


def reduce_tb_fp(match: re.Match) -> str:
    """Cleans up a file path in an exception"""
    path = match.group('path')
    splitted = re.split(SLASH_PATTERN, path)
    relevant = splitted[-2:]
    joined = '/'.join(relevant)
    return f"File \"{joined}\""


def clean_tb(traceback: str) -> str:
    """Cleans up a traceback"""
    return re.sub(FILE_PATTERN, reduce_tb_fp, traceback)


def tb_from_exc(exception: Exception) -> str:
    """Traceback from an exception"""
    exc_info = to_exc_info(exception)
    lines = traceback.format_exception(*exc_info)
    return ''.join(lines)


def clean_tb_from_exc(exc: Exception) -> str:
    """Returns a cleaned traceback from only an exception"""
    tb = tb_from_exc(exc)
    return clean_tb(tb)

