# src/commands.py

import re
from typing import List, Dict, Optional
from src.patterns import NEWLINE_PATTERN
from src.latex_maps.latex_unicode_converter import LatexUnicodeConverter
from collections import OrderedDict

from src.tex_utils import substitute_patterns
from src.handlers.content_command import RAW_PATTERNS as CONTENT_COMMANDS


def substitute_args(definition: str, args: List[str]) -> str:
    """Substitute #1, #2, etc. with the provided arguments in order"""
    result = definition
    # Sort in reverse order to handle #10 before #1, etc.
    for i, arg in enumerate(args, 1):
        if arg is not None:  # Only substitute if we have a value
            result = result.replace(f"#{i}", arg)
    return result


class CommandProcessor:
    def __init__(self):
        self.commands: Dict[str, Dict[str, any]] = {}

        # Replace the unicode conversion initialization with LatexUnicodeConverter
        self.unicode_converter = LatexUnicodeConverter()

    def clear(self):
        self.commands = {}

    def has_command(self, command_name: str) -> bool:
        return command_name in self.commands

    def process_newcommand(
        self,
        command_name: str,
        definition: str,
        num_args: int,
        defaults: List[str],
        usage_pattern: str,
    ):
        if command_name in CONTENT_COMMANDS:
            return

        num_optional = len(defaults)

        def handler(match):
            groups = match.groups()
            args = []

            # Handle optional args
            if num_optional:
                args.extend(
                    groups[i] if groups[i] is not None else defaults[i]
                    for i in range(num_optional)
                )

            # Add required args
            args.extend(groups[num_optional:num_args])

            return substitute_args(definition, args), match.end()

        try:
            command = {
                "pattern": re.compile(usage_pattern, re.DOTALL),
                "handler": handler,
            }
            self.commands[command_name] = command
        except Exception as e:
            print(f"Error processing newcommand {command_name}: {e}")
            raise e

    def process_newdef(
        self,
        command_name: str,
        definition: str,
        num_args: int,
        usage_pattern: str,
        expand_definition=False,
    ):
        if command_name in CONTENT_COMMANDS:
            return

        def handler(match):
            args = [g for g in match.groups() if g is not None]

            return substitute_args(definition, args), match.end()

        if expand_definition:
            definition = self.expand_commands(definition, True)[0]

        try:
            command = {
                "pattern": re.compile(usage_pattern, re.DOTALL),
                "handler": handler,
            }
            self.commands[command_name] = command
        except Exception as e:
            print(f"Error processing newdef {command_name}: {e}")
            raise e

    def process_newif(self, var_name: str):
        def handler(match):
            # return empty str to ignore?
            return "", match.end()

        command = {
            "pattern": re.compile(r"\\" + var_name + r"(?:true|false)"),
            "handler": handler,
        }
        self.commands["newif:" + var_name] = command

    def process_newlength(self, var_name: str):
        def handler(match):
            # return empty str to ignore?
            return "", match.end()

        command = {
            "pattern": re.compile(r"\\" + var_name + r"\b"),
            "handler": handler,
        }
        self.commands["newlength:" + var_name] = command

    def process_newcounter(self, var_name: str):
        def handler(match):
            # return empty str to ignore?
            return "", match.end()

        command = {
            "pattern": re.compile(r"\\the" + var_name + r"\b"),
            "handler": handler,
        }
        self.commands["newcounter:" + var_name] = command

    def expand_commands(
        self, text: str, ignore_unicode: bool = False
    ) -> tuple[str, int]:
        """Recursively expand defined commands in the text until no further expansions are possible."""
        text, match_count = self._expand(text)

        # Handle unicode conversions using the converter
        if not ignore_unicode:
            text = self.unicode_converter.convert(text)

        return text, match_count

    def _expand(self, text: str) -> tuple[str, int]:
        """Recursively expand defined commands in the text until no further expansions are possible."""
        match_count = 0

        commands = self.commands
        command2pattern = {name: cmd["pattern"] for name, cmd in commands.items()}

        def sub_fn(text, match, cmd_name):
            nonlocal match_count
            match_count += 1
            if cmd_name not in commands:
                return match.group(0), match.end()
            handler = commands[cmd_name]["handler"]
            return handler(match)

        prev_text = None
        while prev_text != text:
            prev_text = text
            text = substitute_patterns(text, command2pattern, sub_fn)
        return text, match_count

    def can_handle(self, text: str) -> bool:
        matched = False
        for cmd in self.commands.values():
            if cmd["pattern"].match(text):
                matched = True
                break
        return matched

    def handle(self, text: str) -> str:
        for cmd in self.commands.values():
            match = cmd["pattern"].match(text)
            if match:
                out, end_pos = cmd["handler"](match)
                return out, end_pos
        return text, 0
