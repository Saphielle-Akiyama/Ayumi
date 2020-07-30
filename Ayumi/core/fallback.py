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

import asyncio
import logging

WARN_TEMPLATE = ("Attempted to access %s with:\n-args:%s\n-kwargs:%s\n")
INIT_TEMPLATE = "Created a fallback for %s"

class Fallback:
    """
    A class designed to handle (some) operations without raising any errors
    """
    def __init__(self, name: str, logger: logging.Logger):
        self.name = name
        self.logger = logger
        self.logger.warning(INIT_TEMPLATE, name)

    def __call__(self, *args, **kwargs):
        self.logger.warning(WARN_TEMPLATE, self.name, str(args), str(kwargs))
        return self
    
    __getattr__ = __getitem__ = __setitem__ = __call__

    def __await__(self, *args, **kwargs):
        self(*args, **kwargs)
        return asyncio.sleep(0, self).__await__()

    def __bool__(self):
        return False

