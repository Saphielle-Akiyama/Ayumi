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

import discord
from discord.ext import commands

import aiohttp
import aioredis

class Bot(commands.Bot):

    def __init__(self, *args, **kwargs):

        super().__init__(self, *args, **kwargs)

        self.load_extension('jishaku')


    async def connect(self, *args, **kwargs):
        """Used as an async alternative init"""

        self._session = session = aiohttp.ClientSession()

        adapter = discord.AsyncWebhookAdapter(session)

        self._logger = discord.Webhook.from_url(config.LOGGER_URL, adapter=adapter)

        self._redis = await aioredis.create_redis_pool('redis://localhost')

        return await super().connect(*args, **kwargs)

    # Let's avoid accidentally modifying those

    @property
    def session(self) -> aiohttp.ClientSession:
        return self._session


    @property
    def redis(self) -> aioredis.Redis:
        return self._redis


    async def close(self):
        """Close all of our external connections"""

        self.redis.close()
        await self._session.close()

        return await super().close()
