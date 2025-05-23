# src/commands.py

import re
from typing import List, Dict, Optional, TypedDict, Callable, Pattern, Tuple
from latex2json.latex_maps.latex_unicode_converter import LatexUnicodeConverter

# from latex2json.parser.patterns import command_or_dim
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
    command_pattern,
)


CSNAME_PATTERN = re.compile(
    START_CSNAME_PATTERN.pattern + r"(.*)" + END_CSNAME_PATTERN.pattern
)

# COMPARISON_OP_PATTERN = re.compile(r"\s*=\s*%s" % command_or_dim)


class CommandEntry(TypedDict):
    pattern: Pattern[str]
    handler: Callable[[re.Match[str], str, Optional[bool]], Tuple[str, int]]
    definition: Optional[str]
    math_mode_only: Optional[bool] = False


def default_ignore_handler(
    match: re.Match[str], text: str, math_mode: bool = False
) -> Tuple[str, int]:
    # return empty str to ignore?
    return "", match.end()


ENDS_WITH_SPACE_N_WORD_PATTERN = re.compile(r".+(\s+\w+)$")


def should_wrap_math_mode_arg(
    expanded_output: str,
    full_text: str,
    expanded_start_pos: int,  # position of the expanded output in the full text
    expanded_end_pos: int,  # end position of the expanded output in the full text
) -> bool:
    c: str = expanded_output.strip()
    start_pos = expanded_start_pos
    end_pos = expanded_end_pos
    should_wrap = False
    if len(c) >= 1:
        # print(start_pos, end_pos)
        # print(c)
        # print(full_text)
        is_last = end_pos >= len(full_text)
        next_pos_is_alnum = not is_last and full_text[end_pos].isalnum()
        if start_pos > 0 and c[0].isalnum() and full_text[start_pos - 1].isalnum():
            # if expanded first char and previous char in full_text are both alnum
            should_wrap = True
        elif c[-1].isalnum() and next_pos_is_alnum:
            # if expanded last char and next char in full_text are both alnum
            should_wrap = True
        elif c.startswith("\\"):
            is_single_command = c[1:].isalpha()
            if not is_single_command and start_pos > 0:
                # Handle both subscript and superscript
                prev_char = full_text[start_pos - 1]
                should_wrap = prev_char in "_^"
                if not should_wrap:
                    # Check if expanded ends with space+word
                    # this is to ensure stuff like \newcommand{\calR}{\mathcal R}, \calR 2 -> {\mathcal R} 2
                    match = ENDS_WITH_SPACE_N_WORD_PATTERN.match(c)
                    if match:
                        should_wrap = True

    return should_wrap


def wrap_math_mode_arg(text: str) -> str:
    # Strip whitespace first to properly check braces
    text = text.strip()
    # Only add braces if they're not already present
    if not (text.startswith("{") and text.endswith("}")):
        return "{" + text + "}"
    return text


class CommandProcessor:
    def __init__(self):
        # Replace the unicode conversion initialization with LatexUnicodeConverter
        self.unicode_converter = LatexUnicodeConverter()
        self.if_else_handler = IfElseBlockHandler()

        self.commands: Dict[str, CommandEntry] = {}
        self.let_commands: Dict[str, CommandEntry] = {}

    def clear(self):
        self.commands = {}
        self.let_commands = {}

    @property
    def _all_commands(self):
        return {**self.commands, **self.let_commands}

    def get_commands(self):
        return self._all_commands

    def has_command(self, command_name: str) -> bool:
        return command_name in self._all_commands

    def get_command_iter(self, math_mode=False):
        """
        Returns an iterator over commands, filtered by math_mode if specified.

        Args:
            math_mode (bool): If True, include all commands. If False, exclude math_mode_only commands.

        Returns:
            Iterator of CommandEntry objects
        """
        commands = self._all_commands
        if math_mode:
            yield from commands.values()
        else:
            for cmd in commands.values():
                if not cmd.get("math_mode_only", False):
                    yield cmd

    def process_let(self, command_name: str, definition: str, usage_pattern: str):
        # for let, we evaluate the definition right way
        definition = self.expand_commands(definition, True)[0]

        def handler(
            match: re.Match[str], text: str, math_mode: bool = False
        ) -> Tuple[str, int]:
            return definition, match.end()

        try:
            command: CommandEntry = {
                "pattern": re.compile(usage_pattern, re.DOTALL),
                "handler": handler,
                "definition": definition,
            }
            self.let_commands[command_name] = command
        except Exception as e:
            print(f"Error processing newcommand {command_name}: {e}")
            raise e

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
        math_mode_only=False,
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
                definition = get_definition(match)
                # if math_mode_only and not math_mode:
                #     return "\\" + command_name, match.end()

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

                # fill remaining args with empty strings
                args.extend([""] * (num_args - len(args)))

                return substitute_args(definition, args, math_mode), end_pos

        try:
            command: CommandEntry = {
                "pattern": re.compile(usage_pattern, re.DOTALL),
                "handler": handler,
                "definition": definition,
                "math_mode_only": math_mode_only,
            }
            self.commands[command_name] = command
        except Exception as e:
            print(f"Error processing newcommand {command_name}: {e}")
            raise e

    def process_paired_delimiter(
        self, command_name: str, left_delim: str, right_delim: str
    ):
        r"""Process a paired delimiter command like \br{content}"""
        usage_pattern = r"\\" + command_name + r"\*?\s*{"

        def handler(
            match: re.Match[str], text: str, math_mode: bool = False
        ) -> Tuple[str, int]:
            start_pos = match.end() - 1
            content, end_pos = extract_nested_content(text[start_pos:], "{", "}")
            if content is None:
                return "", start_pos

            out = f"{left_delim}{content}{right_delim}"
            if math_mode and should_wrap_math_mode_arg(
                content, out, len(left_delim), len(left_delim) + len(content)
            ):
                out = left_delim + wrap_math_mode_arg(content) + right_delim

            end_pos += start_pos
            return out, end_pos

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
                    args.append(g)
                    # args.append(wrap_math_mode_arg(g) if math_mode else g)

            return substitute_args(get_definition(match), args, math_mode), match.end()

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
        command_entries = self.commands
        if not math_mode:
            command_entries = {
                k: v
                for k, v in self.commands.items()
                if not v.get("math_mode_only", False)
            }
        # first process commands
        text, match_count = self._expand(text, command_entries, math_mode=math_mode)
        # then process let commands
        text, match_count = self._expand(text, self.let_commands, math_mode=math_mode)

        # Handle unicode conversions using the converter
        if not ignore_unicode:
            text = self.unicode_converter.convert(text)

        return text, match_count

    def _expand(
        self,
        text: str,
        command_entries: Dict[str, CommandEntry],
        math_mode: bool = False,
        max_depth: int = 1000,
    ) -> tuple[str, int]:
        """Recursively expand defined commands in the text until no further expansions are possible."""
        match_count = 0
        depth = 0

        def sub_fn(text, match, cmd_name):
            nonlocal match_count
            match_count += 1
            if cmd_name not in command_entries:
                return match.group(0), match.end()
            handler = command_entries[cmd_name]["handler"]
            out, pos = handler(match, text, math_mode=math_mode)
            # if math mode and out contains a space, wrap the out in braces for grouping
            # Example: a b c  -> {a b c}, perhaps later \frac{a b c}, and NOT \frac a b c
            # if no space and/or starts with \\, we assume the output is a single command that may be affected if wrapped in braces
            # e.g. \tilde -> \tilde{...}, and NOT {\tilde}{...}
            if math_mode:
                should_wrap = should_wrap_math_mode_arg(out, text, match.start(), pos)

                if should_wrap:
                    out = wrap_math_mode_arg(out)
            return out, pos

        command2pattern = {
            name: cmd["pattern"] for name, cmd in command_entries.items()
        }

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
        for cmd in self.get_command_iter(False):
            if cmd["pattern"].match(text):
                return True
        return CSNAME_PATTERN.match(text) is not None

    def _handle_csname(self, text: str) -> tuple[str, int]:
        match = CSNAME_PATTERN.match(text)
        if match:
            nested, end_pos = extract_and_concat_nested_csname(text)
            if nested:
                for cmd in self.get_command_iter(False):
                    match = cmd["pattern"].match(text)
                    if match:
                        out, _ = cmd["handler"](match, text)
                        return out, end_pos
                return "", end_pos
        return text, 0

    def _handle(self, text: str) -> str:
        for cmd in self.get_command_iter(False):
            match = cmd["pattern"].match(text)
            if match:
                out, end_pos = cmd["handler"](match, text)
                if match.group(0) == out:  # prevent infinite loop
                    return "", match.end()
                return out, end_pos

        return self._handle_csname(text)

    def handle(self, text: str) -> str:
        out, end_pos = self._handle(text)
        # (this was originally added to handle some setting of macros with \cmd = x, but commented out -> TOO aggressive, will interfere with math data)
        # if end_pos > 0:
        #     # check if next token is =<>
        #     comp_op_match = COMPARISON_OP_PATTERN.match(text[end_pos:])
        #     if comp_op_match:
        #         return "", end_pos + comp_op_match.end()
        return out, end_pos


if __name__ == "__main__":
    from latex2json.parser.handlers.new_definition import NewDefinitionHandler

    handler = NewDefinitionHandler()

    content = r"\newcommand{\ti}{\tilde}"
    token, pos = handler.handle(content)

    processor = CommandProcessor()
    processor.process_newcommand(
        token["name"],
        token["content"],
        token["num_args"],
        token["defaults"],
        token["usage_pattern"],
    )

    out, pos = processor.expand_commands(r"\ti{3}", math_mode=True)
    print(out, pos)
