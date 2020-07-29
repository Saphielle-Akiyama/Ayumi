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

class Fallback:
    """
    A class designed to handle (some) operations without raising any errors
    """
    __slots__ = ()
    
    def __call__(self, *args, **kwargs):
        return self
    
    __getattr__ = __getitem__ = __setitem__ = __call__

    def __await__(self, *args, **kwargs):
        return asyncio.sleep(0, self).__await__()

    def __bool__(self):
        return False

