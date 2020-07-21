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

import logging

import discord
from discord.ext import commands

import aiohttp
import aioredis

import core
import config

class Bot(commands.Bot):
    
    # Both of those are used as init

    def __init__(self, *args, **kwargs):

        super().__init__(*args, **kwargs)

        self.load_extension('jishaku')

    async def connect(self, *args, **kwargs):
        """Used as an async alternative init"""

        # Aiohttp

        self._session = session = aiohttp.ClientSession()

        # Logging

        adapter = discord.AsyncWebhookAdapter(session)

        self._webhook = webhook = discord.Webhook.from_url(config.LOGGER_URL, adapter=adapter)

        self._logger = logger = logging.getLogger('discord')

        logger.setLevel(config.LOGGING_LEVEL)

        handler = core.WebhookHandler(webhook, level=config.LOGGING_LEVEL)
        
        logger.addHandler(handler)

        # Redis

        self._redis = await aioredis.create_redis_pool('redis://localhost')
        
        # Finalize

        logger.info('Finishing initializing')

        return await super().connect(*args, **kwargs)


    # Let's avoid accidentally modifying those


    @property
    def logger(self) -> logging.Logger:
        return self._logger

    @property
    def redis(self) -> aioredis.Redis:
        return self._redis

    @property
    def session(self) -> aiohttp.ClientSession:
        return self._session

    @property
    def webhook(self) -> discord.Webhook:
        return self._webhook


    # Cleanup


    async def close(self):
        """Close all of our external connections"""

        self.redis.close()

        await self._session.close()

        return await super().close()
