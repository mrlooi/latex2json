from collections import OrderedDict
import re
from typing import List, Dict, Tuple, Union
import sys, os, traceback
import logging

from latex2json.parser.bib_parser import BibEntry, BibParser
from latex2json.utils.logger import setup_logger

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


from latex2json.parser.handlers import (
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
from latex2json.parser.handlers.environment import BaseEnvironmentHandler
from latex2json.utils.tex_utils import (
    extract_nested_content,
    read_tex_file_content,
    strip_latex_comments,
)
from latex2json.parser.tex_preprocessor import LatexPreprocessor
from latex2json.parser.patterns import (
    PATTERNS,
    WHITELISTED_COMMANDS,
    DELIM_PATTERN,
)
from latex2json.parser.packages import get_all_custom_handlers

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

        # color definitions via \definecolor
        self.colors = {}  # e.g. {"mycolor": {"format": "HTML", "value": "FF0000"}}

        # Bib parser
        self.bib_parser = BibParser(logger=self.logger)

        # Regex patterns for different LaTeX elements
        self.command_processor = CommandProcessor()
        self.env_handler = EnvironmentHandler(logger=self.logger)

        self.legacy_formatting_handler = LegacyFormattingHandler()
        self.if_else_block_handler = IfElseBlockHandler(logger=self.logger)
        # handlers
        self.handlers: List[TokenHandler] = [
            # Add custom package handlers in their priority order
            *get_all_custom_handlers(),
            # Standard/common packages
            AuthorHandler(self.parse),
            # ignore unicode conversion for equations
            EquationHandler(
                lambda x: self._expand_command(x, ignore_unicode=True, math_mode=True)
            ),
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

        # Add preprocessor
        self.preprocessor = LatexPreprocessor(logger=self.logger)

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
        self.colors = {}
        self.current_str = ""
        self.current_file_dir = None
        self.current_env = None

        self.command_processor.clear()
        # handlers
        for handler in self.handlers:
            handler.clear()
        self.if_else_block_handler.clear()
        self.new_definition_handler.clear()

        # preprocessor
        self.preprocessor.clear()
        # bib parser
        self.bib_parser.clear()

    def get_colors(self) -> Dict[str, Dict[str, str]]:
        return self.colors.copy()

    def _expand_command(
        self, content: str, ignore_unicode: bool = False, math_mode: bool = False
    ) -> str:
        """Expand LaTeX commands in the content"""
        out, match_count = self.command_processor.expand_commands(
            content, ignore_unicode, math_mode
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
                self.add_token({"type": "label", "content": content}, tokens)

    def add_token(
        self,
        token: str | Dict | List[Dict],
        tokens: List[Dict],
        add_space: bool = False,
    ):
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
                return
            elif isinstance(token_dict, dict):
                typing = token_dict.get("type")
                if typing == "text":
                    # concat text if prev text is also plain text
                    if (
                        tokens
                        and tokens[-1].get("type") == "text"
                        and "styles" not in token_dict
                        and "styles" not in tokens[-1]
                    ):
                        # check consistent spacing
                        if add_space and not tokens[-1]["content"].endswith(" "):
                            tokens[-1]["content"] += " "
                        tokens[-1]["content"] += token_dict["content"]
                        return
                elif typing in ["group", "environment", "list"]:
                    # ignore empty
                    if len(token_dict["content"]) < 1:
                        return

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

    def _process_new_definition_token(self, token: Dict) -> None:
        if token and "name" in token:
            # do not process content commands e.g. section etc
            cmd_name = token.get("name", "")
            if not cmd_name:
                return

            typing = token["type"]

            if typing == "definecolor":
                self.colors[cmd_name] = {
                    "format": token["format"],
                    "value": token["value"],
                }
                return

            # handle envs first
            # floatname for self defined envs
            if typing == "floatname":
                self.env_handler.process_floatname(cmd_name, token["title"])
                return
            elif typing == "newenvironment":
                self.env_handler.process_newenvironment(
                    cmd_name,
                    token["begin_def"],
                    token["end_def"],
                    token["num_args"],
                    token["optional_args"],
                )
            elif typing == "newtheorem":
                self.env_handler.process_newtheorem(cmd_name, token["title"])

            # then check commands
            if cmd_name in WHITELISTED_COMMANDS:
                return

            if typing == "newcommand":
                # check if there is potential recursion.
                if re.search(token["usage_pattern"], token["content"]):
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
            elif typing == "def":
                self.command_processor.process_newdef(
                    cmd_name,
                    token["content"],
                    token["num_args"],
                    token["usage_pattern"],
                    token["is_edef"],
                )
            elif typing == "newif":
                self.command_processor.process_newif(cmd_name)
                self.if_else_block_handler.process_newif(cmd_name)
            elif typing == "newcounter":
                self.command_processor.process_newcounter(cmd_name)
            elif typing == "newlength":
                self.command_processor.process_newlength(cmd_name)
            elif typing == "newtoks":
                self.command_processor.process_newtoks(cmd_name)
            elif typing == "paired_delimiter":
                self.command_processor.process_paired_delimiter(
                    cmd_name, token["left_delim"], token["right_delim"]
                )
            elif typing in ["newother", "newfam", "font"]:
                self.command_processor.process_newX(cmd_name)

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
                Can be a comma-separated list of files like "references, another_references, ..."

        Returns:
            Dict with bibliography token containing parsed contents
        """
        all_tokens = []

        # Handle comma-separated list of files or single file
        file_paths = [p.strip() for p in file_path.split(",") if p.strip()]

        for path in file_paths:
            # Apply current_file_dir to each path
            full_path = (
                os.path.join(self.current_file_dir, path)
                if self.current_file_dir
                else path
            )

            try:
                entries = self.bib_parser.parse_file(full_path)
                all_tokens.extend(
                    [self._convert_bibitem_to_token(entry) for entry in entries]
                )
            except Exception as e:
                self.logger.warning(
                    f"Failed to parse bibliography file: {full_path}, error: {str(e)}"
                )

        return {"type": "bibliography", "content": all_tokens}

    def _process_token(
        self, token: str | Dict | List[Dict], tokens: List[Dict], is_env_type=False
    ) -> None:
        if isinstance(token, str):
            token = {"type": "text", "content": token}
        elif isinstance(token, list):
            for t in token:
                self._process_token(t, tokens)
            return
        else:
            if token["type"] == "bibliography":
                if isinstance(token["content"], str):
                    entries = self.bib_parser.parse(token["content"])
                    token["content"] = [
                        self._convert_bibitem_to_token(entry) for entry in entries
                    ]
            elif token["type"] == "bibliography_file":
                if token["content"]:
                    token = self._parse_bib_file(token["content"])
            elif token["type"] == "input_file":
                # open input file
                if token["content"]:
                    file_path = token["content"]
                    if self.current_file_dir:
                        file_path = os.path.join(self.current_file_dir, file_path)
                    input_tokens = self.parse_file(file_path, extension=".tex")
                    if input_tokens:
                        tokens.extend(input_tokens)
                return
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
            elif is_env_type:
                # algorithmic keep as literal?
                if token["type"] not in ["algorithmic", "tabular"]:
                    prev_env = self.current_env
                    self.current_env = token
                    token["content"] = self.parse(token["content"])
                    self.current_env = prev_env

                # make math env title a list of tokens
                if (
                    token["type"] == "math_env"
                    and "title" in token
                    and isinstance(token["title"], str)
                ):
                    token["title"] = self.parse(token["title"])

        self.add_token(token, tokens)

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
                    self._process_token(
                        token,
                        tokens,
                        is_env_type=isinstance(handler, BaseEnvironmentHandler),
                    )
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
            elif matched_type == "newline":
                self.add_token("\n", tokens)
            elif matched_type == "break_spacing":
                self.add_token(line_break_delimiter, tokens)
            elif matched_type == "line_continuation":
                return True, match.end()
            else:
                # For all other token types, expand any commands in their content
                x = match.group(1) if match.groups() else match.group(0)
                x = self._expand_command(x)
                self.add_token({"type": matched_type, "content": x}, tokens)

            return True, match.end()

        return False, 0

    def parse(
        self,
        content: str,
        line_break_delimiter: str = "\n",
        handle_unknown_commands: bool = True,
        handle_legacy_formatting: bool = True,
        preprocess: bool = False,
    ) -> List[Dict]:
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
        if not isinstance(content, str):
            return content

        content = strip_latex_comments(content)

        if preprocess:
            content = self.preprocess(content)

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
                    # skip delimited braces for next pass
                    if text.endswith("{"):
                        text = text[:-1]
                        next_pos -= 1
                    if handle_unknown_commands:
                        text = self._expand_command(text)
                    # check if preceding text is a space
                    add_space = False
                    if current_pos > 0 and content[current_pos - 1].isspace():
                        add_space = True
                    self.add_token(text, tokens, add_space)
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

    def preprocess(self, content: str) -> str:
        # Preprocess content before parsing
        content, definition_tokens = self.preprocessor.preprocess(
            content, self.current_file_dir
        )

        # Process any definition tokens
        for token in definition_tokens:
            self._process_new_definition_token(token)

        return content

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
                self.logger.error(f"File not found: {file_path}", exc_info=True)
                return []

            out = self.parse(content, preprocess=True)
            self.logger.info(f"Finished parsing file: {file_path}")
            return out
        except Exception as e:
            self.logger.error(
                f"Failed to parse file: {file_path}, error: {str(e)}", exc_info=True
            )
            self.logger.warning(f"Continuing from failed parse at {file_path}")
            return []


if __name__ == "__main__":

    logging.getLogger("asyncio").setLevel(logging.WARNING)

    logger = setup_logger(__name__, level=logging.DEBUG, log_file="logs/tex_parser.log")

    parser = LatexParser(logger=logger)

    file = "papers/tested/arXiv-2402.03300v3/main.tex"
    # file = "papers/tested/arXiv-1706.03762v7/model_architecture.tex"
    tokens = parser.parse_file(file)

#     text = r"""
# \textit{Data Source $\mathcal{D}$}, which determines the training data;

# """
#     tokens = parser.parse(text, preprocess=True)
#     print(tokens)
