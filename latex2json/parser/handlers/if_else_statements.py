from collections import OrderedDict
import logging
from typing import Dict, List, Optional, Tuple
import re

from latex2json.parser.handlers.base import TokenHandler
from latex2json.parser.handlers.new_definition import extract_and_concat_nested_csname
from latex2json.utils.tex_utils import extract_nested_content_sequence_blocks
from latex2json.parser.patterns import command_with_opt_brace_pattern, command_or_dim

# Could be character, command, or more complex token
char_or_command_pattern = r"(?:{\s*)?(?:\\[a-zA-Z@]+|\S)(?:\s*})?"

default_if_pattern = r"\s*(%s\s*%s|.+?)(?=\\|\s|$|\n)" % (
    char_or_command_pattern,
    char_or_command_pattern,
)

# Pattern to match any TeX token (command, character, or group)
tex_token_pattern = r"""
    (?:
        \\[a-zA-Z@]+     # Command token
        |
        \{[^}]*\}        # Group token
        |
        [^\\{}]          # Single character token
    )
"""

# Pattern for \ifx with two tokens to compare
ifx_pattern = re.compile(
    r"\\ifx\s*"
    + rf"({tex_token_pattern})\s*"  # First token
    + rf"({tex_token_pattern})",  # Second token
    re.VERBOSE,
)


IF_PATTERN = re.compile(r"\\(?:@)?if%s" % (default_if_pattern))
ELSE_PATTERN = re.compile(r"\\else\b")
ELSIF_PATTERN = re.compile(
    r"\\els(?:e)?if%s|\\or%s\b" % (default_if_pattern, default_if_pattern)
)  # Matches both \elsif and \elseif
FI_PATTERN = re.compile(r"\\fi\b")

value_pattern = r"\\value\s*{\s*([a-zA-Z@]+)\s*}"
numbered_command_pattern = r"\\([a-zA-Z@]+)(\d+)"

counter_or_num = rf"(?:{value_pattern}|{numbered_command_pattern}|{command_with_opt_brace_pattern}|\d+)"

# Allow either order around operator
ifnum_pattern = rf"\\ifnum\s*{counter_or_num}\s*([=<>])\s*{counter_or_num}"

ifdim_pattern = rf"\\ifdim\s*{command_or_dim}\s*([=<>])\s*{command_or_dim}"

# \ifcat takes two items to compare
ifcat_pattern = rf"\\ifcat\s*{char_or_command_pattern}\s*{char_or_command_pattern}"

EQUAL_PATTERN = re.compile(r"\\equal\s*\{")

# ordered dict so that ifthenelse/ifnum etc is matched before general if
IF_PATTERNS_DEFAULT_LIST = OrderedDict(
    {
        "ifthenelse": re.compile(r"\\ifthenelse\s*\{"),
        "ifx": ifx_pattern,
        "ifdefined": re.compile(
            r"\\if(?:un)?defined\s*%s" % (command_with_opt_brace_pattern)
        ),
        "ifnum": re.compile(ifnum_pattern),
        "ifdim": re.compile(ifdim_pattern),
        "ifcat": re.compile(ifcat_pattern),
        "ifcase": re.compile(r"\\ifcase" + default_if_pattern),
        "iffileexists": re.compile(r"\\IfFileExists\s*\{"),
        "@ifclassloaded": re.compile(r"\\@ifclassloaded\s*\{"),
        "@ifpackageloaded": re.compile(r"\\@ifpackageloaded\s*\{"),
        "@ifundefined": re.compile(r"\\@ifundefined\s*\{"),
        "@ifstar": re.compile(r"\\@ifstar\s*\{"),
        "if": IF_PATTERN,
    }
)


def extract_else_elseif_fi(
    content: str,
    start_delimiter: re.Pattern = IF_PATTERN,
    end_delimiter: re.Pattern = FI_PATTERN,
    else_delimiter: re.Pattern = ELSE_PATTERN,
    elsif_delimiter: re.Pattern = ELSIF_PATTERN,
) -> Tuple[str, str, list, int]:
    nesting_level = 1
    pos = 0
    content_length = len(content)
    if_content = []
    else_content = []
    elsif_branches = []
    current_buffer = if_content

    while pos < content_length and nesting_level > 0:
        # Find all possible next matches
        start_match = start_delimiter.search(content[pos:])
        end_match = end_delimiter.search(content[pos:])
        else_match = else_delimiter.search(content[pos:])
        elsif_match = elsif_delimiter.search(content[pos:])

        valid_matches = []
        if start_match:
            valid_matches.append((start_match.start(), start_match, "start"))
        if end_match:
            valid_matches.append((end_match.start(), end_match, "end"))
        if else_match and nesting_level == 1:  # Only consider else at top level
            valid_matches.append((else_match.start(), else_match, "else"))
        if elsif_match and nesting_level == 1:
            valid_matches.append((elsif_match.start(), elsif_match, "elsif"))

        if not valid_matches:
            raise ValueError("Unclosed conditional block")

        next_pos, next_match, match_type = min(valid_matches, key=lambda x: x[0])

        # Add content up to (but not including) the match for top-level else/elsif/fi
        if nesting_level == 1 and (match_type in ["else", "elsif", "end"]):
            current_buffer.append(content[pos : pos + next_match.start()])
        else:
            # For nested structures, include the full match
            current_buffer.append(content[pos : pos + next_match.end()])

        if match_type == "start":
            nesting_level += 1
        elif match_type == "end":
            nesting_level -= 1
        elif match_type == "else" and nesting_level == 1:
            if elsif_branches:
                condition = elsif_branches[-1][0]
                elsif_branches[-1] = (condition, "".join(current_buffer).strip())
            current_buffer = else_content
        elif match_type == "elsif" and nesting_level == 1:
            # First save the content we've collected so far
            current_content = "".join(current_buffer).strip()
            if current_buffer == if_content:
                if_content = [current_content]
            else:
                # Add the previous elsif branch
                condition = elsif_branches[-1][0]
                elsif_branches[-1] = (condition, current_content)

            # Start new buffer for the next elsif branch
            current_buffer = (
                []
            )  # Create new empty buffer for collecting the next branch
            elsif_condition = next_match.group(1)
            elsif_branches.append((elsif_condition, ""))
            current_buffer = []  # Reset buffer to collect the elsif content

        pos += next_match.end()

    return (
        "".join(if_content).strip(),
        "".join(else_content).strip(),
        elsif_branches,
        pos,
    )


def try_handle_ifthenelse(
    content: str, match: Optional[re.Match] = None
) -> Tuple[Optional[Dict], int]:
    if match is None:
        match = IF_PATTERNS_DEFAULT_LIST["ifthenelse"].match(content)
    if match:
        start_pos = match.end() - 1  # -1 to exclude the opening brace
        blocks, end_pos = extract_nested_content_sequence_blocks(
            content[start_pos:], "{", "}", max_blocks=3
        )
        if len(blocks) != 3:
            raise ValueError("Invalid \\ifthenelse structure")
        return {
            "type": "conditional-ifthenelse",
            "condition": blocks[0],
            "if_content": blocks[1],
            "else_content": blocks[2],
        }, start_pos + end_pos
    return None, 0


class IfElseBlockHandler(TokenHandler):
    def __init__(self, logger=None, **kwargs):
        super().__init__(**kwargs)
        self.logger = logger or logging.getLogger(__name__)
        self.all_ifs: List[Tuple[str, re.Pattern]] = []
        self.all_ifs_compiled: re.Pattern | None = None
        self._reset()

    def clear(self):
        self._reset()

    def _reset(self):
        self.all_ifs = [
            (name, pattern) for name, pattern in IF_PATTERNS_DEFAULT_LIST.items()
        ]
        self._recompile_all_ifs()

    def process_newif(self, var_name: str):
        pattern = re.compile(r"\\if" + var_name + r"(?:true|false)?")
        # push to top of stack i.e. priority
        self.all_ifs.insert(0, (var_name, pattern))
        self._recompile_all_ifs()

    def has_if(self, var_name: str) -> bool:
        return any(name == var_name for name, _ in self.all_ifs)

    def _recompile_all_ifs(self):
        if len(self.all_ifs) == 0:
            self.all_ifs_compiled = None
            return
        pattern = ""
        for k, v in self.all_ifs:
            pattern += "|" + v.pattern
        if pattern.startswith("|"):
            pattern = pattern[1:]
        self.all_ifs_compiled = re.compile(pattern)

    def can_handle(self, content: str) -> bool:
        return any(pattern.match(content) for _, pattern in self.all_ifs)

    def _handle_atif(
        self, content: str, match: re.Match, name: str
    ) -> Tuple[Optional[Dict], int]:
        start_pos = match.end() - 1
        blocks, end_pos = extract_nested_content_sequence_blocks(
            content[start_pos:], "{", "}", max_blocks=3
        )
        if len(blocks) == 0:
            return None, 0
        if_content = blocks[1] if len(blocks) > 1 else ""
        else_content = blocks[2] if len(blocks) > 2 else ""
        return {
            "type": "conditional-" + name,
            "condition": blocks[0],
            "if_content": if_content,
            "else_content": else_content,
        }, start_pos + end_pos

    def _handle_ifstar(
        self, content: str, match: re.Match
    ) -> Tuple[Optional[Dict], int]:
        start_pos = match.end() - 1
        blocks, end_pos = extract_nested_content_sequence_blocks(
            content[start_pos:], "{", "}", max_blocks=2
        )
        if len(blocks) == 0:
            return None, 0
        if_content = blocks[0] if len(blocks) > 0 else ""
        else_content = blocks[1] if len(blocks) > 1 else ""
        return {
            "type": "conditional-ifstar",
            "condition": "@ifstar",
            "if_content": if_content,
            "else_content": else_content,
        }, start_pos + end_pos

    def _handle_iffileexists(
        self, content: str, match: re.Match
    ) -> Tuple[Optional[Dict], int]:
        start_pos = match.end() - 1
        blocks, end_pos = extract_nested_content_sequence_blocks(
            content[start_pos:], "{", "}", max_blocks=3
        )
        condition = blocks[0] if len(blocks) > 0 else ""
        if_true = blocks[1] if len(blocks) > 1 else ""
        if_false = blocks[2] if len(blocks) > 2 else ""
        return {
            "type": "conditional-iffileexists",
            "condition": condition,
            "if_content": if_true,
            "else_content": if_false,
        }, start_pos + end_pos

    def handle(
        self, content: str, prev_token: Optional[Dict] = None
    ) -> Tuple[Optional[Dict], int]:
        for name, pattern in self.all_ifs:
            match = pattern.match(content)
            if match:
                if name == "ifthenelse":
                    token, end_pos = try_handle_ifthenelse(content, match)
                    return token, end_pos
                elif name in [
                    "@ifclassloaded",
                    "@ifpackageloaded",
                    "@ifundefined",
                ]:
                    return self._handle_atif(content, match, name)
                elif name == "@ifstar":
                    return self._handle_ifstar(content, match)
                # elif name == "equal":
                #     start_pos = match.end() - 1
                #     blocks, end_pos = extract_nested_content_sequence_blocks(
                #         content[start_pos:], max_blocks=1
                #     )
                #     if len(blocks) == 0:
                #         return None, 0
                #     # ignore equal anyway
                #     return None, start_pos + end_pos
                else:
                    out_str = match.group(0)
                    start_pos = match.start()
                    cs_name_ind = out_str.find("\\csname")
                    condition = out_str.replace(" ", "")
                    if cs_name_ind != -1:
                        inner, pos = extract_and_concat_nested_csname(
                            content[start_pos + cs_name_ind :]
                        )
                        if inner:
                            start_pos += cs_name_ind + pos
                            condition = inner.strip()
                    else:
                        start_pos = match.end()
                        if condition == "\\if" + name or condition == "\\@if" + name:
                            condition = name
                        else:
                            condition = condition.replace("\\" + name, "")
                            if name == "ifdefined" and "\\ifundefined" in condition:
                                condition = condition.replace("\\ifundefined", "")
                    try:
                        if_content, else_content, elsif_branches, end_pos = (
                            extract_else_elseif_fi(
                                content[start_pos:],
                                start_delimiter=self.all_ifs_compiled or IF_PATTERN,
                            )
                        )
                        # Swap if_content and else_content for \iffalse
                        if condition.replace("{", "").replace("}", "") == "false":
                            if_content, else_content = else_content, if_content

                    except ValueError as e:
                        self.logger.warning(
                            ValueError(f"Unclosed conditional block: {e}")
                        )
                        return None, 0
                    return {
                        "type": "conditional-" + name,
                        "condition": condition,
                        "if_content": if_content,
                        "else_content": else_content,
                        "elsif_branches": elsif_branches,
                    }, start_pos + end_pos

        return None, 0


if __name__ == "__main__":
    text = r"""
    \ifx\csname urlstyle\endcsname\relax\fi
""".strip()

    handler = IfElseBlockHandler()
    print(handler.handle(text))
