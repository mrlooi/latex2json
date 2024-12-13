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
    NewDefinitionHandler,
    IfElseBlockHandler,
)
from src.tex_utils import (
    extract_nested_content,
    read_tex_file_content,
    strip_latex_comments,
)
from src.patterns import USEPACKAGE_PATTERN

# Add these compiled patterns at module level
# match $ or % or { or } only if not preceded by \
# Update DELIM_PATTERN to also match double backslashes and opening braces {
DELIM_PATTERN = re.compile(r"(?<!\\)(?:\\\\|%|(?:^|[ \t])\{|\\\^|\\(?![$%&_#{}^~\\]))")

INCLUDE_PATTERN = re.compile(r"\\input\s*\{([^}]+)\}", re.DOTALL)


class LatexStyParser:
    def __init__(self, logger: logging.Logger = None):
        # for logging
        self.logger = logger or logging.getLogger(__name__)

        self.current_file_dir = None

        self.if_else_block_handler = IfElseBlockHandler()
        self.new_definition_handler = NewDefinitionHandler()

    def clear(self):
        self.current_file_dir = None
        self.if_else_block_handler.clear()
        self.new_definition_handler.clear()

    def _check_for_new_definitions(self, content: str):
        """Check for new definitions in the content and process them"""
        if self.new_definition_handler.can_handle(content):
            token, end_pos = self.new_definition_handler.handle(content)
            if token:
                return token, end_pos
        return None, 0

    def _check_usepackage(self, content: str) -> None:
        match = USEPACKAGE_PATTERN.match(content) or INCLUDE_PATTERN.match(content)
        tokens = []
        if match:
            package_name = match.group(1)
            if not package_name.endswith(".sty"):
                package_name += ".sty"
            package_path = package_name
            if self.current_file_dir:
                package_path = os.path.join(self.current_file_dir, package_name)
            if os.path.exists(package_path):
                tokens = self.parse_file(package_path)
            return tokens, match.end()
        return tokens, 0

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

            new_tokens, end_pos = self._check_usepackage(content[current_pos:])
            if end_pos > 0:
                current_pos += end_pos
                tokens.extend(new_tokens)
                continue

            # check for new definition commands
            token, end_pos = self._check_for_new_definitions(content[current_pos:])
            if end_pos > 0:
                current_pos += end_pos
                tokens.append(token)
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

            current_pos += 1

        return tokens

    def parse_file(
        self, file_path: str, extension: str = ".sty"
    ) -> List[Dict[str, str]]:
        try:
            self.logger.info(f"Parsing file: {file_path}, ext: {extension}")
            current_file_dir = self.current_file_dir
            content = read_tex_file_content(file_path, extension=extension)
            out = self.parse(content, file_path=file_path)
            self.current_file_dir = current_file_dir
            return out
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

    parser = LatexStyParser(logger=logger)

    file = "papers/arXiv-1512.03385v1/cvpr.sty"
    tokens = parser.parse_file(file)
