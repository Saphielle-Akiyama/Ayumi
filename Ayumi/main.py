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

import config
import core
import utils
import logging

if __name__ == '__main__':
    bot = core.Bot(**config.DEFAULT_PARAMETERS)
    bot.run(config.DISCORD_TOKEN)    

