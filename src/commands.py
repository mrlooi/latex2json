# src/commands.py

import re
from typing import List, Dict, Optional
from src.patterns import NEWLINE_PATTERN
from src.latex_maps.latex_unicode_converter import LatexUnicodeConverter
from collections import OrderedDict

from src.tex_utils import extract_nested_content_sequence_blocks, substitute_patterns
from src.handlers.content_command import RAW_PATTERNS as CONTENT_COMMANDS
from src.handlers.new_definition import (
    END_CSNAME_PATTERN,
    START_CSNAME_PATTERN,
    extract_and_concat_nested_csname,
)


def substitute_args(definition: str, args: List[str]) -> str:
    """Substitute #1, #2, etc. with the provided arguments in order"""
    result = definition
    for i, arg in enumerate(args, 1):
        if arg is not None:
            result = result.replace(f"#{i}", arg)
    return result


CSNAME_PATTERN = re.compile(
    START_CSNAME_PATTERN.pattern + r"(.*)" + END_CSNAME_PATTERN.pattern
)


def default_ignore_handler(match, text):
    # return empty str to ignore?
    return "", match.end()


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

        def handler(match, text):
            start_pos = match.end()
            end_pos = start_pos
            args = defaults.copy()

            # Handle optional args
            if num_optional:
                blocks, end_pos = extract_nested_content_sequence_blocks(
                    text[start_pos:], "[", "]", num_optional
                )
                end_pos += start_pos
                for i, block in enumerate(blocks):
                    args[i] = block

            args_left = num_args - num_optional
            if args_left > 0:
                start_pos = end_pos
                blocks, end_pos = extract_nested_content_sequence_blocks(
                    text[start_pos:], "{", "}", args_left
                )
                end_pos += start_pos
                for block in blocks:
                    args.append(block)

            # fill remaining args with empty strings
            args.extend([""] * (num_args - len(args)))

            return substitute_args(definition, args), end_pos

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

        def handler(match, text):
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

        command = {
            "pattern": re.compile(r"\\" + var_name + r"(?:true|false)"),
            "handler": default_ignore_handler,
        }
        self.commands["newif:" + var_name] = command

    def process_newlength(self, var_name: str):

        command = {
            "pattern": re.compile(r"\\" + var_name + r"\b"),
            "handler": default_ignore_handler,
        }
        self.commands["newlength:" + var_name] = command

    def process_newcounter(self, var_name: str):

        command = {
            "pattern": re.compile(r"\\the" + var_name + r"\b"),
            "handler": default_ignore_handler,
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
            return handler(match, text)

        prev_text = None
        while prev_text != text:
            prev_text = text
            text = substitute_patterns(text, command2pattern, sub_fn)
        return text, match_count

    def can_handle(self, text: str) -> bool:
        for cmd in self.commands.values():
            if cmd["pattern"].match(text):
                return True
        return CSNAME_PATTERN.match(text) is not None

    def _handle_csname(self, text: str) -> tuple[str, int]:
        match = CSNAME_PATTERN.match(text)
        if match:
            nested, end_pos = extract_and_concat_nested_csname(text)
            if nested:
                for cmd in self.commands.values():
                    match = cmd["pattern"].match(text)
                    if match:
                        out, _ = cmd["handler"](match, text)
                        return out, end_pos
                return "", end_pos
        return text, 0

    def handle(self, text: str) -> str:
        for cmd in self.commands.values():
            match = cmd["pattern"].match(text)
            if match:
                return cmd["handler"](match, text)

        return self._handle_csname(text)
