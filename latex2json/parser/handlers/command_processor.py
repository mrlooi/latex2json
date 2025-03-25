# src/commands.py

import re
from typing import List, Dict, Optional, TypedDict, Callable, Pattern, Tuple
from latex2json.latex_maps.latex_unicode_converter import LatexUnicodeConverter

from latex2json.parser.patterns import command_or_dim
from latex2json.parser.handlers.if_else_statements import IfElseBlockHandler
from latex2json.utils.tex_utils import (
    extract_nested_content_sequence_blocks,
    substitute_patterns,
    extract_nested_content,
    substitute_args,
)
from latex2json.parser.handlers.new_definition import (
    END_CSNAME_PATTERN,
    START_CSNAME_PATTERN,
    extract_and_concat_nested_csname,
)


CSNAME_PATTERN = re.compile(
    START_CSNAME_PATTERN.pattern + r"(.*)" + END_CSNAME_PATTERN.pattern
)

COMPARISON_OP_PATTERN = re.compile(r"\s*=\s*%s" % command_or_dim)


class CommandEntry(TypedDict):
    pattern: Pattern[str]
    handler: Callable[[re.Match[str], str, Optional[bool]], Tuple[str, int]]
    definition: Optional[str]


def default_ignore_handler(
    match: re.Match[str], text: str, math_mode: bool = False
) -> Tuple[str, int]:
    # return empty str to ignore?
    return "", match.end()


class CommandProcessor:
    def __init__(self):
        self.commands: Dict[str, CommandEntry] = {}

        # Replace the unicode conversion initialization with LatexUnicodeConverter
        self.unicode_converter = LatexUnicodeConverter()
        self.if_else_handler = IfElseBlockHandler()

    def clear(self):
        self.commands = {}

    def has_command(self, command_name: str) -> bool:
        return command_name in self.commands

    def _parse_definition_conditionals(self, definition: str, usage_pattern: str):
        definition = definition.strip()
        true_block = definition
        false_block = ""

        has_ifstar = definition.startswith(r"\@ifstar")
        if has_ifstar:
            usage_pattern += r"\*?"
            out, pos = self.if_else_handler.handle(definition)
            if out and "ifstar" in out["type"]:
                true_block = out["if_content"] + definition[pos:]
                false_block = out["else_content"] + definition[pos:]

                def get_definition(match: re.Match[str]) -> str:
                    return true_block if match.group(0).endswith("*") else false_block

                return {
                    "get_definition": get_definition,
                    "usage_pattern": usage_pattern,
                }
        return None

    def process_newcommand(
        self,
        command_name: str,
        definition: str,
        num_args: int,
        defaults: List[str],
        usage_pattern: str,
    ):

        get_definition = lambda match: definition
        # hacky??
        check_definition = self._parse_definition_conditionals(
            definition, usage_pattern
        )
        if check_definition:
            get_definition = check_definition["get_definition"]
            usage_pattern = check_definition["usage_pattern"]

        if num_args == 0:

            def handler(
                match: re.Match[str], text: str, math_mode: bool = False
            ) -> Tuple[str, int]:
                return get_definition(match), match.end()

        else:

            def handler(
                match: re.Match[str], text: str, math_mode: bool = False
            ) -> Tuple[str, int]:
                start_pos = match.end()
                end_pos = start_pos
                args = defaults.copy()

                # Handle optional args
                num_optional = len(defaults)
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

                if math_mode:
                    # pad args with spaces
                    args = [" " + arg + " " if arg is not None else arg for arg in args]

                # fill remaining args with empty strings
                args.extend([""] * (num_args - len(args)))

                return substitute_args(get_definition(match), args), end_pos

        try:
            command: CommandEntry = {
                "pattern": re.compile(usage_pattern, re.DOTALL),
                "handler": handler,
                "definition": definition,
            }
            self.commands[command_name] = command
        except Exception as e:
            print(f"Error processing newcommand {command_name}: {e}")
            raise e

    def process_paired_delimiter(
        self, command_name: str, left_delim: str, right_delim: str
    ):
        """Process a paired delimiter command like \br{content}"""
        usage_pattern = r"\\" + command_name + r"\s*{"

        def handler(
            match: re.Match[str], text: str, math_mode: bool = False
        ) -> Tuple[str, int]:
            start_pos = match.end() - 1
            content, end_pos = extract_nested_content(text[start_pos:], "{", "}")
            if content is None:
                return "", start_pos

            if math_mode:
                content = " " + content + " "

            end_pos += start_pos
            return f"{left_delim}{content}{right_delim}", end_pos

        try:
            command: CommandEntry = {
                "pattern": re.compile(usage_pattern, re.DOTALL),
                "handler": handler,
            }
            self.commands[command_name] = command
        except Exception as e:
            print(f"Error processing paired delimiter {command_name}: {e}")
            raise e

    def process_newdef(
        self,
        command_name: str,
        definition: str,
        num_args: int,
        usage_pattern: str,
        expand_definition=False,
    ):
        get_definition = lambda match: definition
        if num_args == 0:
            # hacky??
            check_definition = self._parse_definition_conditionals(
                definition, usage_pattern
            )
            if check_definition:
                get_definition = check_definition["get_definition"]
                usage_pattern = check_definition["usage_pattern"]

        def handler(
            match: re.Match[str], text: str, math_mode: bool = False
        ) -> Tuple[str, int]:
            args = []
            for g in match.groups():
                if g is not None:
                    args.append(g if not math_mode else " " + g + " ")

            return substitute_args(get_definition(match), args), match.end()

        if expand_definition:
            definition = self.expand_commands(definition, True)[0]

        try:
            command: CommandEntry = {
                "pattern": re.compile(usage_pattern, re.DOTALL),
                "handler": handler,
                "definition": definition,
            }
            self.commands[command_name] = command
        except Exception as e:
            print(f"Error processing newdef {command_name}: {e}")
            raise e

    def process_newif(self, var_name: str):
        command: CommandEntry = {
            "pattern": re.compile(r"\\" + var_name + r"(?:true|false)"),
            "handler": default_ignore_handler,
        }
        self.commands["newif:" + var_name] = command

    def process_newlength(self, var_name: str):
        self.process_newX(var_name, "newlength")

    def process_newtoks(self, var_name: str):
        def handler(
            match: re.Match[str], text: str, math_mode: bool = False
        ) -> Tuple[str, int]:
            # check if there is traling { ... } # we strip this out if exists
            start_pos = match.end()
            content, end_pos = extract_nested_content(text[start_pos:], "{", "}")
            if content is None:
                return "", start_pos
            # ignore the trailing {...} anyway
            return "", start_pos + end_pos

        command: CommandEntry = {
            "pattern": re.compile(r"\\" + var_name + r"\b"),
            "handler": handler,
        }
        self.commands["newtoks:" + var_name] = command

    def process_newX(self, var_name: str, type: str = "newX"):
        command: CommandEntry = {
            "pattern": re.compile(r"\\" + var_name + r"\b"),
            "handler": default_ignore_handler,
        }
        self.commands[type + ":" + var_name] = command

    def process_newcounter(self, var_name: str):

        command: CommandEntry = {
            "pattern": re.compile(r"\\the" + var_name + r"\b"),
            "handler": default_ignore_handler,
        }
        self.commands["newcounter:" + var_name] = command

    def expand_commands(
        self, text: str, ignore_unicode: bool = False, math_mode: bool = False
    ) -> tuple[str, int]:
        """Recursively expand defined commands in the text until no further expansions are possible."""
        text, match_count = self._expand(text, math_mode=math_mode)

        # Handle unicode conversions using the converter
        if not ignore_unicode:
            text = self.unicode_converter.convert(text)

        return text, match_count

    def _expand(
        self, text: str, math_mode: bool = False, max_depth: int = 1000
    ) -> tuple[str, int]:
        """Recursively expand defined commands in the text until no further expansions are possible."""
        match_count = 0
        depth = 0

        commands = self.commands
        command2pattern = {name: cmd["pattern"] for name, cmd in commands.items()}

        def sub_fn(text, match, cmd_name):
            nonlocal match_count
            match_count += 1
            if cmd_name not in commands:
                return match.group(0), match.end()
            handler = commands[cmd_name]["handler"]
            return handler(match, text, math_mode=math_mode)

        prev_text = None
        while prev_text != text:
            depth += 1
            if depth > max_depth:
                raise RecursionError(
                    f"Maximum recursion depth ({max_depth}) exceeded. Possible infinite loop in LaTeX commands."
                )
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

    def _handle(self, text: str) -> str:
        for cmd in self.commands.values():
            match = cmd["pattern"].match(text)
            if match:
                out, end_pos = cmd["handler"](match, text)
                if match.group(0) == out:  # prevent infinite loop
                    return "", match.end()
                return out, end_pos

        return self._handle_csname(text)

    def handle(self, text: str) -> str:
        out, end_pos = self._handle(text)
        if end_pos > 0:
            # check if next token is =<>
            comp_op_match = COMPARISON_OP_PATTERN.match(text[end_pos:])
            if comp_op_match:
                return "", end_pos + comp_op_match.end()
        return out, end_pos


if __name__ == "__main__":
    from latex2json.parser.handlers.new_definition import NewDefinitionHandler

    handler = NewDefinitionHandler()

    content = r"\newcommand{\cmd}{\@ifstar{star}{nostar}}"
    token, pos = handler.handle(content)

    processor = CommandProcessor()
    processor.process_newcommand(
        token["name"],
        token["content"],
        token["num_args"],
        token["defaults"],
        token["usage_pattern"],
    )

    out, pos = processor.handle(r"\cmd=2")
    print(out, pos)
