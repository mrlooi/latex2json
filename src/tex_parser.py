import re
from typing import List, Dict, Tuple, Union

import sys, os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.handlers import (
    CodeBlockHandler,
    EquationHandler,
    TokenHandler,
    ContentCommandHandler,
    NewDefinitionHandler,
    TabularHandler,
    FormattingHandler,
    ItemHandler,
    EnvironmentHandler,
    LegacyFormattingHandler,
    BibItemHandler,
    AuthorHandler,
    TextFormattingHandler,
)
from src.handlers.environment import BaseEnvironmentHandler
from src.patterns import PATTERNS
from src.commands import CommandProcessor
from src.tex_utils import extract_nested_content

# Add these compiled patterns at module level
# match $ or % or { or } only if not preceded by \
# Update DELIM_PATTERN to also match double backslashes and opening braces {
DELIM_PATTERN = re.compile(
    r"(?<!\\)(?:\\\\|\$|%|(?:^|[ \t])\{|\s{|\\\^|\\(?![$%&_#{}^~\\]))"
)
ESCAPED_AMPERSAND_SPLIT = re.compile(r"(?<!\\)&")
TRAILING_BACKSLASH = re.compile(r"\\+$")
UNKNOWN_COMMAND_PATTERN = re.compile(r"(\\[@a-zA-Z*]+\s*\{?)", re.DOTALL)


class LatexParser:
    def __init__(self):
        self.labels = {}

        self.current_env = (
            None  # Current environment token (used for associating nested labels)
        )
        self.current_str = ""

        # Regex patterns for different LaTeX elements
        self.command_processor = CommandProcessor()
        self.env_handler = EnvironmentHandler()

        self.legacy_formatting_handler = LegacyFormattingHandler()

        # handlers
        self.handlers: List[TokenHandler] = [
            AuthorHandler(),
            # ignore unicode conversion for equations
            EquationHandler(lambda x: self._expand_command(x, ignore_unicode=True)),
            CodeBlockHandler(),
            ItemHandler(),
            BibItemHandler(),
            ContentCommandHandler(self._expand_command),
            # for tabular, on the first pass we process content and maintain the '\\' delimiter to maintain row integrity
            TabularHandler(
                process_content_fn=lambda x: self.parse(
                    x, r"\\", handle_unknown_commands=False
                ),
                cell_parser_fn=self.parse,
            ),
            # make sure to add EnvironmentHandler after equation/tabular or other env related formats, since it will greedily parse any begin/end block. Add as last to be safe
            self.env_handler,
            # add formatting stuffs last
            TextFormattingHandler(),
            FormattingHandler(),
            # self.legacy_formatting_handler,
        ]
        self.new_definition_handler = NewDefinitionHandler()

    # getter for commands
    @property
    def commands(self):
        return self.command_processor.commands

    @property
    def environments(self):
        return self.env_handler.environments

    def clear(self):
        self.labels = {}
        self.current_str = ""
        self.current_env = None
        self.command_processor.clear()
        # handlers
        for handler in self.handlers:
            handler.clear()
        self.new_definition_handler.clear()

    def _expand_command(self, content: str, ignore_unicode: bool = False) -> str:
        """Expand LaTeX commands in the content"""
        out, match_count = self.command_processor.expand_commands(
            content, ignore_unicode
        )
        return out

    def _handle_label(self, content: str, tokens: List[Dict[str, str]]) -> None:
        """Handle labels by associating them with the current environment or adding them as a separate token"""
        if self.current_env:
            # Associate label with current environment
            if "labels" not in self.current_env:
                self.current_env["labels"] = []
            self.current_env["labels"].append(content)
            self.labels[content] = self.current_env
        else:
            # No current environment, associate with previous token if exists
            if tokens and tokens[-1]:
                if "labels" not in tokens[-1]:
                    tokens[-1]["labels"] = []
                tokens[-1]["labels"].append(content)
                self.labels[content] = tokens[-1]
            else:
                tokens.append({"type": "label", "content": content})

    def _parse_cell(self, cell_content: str) -> List[Dict]:
        cell = self.parse(cell_content)
        return self._clean_cell(cell)

    def _clean_cell(self, cell: List[Dict]) -> List[Dict]:
        if len(cell) == 0:
            return None
        elif len(cell) == 1:
            if cell[0]["type"] == "text":
                return cell[0]["content"]
            return cell[0]
        return cell

    def add_token(self, token: str | Dict, tokens: List[Dict]):
        # uncomment this if we want to merge self.current_str whitespaces
        # if self.current_str:
        #     if tokens and tokens[-1].get('type') == 'text':
        #         tokens[-1]['content'] += self.current_str
        #     else:
        #         tokens.append({
        #             "type": "text",
        #             "content": self.current_str
        #         })

        self.current_str = ""

        if token:
            # Convert string token to dict format
            token_dict = token
            if isinstance(token, str):
                token_dict = {"type": "text", "content": token}

            # Merge consecutive text tokens
            if (
                token_dict.get("type") == "text"
                and tokens
                and tokens[-1].get("type") == "text"
                and "styles" not in token_dict
                and "styles" not in tokens[-1]
            ):
                tokens[-1]["content"] += token_dict["content"]
            else:
                tokens.append(token_dict)

    def _check_unknown_command(
        self, content: str, tokens: List[Dict]
    ) -> Tuple[bool, int]:
        """Convert unknown LaTeX command into a text token with original syntax"""
        # Get the full matched text to preserve all arguments
        match = UNKNOWN_COMMAND_PATTERN.match(content)
        if match:
            command = match.group(0).strip()
            end_pos = match.end()

            inner_content = None
            if command.endswith("{"):
                command = command[:-1]
                inner_content, inner_end_pos = extract_nested_content(
                    content[end_pos - 1 :]
                )
                end_pos += inner_end_pos - 1
                inner_content = self.parse(inner_content)

            token = {"type": "command", "command": command}
            if inner_content:
                token["content"] = inner_content

            self.add_token(token, tokens)
            return True, end_pos

        return False, 0

    def _check_for_new_definitions(self, content: str) -> None:
        """Check for new definitions in the content and process them"""
        if self.new_definition_handler.can_handle(content):
            token, end_pos = self.new_definition_handler.handle(content)
            if token:
                if token["type"] == "newcommand":
                    cmd_name = token["name"]
                    self.command_processor.process_newcommand(
                        cmd_name, token["content"], token["num_args"], token["defaults"]
                    )
                elif token["type"] == "def":
                    self.command_processor.process_newdef(
                        token["name"],
                        token["content"],
                        token["num_args"],
                        token["usage_pattern"],
                    )
                # elif token['type'] == 'newtheorem':
                #     pass

            return end_pos
        return 0

    def _check_handlers(self, content: str, tokens: List[Dict]) -> Tuple[bool, int]:
        """Process content through available handlers.

        Returns:
            Tuple[bool, int]: (whether content was matched, new position)
        """
        for handler in self.handlers:
            if handler.can_handle(content):
                token, end_pos = handler.handle(content)
                if token:
                    if isinstance(token, str):
                        token = {"type": "text", "content": token}
                    elif token["type"] in ["footnote", "caption"]:
                        prev_env = self.current_env
                        self.current_env = token
                        token["content"] = self._parse_cell(token["content"])
                        self.current_env = prev_env
                    elif token["type"] == "url":
                        if "title" in token:
                            token["title"] = self._parse_cell(token["title"])
                    elif token["type"] == "section":
                        self.current_env = token
                    elif isinstance(handler, BaseEnvironmentHandler):
                        prev_env = self.current_env
                        self.current_env = token
                        token["content"] = self.parse(token["content"])
                        self.current_env = prev_env
                    elif isinstance(handler, TextFormattingHandler):
                        # Parse inner first
                        inner_content = self.parse(token["content"])
                        # Maintain token metadata
                        styled_token = {
                            **token,
                            "content": inner_content,
                        }
                        processed_tokens = (
                            TextFormattingHandler.process_style_in_tokens(
                                [styled_token]
                            )
                        )
                        tokens.extend(processed_tokens)

                        return True, end_pos

                    self.add_token(token, tokens)
                return True, end_pos
        return False, 0

    def _check_remaining_patterns(
        self, content: str, tokens: List[Dict], line_break_delimiter: str = "\n"
    ) -> Tuple[bool, int]:
        # Try each pattern
        for pattern_type, pattern in PATTERNS.items():
            match = re.match(pattern, content)
            if match:
                matched_type = pattern_type
                break

        if match:
            if matched_type == "label":
                start_pos = match.end() - 1  # -1 to account for the label command '{'
                label, end_pos = extract_nested_content(content[start_pos:])
                if label:
                    self._handle_label(label, tokens)
                return True, start_pos + end_pos
            elif matched_type == "newline" or matched_type == "break_spacing":
                self.add_token(line_break_delimiter, tokens)
            else:
                # For all other token types, expand any commands in their content
                x = match.group(1) if match.groups() else match.group(0)
                x = self._expand_command(x)
                self.add_token({"type": matched_type, "content": x})

            return True, match.end()

        return False, 0

    def parse(
        self,
        content: str,
        line_break_delimiter: str = "\n",
        handle_unknown_commands: bool = True,
        # nesting_level: int = 0,
    ) -> List[Dict[str, str]]:
        tokens = []
        current_pos = 0

        while current_pos < len(content):
            # Skip whitespace
            while current_pos < len(content) and content[current_pos].isspace():
                self.current_str += content[current_pos]
                current_pos += 1
            if current_pos >= len(content):
                break

            # Add handling for bare braces at the start i.e. latex grouping {content here}
            if content[current_pos] == "{":
                # Find matching closing brace
                inner_content, end_pos = extract_nested_content(content[current_pos:])
                if inner_content is not None:
                    # Parse the content within the braces
                    nested_tokens = self.parse(
                        inner_content  # , nesting_level=nesting_level + 1
                    )
                    if nested_tokens:
                        # could use append here but we want to keep flatten it out since {} are used just for basic grouping and don't preserve meaningful structure
                        tokens.extend(nested_tokens)
                    current_pos += end_pos
                    continue

            # find the next delimiter (this block allows us to quickly identify and process chunks of text between special LaTeX delimiters
            # without it, we would have to parse the entire content string character by character. which would be slower.)
            # if next delimiter exists, we need to store the text before the next delimiter (or all remaining text if no delimiter)
            next_delimiter = DELIM_PATTERN.search(content[current_pos:])
            next_pos = (
                len(content[current_pos:])
                if not next_delimiter
                else next_delimiter.start()
            )
            if next_pos > 0:
                # convert text before next delimiter to tokens
                text = content[current_pos : current_pos + next_pos]  # .strip()
                if text:
                    self.add_token(text, tokens)
                current_pos += next_pos
                if not next_delimiter:
                    break
                continue

            # check for new definition commands
            end_pos = self._check_for_new_definitions(content[current_pos:])
            if end_pos > 0:
                current_pos += end_pos
                continue

            # check for user defined commands
            if self.command_processor.can_handle(content[current_pos:]):
                text, end_pos = self.command_processor.handle(content[current_pos:])
                if end_pos > 0:
                    # replace the matched user command with the expanded text
                    content = (
                        content[:current_pos] + text + content[current_pos + end_pos :]
                    )
                    continue

            # check if legacy formatting
            if self.legacy_formatting_handler.can_handle(content[current_pos:]):
                parsed_text, end_pos = self.legacy_formatting_handler.handle(
                    content[current_pos:]
                )
                if end_pos > 0:
                    content = (
                        content[:current_pos]
                        + parsed_text
                        + content[current_pos + end_pos :]
                    )
                    continue

            # try each handler
            matched, end_pos = self._check_handlers(content[current_pos:], tokens)
            current_pos += end_pos
            if matched:
                continue

            # check remaining patterns
            matched, end_pos = self._check_remaining_patterns(
                content[current_pos:], tokens, line_break_delimiter
            )
            current_pos += end_pos
            if matched:
                continue

            # check for unknown command
            if handle_unknown_commands:
                matched, end_pos = self._check_unknown_command(
                    content[current_pos:], tokens
                )
                current_pos += end_pos
                if matched:
                    continue

            self.add_token(content[current_pos], tokens)
            current_pos += 1

        return tokens


if __name__ == "__main__":

    text = r"""
    
    \def\foo{bar}

    \begin{tabular}{|c|c|}
        \hline
        {
            \normalsize sss
            \bf{Hii} bro 
            \foo
        } & 2nd block \\
        \noindent & \begin{equation} x=1 & wer \end{equation} \\
        \hline
    \end{tabular}
    """

    # Example usage
    parser = LatexParser()
    parsed_tokens = parser.parse(text)
    print(parsed_tokens)

# commands = [
#     r"\foo \ss",  # capture \foo and \ss
#     r"\b@ar  ",  # capture \b@ar
#     r"\ef{s\dsd\textbf{ss}}",  # capture \ef{
#     "sdsds",  # no match
#     r"\begin{\textbf{xxsss{ssd{sds}}}}\n",  # capture \begin{
#     r"\foo {ss}",
#     r"   \textbf{sdsds}",
# ]

# for command in commands:
#     print(command, UNKNOWN_COMMAND_PATTERN.match(command))
