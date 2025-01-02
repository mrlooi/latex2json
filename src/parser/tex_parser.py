from collections import OrderedDict
import re
from typing import List, Dict, Tuple, Union
import sys, os, traceback
import logging

from src.parser.bib_parser import BibEntry, BibParser
from src.utils.logger import setup_logger

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


from src.parser.handlers import (
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
    AuthorHandler,
    TextFormattingHandler,
    IfElseBlockHandler,
    DiacriticsHandler,
    ForLoopHandler,
    CommandProcessor,
)
from src.parser.handlers.environment import BaseEnvironmentHandler
from src.utils.tex_utils import (
    extract_nested_content,
    read_tex_file_content,
    strip_latex_comments,
)
from src.parser.sty_parser import LatexStyParser
from src.parser.patterns import PATTERNS, USEPACKAGE_PATTERN, WHITELISTED_COMMANDS

# Add these compiled patterns at module level
# match $ or % or { or } only if not preceded by \
# Update DELIM_PATTERN to also match double backslashes and opening braces {
DELIM_PATTERN = re.compile(
    r"(?<!\\)(?:\\\\|\$|%|(?:^|[ \t])\{|\s{|\\\^|\\(?![$%&_#{}^~\\]))"
)
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

        # STY parser
        self.sty_parser = LatexStyParser(logger=self.logger)
        # Bib parser
        self.bib_parser = BibParser(logger=self.logger)

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
            ContentCommandHandler(),
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
        self.sty_parser.clear()
        self.bib_parser.clear()

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

    def _check_usepackage(self, content: str) -> None:
        # check for STY file
        match = USEPACKAGE_PATTERN.match(content)
        if match:
            package_names = match.group(1).strip()
            for package_name in package_names.split(","):
                package_path = package_name.strip()
                if self.current_file_dir:
                    package_path = os.path.join(self.current_file_dir, package_path)
                if not package_path.endswith(".sty"):
                    package_path += ".sty"
                if os.path.exists(package_path):
                    tokens = self.sty_parser.parse_file(package_path)
                    for token in tokens:
                        self._process_new_definition_token(token)
                # else:
                #     self.logger.warning(f"Package file not found: {package_path}")
            return match.end()
        return 0

    def _process_new_definition_token(self, token: Dict) -> None:
        if token and "name" in token:
            # do not process content commands e.g. section etc
            cmd_name = token.get("name", "")
            if not cmd_name:
                return

            # handle envs first
            # floatname for self defined envs
            if token["type"] == "floatname":
                self.env_handler.process_floatname(cmd_name, token["title"])
                return
            elif token["type"] == "newenvironment":
                self.env_handler.process_newenvironment(
                    cmd_name,
                    token["begin_def"],
                    token["end_def"],
                    token["num_args"],
                    token["optional_args"],
                )
            elif token["type"] == "newtheorem":
                self.env_handler.process_newtheorem(cmd_name, token["title"])

            # then check commands
            if cmd_name in WHITELISTED_COMMANDS:
                return

            if token["type"] == "newcommand":
                # check if there is potential recursion.
                if re.search(r"\\" + cmd_name + r"(?![a-zA-Z@])", token["content"]):
                    self.logger.warning(
                        f"Potential recursion detected for newcommand: \\{cmd_name}, skipping..."
                    )
                    return
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
            elif token["type"] == "newcounter":
                self.command_processor.process_newcounter(cmd_name)
            elif token["type"] == "newlength":
                self.command_processor.process_newlength(cmd_name)
            elif token["type"] == "newother":
                self.command_processor.process_newX(cmd_name)
            elif token["type"] == "paired_delimiter":
                self.command_processor.process_paired_delimiter(
                    cmd_name, token["left_delim"], token["right_delim"]
                )

    def _check_for_new_definitions(self, content: str) -> None:
        """Check for new definitions in the content and process them"""
        if self.new_definition_handler.can_handle(content):
            token, end_pos = self.new_definition_handler.handle(content)
            if token:
                self._process_new_definition_token(token)
            return end_pos
        return 0

    def _convert_bibitem_to_token(self, entry: BibEntry) -> Dict:
        content = entry.content
        if entry.entry_type == "bibitem":
            content = self.parse(content)
        # else:
        #     content = {"type": "text", "content": content}
        return {
            "type": "bibitem",
            "content": content,
            "cite_key": entry.citation_key,
            "title": entry.title,
        }

    def _parse_bib_file(self, file_path: str) -> Dict:
        """Parse a bibliography file and return its contents as a token.

        Args:
            file_path: Path to the bibliography file (with or without extension)

        Returns:
            Dict with bibliography token containing parsed contents
        """
        if self.current_file_dir:
            file_path = os.path.join(self.current_file_dir, file_path)

        entries = self.bib_parser.parse_file(file_path)
        tokens = [self._convert_bibitem_to_token(entry) for entry in entries]
        return {"type": "bibliography", "content": tokens}

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
                    elif token["type"] == "bibliography":
                        if isinstance(token["content"], str):
                            entries = self.bib_parser.parse(token["content"])
                            token["content"] = [
                                self._convert_bibitem_to_token(entry)
                                for entry in entries
                            ]
                    elif token["type"] == "bibliography_file":
                        if token["content"]:
                            token = self._parse_bib_file(token["content"])
                    elif token["type"] == "input_file":
                        # open input file
                        if token["content"]:
                            file_path = token["content"]
                            if self.current_file_dir:
                                file_path = os.path.join(
                                    self.current_file_dir, file_path
                                )
                            input_tokens = self.parse_file(file_path, extension=".tex")
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
                    elif token["type"] in ["section", "paragraph", "title"]:
                        self.current_env = token
                        token["title"] = self.parse(token["title"])
                    elif token["type"] == "abstract":
                        token["content"] = self.parse(token["content"])
                    elif isinstance(handler, BaseEnvironmentHandler):
                        # algorithmic keep as literal?
                        if token["type"] not in ["algorithmic", "tabular"]:
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
        if isinstance(content, str):
            content = strip_latex_comments(content)

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

            end_pos = self._check_usepackage(content[current_pos:])
            if end_pos > 0:
                current_pos += end_pos
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
                    block = ""
                    if token:
                        block = token.get("if_content", "")
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

                            pos = current_pos - end_pos
                            surrounding_content = (
                                content[max(0, pos - 100) : pos]
                                + "-->"
                                + content[pos : pos + 100]
                            ).strip()
                            self.logger.warning(
                                f"\n*****\nUnknown command: Token: {token}\n***Surrounding content***\n{surrounding_content}\n*****"
                            )
                        else:
                            self.logger.warning(
                                f"*****(Again) Unknown command token: {token}*****"
                            )
                    continue

            self.add_token(content[current_pos], tokens)
            current_pos += 1

        return tokens

    def parse_file(
        self, file_path: str, extension: str = ".tex"
    ) -> List[Dict[str, str]]:
        """
        Parse a LaTeX file directly from the file path.

        Args:
            file_path: Path to the LaTeX file to parse
            extension: File extension to try if not found (default: .tex)

        Returns:
            List[Dict[str, str]]: List of parsed tokens
        """
        try:
            self.logger.info(f"Parsing file: {file_path}, ext: {extension}")

            file_abspath = os.path.abspath(file_path)
            if not self.current_file_dir:
                self.current_file_dir = os.path.dirname(file_abspath)

            try:
                content = read_tex_file_content(file_path, extension=extension)
            except FileNotFoundError:
                self.logger.error(f"File not found: {file_path}")
                return []

            out = self.parse(content)
            self.logger.info(f"Finished parsing file: {file_path}")
            return out
        except Exception as e:
            self.logger.error(f"Failed to parse file: {file_path}, error: {str(e)}")
            self.logger.error(
                "Stack trace:\n"
                + "".join(traceback.format_tb(e.__traceback__, limit=10))
            )
            self.logger.warning(f"Continuing from failed parse at {file_path}")
            return []


if __name__ == "__main__":

    logging.getLogger("asyncio").setLevel(logging.WARNING)

    logger = setup_logger(__name__, level=logging.DEBUG, log_file="logs/tex_parser.log")

    parser = LatexParser(logger=logger)

    file = "papers/new/arXiv-2005.14165v4/main.tex"
    # file = "papers/tested/arXiv-2301.10303v4.tex"
    tokens = parser.parse_file(file)

#     text = r"""
#         \newcommand{\@notice}{%
#         % give a bit of extra room back to authors on first page
#         \enlargethispage{2\baselineskip}%
#         \@float{noticebox}[b]%
#             \footnotesize\@noticestring%
#         \end@float%
#         }
# """
#     tokens = parser.parse(text)
#     print(tokens)
