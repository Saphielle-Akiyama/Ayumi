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

from discord.ext import commands


class Command(commands.Command):
    """Differs in nsfw kwarg"""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.differs_in_nsfw_channel = kwargs.get('differs_in_nsfw_channel', False) 


def command(name=None, cls=Command, **attrs):
    """Use our subclass by default"""
    return commands.command(name=name, cls=cls, **attrs)

class Group(Command, commands.Group):
    """Copypaste of the superclass to use our subclassed stuff"""
    def group(self, *args, **kwargs):
        def decorator(func):
            kwargs.setdefault('parent', self)
            result = group(*args, **kwargs)(func)
            self.add_command(result)
            return result
        return decorator

    def command(self, *args, **kwargs):
        def decorator(func):
            kwargs.setdefault('parent', self)
            result = command(*args, **kwargs)(func)
            self.add_command(result)
            return result
        return decorator

def group(name=None, **attrs):
    """
    Copypaste of the commands.group to use our superclass
    without having to explicitely pass cls everywhere
    """
    attrs.setdefault('cls', Group)
    return command(name=name, **attrs)
