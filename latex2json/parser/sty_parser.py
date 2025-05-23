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

from latex2json.parser.handlers import (
    IfElseBlockHandler,
)
from latex2json.utils.tex_utils import (
    extract_nested_content,
    read_tex_file_content,
    strip_latex_comments,
)
from latex2json.parser.patterns import (
    USEPACKAGE_PATTERN,
    WHITELISTED_COMMANDS,
    DELIM_PATTERN,
    LOADCLASS_PATTERN,
)
from latex2json.parser.handlers.command_manager import CommandManager

INCLUDE_PATTERN = re.compile(r"\\input\s*\{([^}]+)\}", re.DOTALL)

AT_BEGIN_DOC_PATTERN = re.compile(r"\\AtBeginDocument\s*{", re.IGNORECASE)


class LatexStyParser:
    def __init__(self, logger: logging.Logger = None):
        # for logging
        self.logger = logger or logging.getLogger(__name__)

        self.current_file_dir = None
        self.parsed_files = set()

        self.command_manager = CommandManager(
            command_types={"newif"},
            logger=self.logger,
        )

        self.if_else_block_handler = IfElseBlockHandler(logger=self.logger)

    def clear(self):
        self.current_file_dir = None
        self.parsed_files.clear()
        self.if_else_block_handler.clear()
        self.command_manager.clear()

    def _check_for_new_definitions(self, content: str):
        """Check for new definitions in the content and process them"""
        token, end_pos = self.command_manager.process_definition(content)
        if token:
            cmd_name = token.get("name", "")
            if not cmd_name:
                return None, end_pos
            if cmd_name in WHITELISTED_COMMANDS:
                return None, end_pos

            if token["type"] == "newif":
                self.if_else_block_handler.process_newif(cmd_name)

            return token, end_pos
        return None, 0

    def _parse_packages(self, package_names: list[str], extension=".sty") -> list[Dict]:
        tokens = []
        for package_name in package_names:
            package_path = package_name.strip()
            if self.current_file_dir:
                package_path = os.path.join(self.current_file_dir, package_path)
            if not package_path.endswith(extension):
                package_path += extension
            if os.path.exists(package_path):
                tokens.extend(self.parse_file(package_path))
        return tokens

    def _check_usepackage(self, content: str) -> Tuple[List[Dict], int]:
        """Check for usepackage commands and parse any found .sty files

        Returns:
            tuple: (list of tokens from sty files, end_position)
        """
        match = USEPACKAGE_PATTERN.match(content) or INCLUDE_PATTERN.match(content)
        if match:
            package_names = match.group(1).strip()
            tokens = self._parse_packages(package_names.split(","))
            return tokens, match.end()
        return [], 0

    def _check_loadclass(self, content: str) -> Tuple[List[Dict], int]:
        r"""Check for \loadclass commands and parse any found .cls files

        Returns:
            tuple: (list of tokens from cls files, end_position)
        """
        match = LOADCLASS_PATTERN.match(content)
        if match:
            class_names = match.group(1).strip()
            tokens = self._parse_packages(class_names.split(","), extension=".cls")
            return tokens, match.end()
        return [], 0

    def _handle_if_else_block(self, content: str, current_pos: int) -> Tuple[str, int]:
        """Handle if-else blocks and return the processed content and new position"""
        if self.if_else_block_handler.can_handle(content[current_pos:]):
            token, end_pos = self.if_else_block_handler.handle(content[current_pos:])
            if end_pos > 0:
                block = ""
                if token:
                    typing = token.get("type", "")
                    if "@" not in typing:
                        block = token.get("if_content", "")
                    # Handle iffileexists condition
                    elif typing == "conditional-iffileexists":
                        block = token.get("else_content", "")

                        file_path = token.get("condition", "").strip()
                        if file_path:
                            if self.current_file_dir:
                                file_path = os.path.join(
                                    self.current_file_dir, file_path
                                )
                            if os.path.exists(file_path):
                                block = token.get("if_content", "")
                return block, current_pos + end_pos
        return None, current_pos

    def parse(
        self,
        content: str,
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

        if isinstance(content, str):
            content = strip_latex_comments(content)

        tokens = []
        current_pos = 0

        while current_pos < len(content):
            # Skip whitespace
            while current_pos < len(content) and content[current_pos].isspace():
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
                        tokens.extend(nested_tokens)
                    current_pos += end_pos
                    continue

            # print(content[current_pos : current_pos + 20])
            # if content[current_pos : current_pos + 20].startswith(r"\icmlrulerbox"):
            #     raise Exception("WTF")

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
                current_pos += next_pos
                if not next_delimiter:
                    break
                continue

            match = AT_BEGIN_DOC_PATTERN.match(content[current_pos:])
            if match:
                start_pos = current_pos + match.end() - 1
                text, end_pos = extract_nested_content(content[start_pos:])
                if text:
                    # replace the matched user command with the expanded text
                    text = text.strip()
                    content = (
                        content[:current_pos] + text + content[start_pos + end_pos :]
                    )
                    continue

            # check for user defined commands (important to check before new definitions in case of floating \csname)
            if self.command_manager.can_handle(content[current_pos:]):
                text, end_pos = self.command_manager.handle(content[current_pos:])
                if end_pos > 0:
                    # replace the matched user command with the expanded text
                    content = (
                        content[:current_pos] + text + content[current_pos + end_pos :]
                    )
                    continue

            new_tokens, end_pos = self._check_usepackage(content[current_pos:])
            if end_pos > 0:
                current_pos += end_pos
                tokens.extend(new_tokens)
                continue

            # Add check for loadclass
            new_tokens, end_pos = self._check_loadclass(content[current_pos:])
            if end_pos > 0:
                current_pos += end_pos
                tokens.extend(new_tokens)
                continue

            # check for new definition commands
            token, end_pos = self._check_for_new_definitions(content[current_pos:])
            if end_pos > 0:
                current_pos += end_pos
                if token:
                    tokens.append(token)
                continue

            # check for if else blocks
            result, new_pos = self._handle_if_else_block(content, current_pos)
            if result is not None:
                content = content[:current_pos] + result + content[new_pos:]
                continue

            current_pos += 1

        return tokens

    def parse_file(
        self, file_path: str, extension: str = ".sty"
    ) -> List[Dict[str, str]]:
        try:
            file_path = os.path.abspath(file_path)
            if file_path in self.parsed_files:
                self.logger.info(f"File already parsed, skipping: {file_path}")
                return []

            self.logger.info(f"Parsing file: {file_path}, ext: {extension}")
            current_file_dir = self.current_file_dir

            content = read_tex_file_content(file_path, extension=extension)
            self.parsed_files.add(file_path)

            tokens = self.parse(content, file_path=file_path)

            for token in tokens:
                token["is_sty"] = True

            self.current_file_dir = current_file_dir
            self.logger.info(f"Finished parsing file: {file_path}")
            return tokens
        except Exception as e:
            self.logger.error(
                f"Failed to parse file: {file_path}, error: {str(e)}", exc_info=True
            )
            return []


if __name__ == "__main__":
    # More detailed logging configuration for direct script execution
    logging.basicConfig(
        level=logging.DEBUG,  # More verbose when running directly
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        force=True,
        handlers=[
            logging.FileHandler("logs/sty_parser.log"),
            logging.StreamHandler(),  # Optional: also output to console
        ],
    )
    logging.getLogger("asyncio").setLevel(logging.WARNING)

    logger = logging.getLogger(__name__)

    parser = LatexStyParser(logger=logger)

    file = "papers/new/arXiv-2301.13741v3/icml2023.sty"
    tokens = parser.parse_file(file)
    # print(tokens)
