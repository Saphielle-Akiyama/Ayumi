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

import discord


COLORS = {
    "DEBUG": discord.Color.blue(),
    "INFO": discord.Color.green(),
    "WARNING": discord.Color.gold(),
    "ERROR": discord.Color.red(),
    "CRITICAL": discord.Color.dark_red(),
}


class WebhookHandler(logging.Handler):
    def __init__(self, webhook: discord.Webhook, *, level: int = logging.NOTSET):

        super().__init__(level)

        self.webhook = webhook

        self.loop = asyncio.get_event_loop() 

    def emit(self, record: logging.LogRecord):
        """
        Sends as webhook into the logging channel
        """
        # Embed 

        title = f"Logging from {record.filename}"

        description = "```" + record.msg % record.args + "```"

        color = COLORS.get(record.levelname)
        
        timestamp = datetime.datetime.now(datetime.timezone.utc)

        embed = discord.Embed(

            title=title, 

            description=description, 

            color=color,

            timestamp=timestamp
        )

        # Send

        coro = self.webhook.send(embed=embed)

        self.loop.create_task(coro)

