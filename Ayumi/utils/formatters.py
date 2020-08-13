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
from typing import Tuple

URL_REGEX = re.compile(r"(?P<full_match>\"https?://(?P<domain_name>.+)/.+\")")
HTML_TAG_REGEX = re.compile(r"<.+>")

INDENT = '\u200b '


def to_codeblocks(arg: str, lang: str = '') -> str:
    """Turns a string into a codeblock one"""
    return f"```{lang}\n{arg}```"


def line_no_dedent(line: str) -> str:
    """Prevents discord from dedenting a line"""
    initial_length = len(line)

    lstripped = line.lstrip()
    lstripped_length = len(lstripped)

    diff = initial_length - lstripped_length

    if diff != 0:
        return line.replace(' ', INDENT, diff)

    return line


def text_no_dedent(arg: str):
    """Prevents discord from dedenting a text"""
    splitted = arg.split('\n')
    mapped = map(line_no_dedent, splitted)
    return '\n'.join(mapped)


def indent(line: str, *, count: int = 4) -> str:
    """Indents a line in a way that discord doesn't dedent it"""
    return f"{INDENT * count}{line}"


def to_url_markdown(match: re.Match) -> str:
    """A helper function that replaces urls with their markdown version"""
    domain_name = match.group('domain_name')
    full_match = match.group('full_match')

    return f"[{domain_name}]({full_match})"


def shorten_urls(arg: str):
    """Transforms urls into markdown to avoid showing the full link"""
    return re.sub(URL_REGEX, to_url_markdown, arg)


def remove_html_tags(arg: str) -> str:
    """Removes all html tags for a string, option seems weird"""
    return re.sub(HTML_TAG_REGEX, '', arg)


def split_by_caps(char: str) -> str:
    """Helper function that returns a whitespace + the lowercase letter
    if the char is lower"""
    if char.islower():
        return char
    lower = char.lower()
    return f" {lower}"


def camelcase_to_natural(arg: str) -> str:
    """camelCase -> camel case"""
    mapped = map(split_by_caps, arg)
    return ''.join(mapped)


def to_graphql_search_param(*data: str):
    """Makes it easier to format graphql search data"""
    media_params = []

    for param in data:
        arg_pointer, _ = param.split(':')

        arg_name = arg_pointer[1:]
        media_params.append(f"{arg_name}: {arg_pointer}")

    return ', '.join(data), ', '.join(media_params)


