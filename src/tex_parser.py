from collections import OrderedDict
import re
from typing import List, Dict, Tuple, Union
import sys, os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


import logging

logging.basicConfig(
    level=logging.WARNING,
    format="%(levelname)s: %(message)s",
    force=True,  # This ensures the config is applied even if another module has configured logging
)

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
    IfElseBlockHandler,
    DiacriticsHandler,
    ForLoopHandler,
)
from src.handlers.environment import BaseEnvironmentHandler
from src.patterns import PATTERNS
from src.commands import CommandProcessor
from src.tex_utils import extract_nested_content, read_tex_file_content

# Add these compiled patterns at module level
# match $ or % or { or } only if not preceded by \
# Update DELIM_PATTERN to also match double backslashes and opening braces {
DELIM_PATTERN = re.compile(
    r"(?<!\\)(?:\\\\|\$|%|(?:^|[ \t])\{|\s{|\\\^|\\(?![$%&_#{}^~\\]))"
)
ESCAPED_AMPERSAND_SPLIT = re.compile(r"(?<!\\)&")
TRAILING_BACKSLASH = re.compile(r"\\+$")
UNKNOWN_COMMAND_PATTERN = re.compile(r"(\\[@a-zA-Z\*]+(?:\s*{)?)")


class LatexParser:
    def __init__(self, logger: logging.Logger = None):
        # for logging
        self.logger = logger or logging.getLogger(__name__)
        self._unknown_commands = {}

        # state vars
        self.labels = {}
        self.current_env = (
            None  # Current environment token (used for associating nested labels)
        )
        self.current_file_dir = None
        self.current_str = ""

        # Regex patterns for different LaTeX elements
        self.command_processor = CommandProcessor()
        self.env_handler = EnvironmentHandler()

        self.legacy_formatting_handler = LegacyFormattingHandler()
        self.if_else_block_handler = IfElseBlockHandler()
        # handlers
        self.handlers: List[TokenHandler] = [
            AuthorHandler(self.parse),
            # ignore unicode conversion for equations
            EquationHandler(lambda x: self._expand_command(x, ignore_unicode=True)),
            CodeBlockHandler(),
            ItemHandler(),
            BibItemHandler(self.parse),
            ContentCommandHandler(self._expand_command),
            # for tabular, on the first pass we process content and maintain the '\\' delimiter to maintain row integrity
            TabularHandler(
                process_content_fn=lambda x: self.parse(
                    x,
                    r"\\",
                    handle_unknown_commands=False,
                    handle_legacy_formatting=False,
                ),
                cell_parser_fn=self.parse,
            ),
            # make sure to add EnvironmentHandler after equation/tabular or other env related formats, since it will greedily parse any begin/end block. Add as last to be safe
            self.env_handler,
            ForLoopHandler(),
            # add formatting stuffs last
            TextFormattingHandler(self.parse),
            FormattingHandler(),
            DiacriticsHandler(),
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
        self._unknown_commands = {}
        self.current_str = ""
        self.current_file_dir = None
        self.current_env = None
        self.command_processor.clear()
        # handlers
        for handler in self.handlers:
            handler.clear()
        self.if_else_block_handler.clear()
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
            if isinstance(token_dict, list):
                tokens.extend(token_dict)
            elif (
                token_dict.get("type") == "text"
                and tokens
                and tokens[-1].get("type") == "text"
                and "styles" not in token_dict
                and "styles" not in tokens[-1]
            ):
                tokens[-1]["content"] += token_dict["content"]
            else:
                tokens.append(token_dict)

    def _check_unknown_command(self, content: str) -> Tuple[bool, int]:
        """Convert unknown LaTeX command into a text token with original syntax"""
        # Get the full matched text to preserve all arguments
        match = UNKNOWN_COMMAND_PATTERN.match(content)
        if match:
            command = match.group(0)
            end_pos = match.end()

            inner_content = None
            total_content = command
            if command.endswith("{"):
                command = command[:-1]
                inner_content, inner_end_pos = extract_nested_content(
                    content[end_pos - 1 :]
                )
                end_pos += inner_end_pos - 1
                total_content += inner_content + "}"

            expanded = self._expand_command(total_content)

            if expanded.startswith("\\"):
                token = {"type": "command", "command": command}
                if expanded.startswith(command):
                    expanded = expanded[len(command) :]
                # expanded = expanded.strip("{}")
                if expanded:
                    token["content"] = expanded
            else:
                token = {"type": "text", "content": expanded}

            return token, end_pos

        return None, 0

    def _check_for_new_definitions(self, content: str) -> None:
        """Check for new definitions in the content and process them"""
        if self.new_definition_handler.can_handle(content):
            token, end_pos = self.new_definition_handler.handle(content)
            if token and "name" in token:
                cmd_name = token["name"]
                if token["type"] == "newcommand":
                    self.command_processor.process_newcommand(
                        cmd_name,
                        token["content"],
                        token["num_args"],
                        token["defaults"],
                        token["usage_pattern"],
                    )
                elif token["type"] == "def":
                    self.command_processor.process_newdef(
                        cmd_name,
                        token["content"],
                        token["num_args"],
                        token["usage_pattern"],
                        token["is_edef"],
                    )
                elif token["type"] == "newif":
                    self.command_processor.process_newif(cmd_name)
                    self.if_else_block_handler.process_newif(cmd_name)
                elif token["type"] == "newlength":
                    self.command_processor.process_newlength(cmd_name)
                elif token["type"] == "newcounter":
                    self.command_processor.process_newcounter(cmd_name)
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
                prev_token = tokens[-1] if tokens else None
                token, end_pos = handler.handle(content, prev_token)
                if token:
                    if isinstance(token, str):
                        token = {"type": "text", "content": token}
                    elif token["type"] == "input":
                        # open input file
                        if token["content"]:
                            file_path = token["content"]
                            if self.current_file_dir:
                                file_path = os.path.join(
                                    self.current_file_dir, file_path
                                )
                            input_tokens = self.parse_file(file_path)
                            if input_tokens:
                                tokens.extend(input_tokens)
                        return True, end_pos
                    elif token["type"] in ["footnote", "caption"]:
                        prev_env = self.current_env
                        self.current_env = token
                        token["content"] = self.parse(token["content"])
                        self.current_env = prev_env
                    elif token["type"] == "url":
                        if "title" in token:
                            token["title"] = self.parse(token["title"])
                    elif token["type"] == "section":
                        self.current_env = token
                    elif isinstance(handler, BaseEnvironmentHandler):
                        # algorithmic keep as literal?
                        if token["type"] != "algorithmic":
                            prev_env = self.current_env
                            self.current_env = token
                            token["content"] = self.parse(token["content"])
                            self.current_env = prev_env

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
            elif matched_type == "line_continuation":
                return True, match.end()
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
        handle_legacy_formatting: bool = True,
        file_path: str = None,
    ) -> List[Dict[str, str]]:
        """
        Parse LaTeX content string into tokens.

        Args:
            content: The LaTeX content to parse
            line_break_delimiter: Character to use for line breaks
            handle_unknown_commands: Whether to process unknown commands
            handle_legacy_formatting: Whether to handle legacy formatting
            file_path: Optional path to the source file (used for resolving relative paths)

        Returns:
            List[Dict[str, str]]: List of parsed tokens
        """
        if file_path:
            self.current_file_dir = os.path.dirname(os.path.abspath(file_path))

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
                    nested_tokens = self.parse(inner_content)
                    if nested_tokens:
                        for token in nested_tokens:
                            self.add_token(token, tokens)
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
                text = content[current_pos : current_pos + next_pos]
                if text:
                    if handle_unknown_commands:
                        text = self._expand_command(text)
                    self.add_token(text, tokens)
                current_pos += next_pos
                if not next_delimiter:
                    break
                continue

            # check for user defined commands (important to check before new definitions in case of floating \csname)
            if self.command_processor.can_handle(content[current_pos:]):
                text, end_pos = self.command_processor.handle(content[current_pos:])
                if end_pos > 0:
                    # replace the matched user command with the expanded text
                    content = (
                        content[:current_pos] + text + content[current_pos + end_pos :]
                    )
                    continue

            # check for new definition commands
            end_pos = self._check_for_new_definitions(content[current_pos:])
            if end_pos > 0:
                current_pos += end_pos
                continue

            # check for if else blocks
            if self.if_else_block_handler.can_handle(content[current_pos:]):
                token, end_pos = self.if_else_block_handler.handle(
                    content[current_pos:]
                )
                if end_pos > 0:
                    block = token["if_content"]
                    content = (
                        content[:current_pos] + block + content[current_pos + end_pos :]
                    )
                    continue

            # check if legacy formatting
            if handle_legacy_formatting and self.legacy_formatting_handler.can_handle(
                content[current_pos:]
            ):
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
                token, end_pos = self._check_unknown_command(content[current_pos:])
                current_pos += end_pos
                if token:
                    self.add_token(token, tokens)
                    if token["type"] == "command":
                        cmd_name = token["command"]
                        if cmd_name not in self._unknown_commands:
                            self._unknown_commands[cmd_name] = token
                            self.logger.warning(
                                f"\n*****\nUnknown command: Token: {token}\n***Surrounding content***\n{content[max(0, current_pos-100):current_pos+100]}\n*****"
                            )
                        else:
                            self.logger.warning(
                                f"\n*****(Again) Unknown command token: {token}\n*****"
                            )
                    continue

            self.add_token(content[current_pos], tokens)
            current_pos += 1

        return tokens

    def parse_file(self, file_path: str) -> List[Dict[str, str]]:
        """
        Parse a LaTeX file directly from the file path.

        Args:
            file_path: Path to the LaTeX file to parse

        Returns:
            List[Dict[str, str]]: List of parsed tokens
        """
        try:
            self.logger.info(f"Parsing file: {file_path}")
            content = read_tex_file_content(file_path)
            return self.parse(content, file_path=file_path)
        except Exception as e:
            self.logger.error(f"Failed to parse file: {file_path}, error: {str(e)}")
            self.logger.error(
                "Stack trace:", exc_info=True
            )  # This will log the full stack trace

            return []


if __name__ == "__main__":

    # More detailed logging configuration for direct script execution
    logging.basicConfig(
        level=logging.DEBUG,  # More verbose when running directly
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        force=True,
        handlers=[
            logging.FileHandler(
                "logs/tex_parser.log"
            ),  # Output to a file named 'tex_parser.log'
            logging.StreamHandler(),  # Optional: also output to console
        ],
    )
    logging.getLogger("asyncio").setLevel(logging.WARNING)

    logger = logging.getLogger(__name__)

    parser = LatexParser(logger=logger)

    file = "papers/arXiv-1706.03762v7/ms.tex"
    parsed_tokens = parser.parse_file(file)

    #     # Example usage
    #     text = r"""
    # \begin{algorithm}[H]
    # \caption{Sum of Array Elements}
    # \label{alg:loop}
    # \begin{algorithmic}[1]
    # \Require{$A_{1} \dots A_{N}$}
    # \Ensure{$Sum$ (sum of values in the array)}
    # \Statex
    # \Function{Loop}{$A[\;]$}
    #   \State {$Sum$ $\gets$ {$0$}}
    #     \State {$N$ $\gets$ {$length(A)$}}
    #     \For{$k \gets 1$ to $N$}
    #         \State {$Sum$ $\gets$ {$Sum + A_{k}$}}
    #     \EndFor
    #     \State \Return {$Sum$}
    # \EndFunction
    # \end{algorithmic}
    # \end{algorithm}
    # """

    # parser = LatexParser(logger=logger)
    # parsed_tokens = parser.parse(text)
    # print(len(parsed_tokens))
    # print(parsed_tokens)
