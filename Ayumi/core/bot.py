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

import pathlib
import logging
import traceback
import inspect
from typing import Union, Tuple, Callable, Optional

import discord
from discord.ext import commands, tasks

import aiohttp
import asyncpg

import core
import config
import utils

from . import context
from . import fallback

LOGGING_LEVEL = logging.INFO
EVENT_ERROR_TEMPLATE = "Exception occured in event %s :\n%s"
COMMAND_ERROR_TEMPLATE = "Exception occured in command \"%s\"\n\nCalled with: \"%s\"\n\n%s"

class Bot(commands.Bot):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.load_extension('jishaku')
        self._session = None
        self._webhook = None
        self._logger = None
        self._pool = None

    async def connect(self, *args, **kwargs):
        """Used as an async alternative init"""
        self._session = session = aiohttp.ClientSession()

        self._logger = logger = logging.getLogger('discord')

        adapter = discord.AsyncWebhookAdapter(session)
        self._webhook = discord.Webhook.from_url(config.LOGGER_URL, adapter=adapter)
        logger.setLevel(LOGGING_LEVEL)
        handler = core.WebhookHandler(self, level=LOGGING_LEVEL)
        logger.addHandler(handler)

        logger.info('Started connecting to storage')

        try:
            self._pool = await asyncpg.create_pool(config.PSQL_URL,
                                                   password=config.PSQL_PASSWORD)
        except Exception as e:
            self.dispatch("error", "PSQL connection", exception=e, level='critical')
            self._pool = fallback.Fallback('psql', logger)
        else:
            logger.info('Connected to psql')

        for file in pathlib.Path('./extensions').glob('**/*.py'):
            ext_path = '.'.join(file.parts[:-1]) + '.' + file.stem
            try:
                self.load_extension(ext_path)
            except Exception as e:
                print(e)
            else:
                logger.info('Loaded %s', ext_path)


        logger.info('Finishing initializing')

        return await super().connect(*args, **kwargs)

    @property
    def logger(self) -> logging.Logger:
        return self._logger

    @property
    def pool(self) -> asyncpg.Connection:
        return self._pool

    @property
    def session(self) -> aiohttp.ClientSession:
        return self._session

    @property
    def webhook(self) -> discord.Webhook:
        return self._webhook
    
    # Custom context
    async def get_context(self, msg: discord.Message, cls=context.Context) -> context.Context:
        return await super().get_context(msg, cls=cls)

    # Error handling

    async def on_error(self, event: str, *args, **kwargs):
        """Sends errors over a webhook"""
        if exc := kwargs.get('exception'):
            clean_tb = utils.clean_tb_from_exc(exc)
        else:
            tb = traceback.format_exc()
            clean_tb = utils.clean_tb(tb)
        
        log_method = self.logger.warning
        log_method = kwargs.get('level', log_method)
        log_method(EVENT_ERROR_TEMPLATE, event, clean_tb)
    
    def fuzzy_search_commands(self, user_input: str) -> Optional[commands.Command]:
        command_gen = self.walk_commands()
        commands_names = [*map(str, command_gen)]
        try:
            command_name = utils.Literal[commands_names](user_input)
        except commands.BadArgument:
            return None
        else:
            return self.get_command(command_name)

    async def on_command_error(self, ctx: context.Context, error: Exception):
        """Logs errors for command, then send them into the user"""
        error = getattr(error, "original", error)

        clean_tb = utils.clean_tb_from_exc(error)
        self.logger.warn(
            COMMAND_ERROR_TEMPLATE,
            str(ctx.command),
            ctx.message.content,
            clean_tb
        )
        if isinstance(error, commands.CommandNotFound):
            corrected_command = self.fuzzy_search_commands(ctx.invoked_with)
            if not corrected_command:
                return
            try:
                await corrected_command.can_run(ctx)
            except commands.CommandError:
                return self.dispatch("command_error", ctx, error)
            else:
                ctx.command = corrected_command
                return await ctx.reinvoke(call_hooks=True)
        
        title = f"An error has occured : {error.__class__.__name__}",
        description = utils.to_codeblocks(error, lang='py')
        embed = utils.Embed(title=title, description=description)

        embed.add_field(name="Support server", value=f"[Support server]({config.SUPPORT_SERVER})")

        await ctx.send(embed=embed)

    async def close(self):
        """Close all of our external connections"""
        try:
            await self.pool.close()
        except Exception:
            traceback.print_exc()
        else:
            self.logger.info('Pool is closed')

        try:
            await self.session.close()
        except Exception:
            traceback.print_exc()
        
        return await super().close()
