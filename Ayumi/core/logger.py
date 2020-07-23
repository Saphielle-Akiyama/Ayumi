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
import datetime
import logging
from typing import List

import discord
from discord.ext import commands

import utils
from . import bot

COLORS = {
    "DEBUG": discord.Color.blue(),
    "INFO": discord.Color.green(),
    "WARNING": discord.Color.gold(),
    "ERROR": discord.Color.red(),
    "CRITICAL": discord.Color.dark_red(),
}

NEED_FULL_MESSAGE = {"ERROR", "CRITICAL"}
MAGNIFYING_GLASS = "\U0001f50e"


class WebhookHandler(logging.Handler):
    def __init__(self, bot: bot.Bot, *, level: int = logging.NOTSET):
        super().__init__(level)
        self.webhook = bot.webhook
        self.bot = bot
        self.loop = bot.loop
        self.queue = asyncio.Queue() 
        coro = self.send_webhooks()
        self.loop.create_task(coro)

    async def send_webhooks(self):
        """
        Sends webhooks to the log channel,
        tries to send them in one message if possible
        """
        while not self.bot.is_closed():
            embed = await self.queue.get()
            embeds = [embed]

            await asyncio.sleep(1)
            
            queue_size = self.queue.qsize()
            
            amount_to_get = min(queue_size, 9)

            for _ in range(amount_to_get):
                embed = self.queue.get_nowait()
                embeds.append(embed)
            
            await self.webhook.send(embeds=embeds)


    def emit(self, record: logging.LogRecord):
        """
        Formats the record then sends it
        """
        paginator = commands.Paginator(prefix="```py")
        formatted = record.msg % record.args

        embed = utils.LongEmbed(
            title="[{0.levelname}] handled by {0.filename} in {0.funcName}".format(record),
            color=COLORS.get(record.levelname),
            timestamp=datetime.datetime.now(datetime.timezone.utc),
            description=formatted,
            prefix="```py"
        )

        self.queue.put_nowait(embed)

