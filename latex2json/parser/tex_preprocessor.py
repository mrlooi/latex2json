import re
import sys, os, traceback
import logging
from typing import Dict

from latex2json.parser.handlers.if_else_statements import IfElseBlockHandler
from latex2json.parser.patterns import (
    USEPACKAGE_PATTERN,
    WHITELISTED_COMMANDS,
    DELIM_PATTERN,
)
from latex2json.utils.logger import setup_logger

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


from latex2json.parser.handlers import (
    NewDefinitionHandler,
    CommandProcessor,
)
from latex2json.utils.tex_utils import (
    strip_latex_comments,
)
from latex2json.parser.sty_parser import LatexStyParser

OPTIONAL_BRACE_PATTERN = r"(?:\[[^\]]*\])?"

DOCUMENTCLASS_PATTERN = re.compile(
    r"\\documentclass\s*%s\s*\{([^}]+)\}" % OPTIONAL_BRACE_PATTERN
)
ADD_TO_PATTERN = re.compile(r"\\addto\s*(?:{?\\[^}\s]+}?)\s*\{")  # e.g. \addto\cmd{...}


class LatexPreprocessor:
    def __init__(self, logger=None):
        self.logger = logger or logging.getLogger(__name__)

        self.command_processor = CommandProcessor()
        self.new_definition_handler = NewDefinitionHandler()
        self.if_else_block_handler = IfElseBlockHandler(logger=self.logger)
        self.sty_parser = LatexStyParser(logger=self.logger)

    def clear(self):
        self.if_else_block_handler.clear()
        self.new_definition_handler.clear()
        self.command_processor.clear()
        self.sty_parser.clear()

    def preprocess(self, content: str, file_dir=None) -> tuple[str, list[Dict]]:
        """Main preprocessing pipeline

        Returns:
            tuple: (processed_content, list of definition tokens)
        """
        # 1. Strip comments
        content = strip_latex_comments(content)

        # 2. Check for documentclass (only once at the start)
        end_pos, out_tokens = self._check_documentclass(content, file_dir)
        if end_pos > 0:
            content = content[end_pos:]

        # 3. Process all definitions and expand commands
        content, tokens = self._process_definitions_and_expand(content, file_dir)
        out_tokens.extend(tokens)

        return content, out_tokens

    def _process_new_definition_token(self, token: Dict) -> None:
        if token and "name" in token:
            # do not process content commands e.g. section etc
            cmd_name = token.get("name", "")
            if not cmd_name:
                return

            # then check commands
            if cmd_name in WHITELISTED_COMMANDS:
                return

            if token["type"] == "newcommand":
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
            return token, end_pos
        return None, 0

    def _check_documentclass(
        self, content: str, file_dir: str = None
    ) -> tuple[int, list[Dict]]:
        """Check for documentclass command

        Returns:
            int: end position of the match
        """
        match = DOCUMENTCLASS_PATTERN.search(content)
        if match:
            cls_name = match.group(1).strip()
            tokens = self._parse_packages([cls_name], file_dir, ".cls")
            return match.end(), tokens
        return 0, []

    def _check_usepackage(
        self, content: str, file_dir: str = None
    ) -> tuple[int, list[Dict]]:
        """Check for usepackage commands and parse any found .sty files

        Returns:
            tuple: (end_position, list of tokens from sty files)
        """
        # check for STY file
        match = USEPACKAGE_PATTERN.match(content)
        tokens = []
        if match:
            package_names = match.group(1).strip()
            tokens = self._parse_packages(package_names.split(","), file_dir, ".sty")
            return match.end(), tokens
        return 0, []

    def _parse_packages(
        self, package_names: list[str], file_dir: str = None, extension=".sty"
    ) -> list[Dict]:
        tokens = []
        for package_name in package_names:
            package_path = package_name.strip()
            if file_dir:
                package_path = os.path.join(file_dir, package_path)
            if not package_path.endswith(extension):
                package_path += extension
            if os.path.exists(package_path):
                _tokens = self.sty_parser.parse_file(package_path)
                tokens.extend(_tokens)
                for token in _tokens:
                    self._process_new_definition_token(token)
        return tokens

    def _process_definitions_and_expand(
        self, content: str, file_dir: str = None
    ) -> tuple[str, list[Dict]]:
        """Handle all definitions and command expansions

        Returns:
            tuple: (processed_content, list of definition tokens)
        """
        current_pos = 0
        tokens = []  # Store all definition tokens

        while current_pos < len(content):
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

            # Process addto by simply treating the content inside as {...}
            match = ADD_TO_PATTERN.match(content[current_pos:])
            if match:
                content = (
                    content[:current_pos] + content[current_pos + match.end() - 1 :]
                )
                continue

            # Process definitions
            token, end_pos = self._check_for_new_definitions(content[current_pos:])
            if token:
                tokens.append(token)  # Store the token
            if end_pos > 0:
                content = content[:current_pos] + content[current_pos + end_pos :]
                continue

            # Update usepackage check to handle returned tokens
            end_pos, sty_tokens = self._check_usepackage(
                content[current_pos:], file_dir
            )
            tokens.extend(sty_tokens)  # Add sty tokens to our token list
            if end_pos > 0:
                content = content[:current_pos] + content[current_pos + end_pos :]
                continue

            # Expand commands
            if self.command_processor.can_handle(content[current_pos:]):
                expanded_text, end_pos = self.command_processor.handle(
                    content[current_pos:]
                )
                if end_pos > 0:
                    content = (
                        content[:current_pos]
                        + expanded_text
                        + content[current_pos + end_pos :]
                    )
                    continue

            # check for if else blocks
            if self.if_else_block_handler.can_handle(content[current_pos:]):
                token, end_pos = self.if_else_block_handler.handle(
                    content[current_pos:]
                )
                if end_pos > 0:
                    block = ""
                    if token:
                        if "@" not in token.get("type", ""):
                            block = token.get("if_content", "")
                    content = (
                        content[:current_pos] + block + content[current_pos + end_pos :]
                    )
                    continue

            current_pos += 1

        return content, tokens


if __name__ == "__main__":
    text = r"""
    \definecolor{mycolor}{rgb}{1,0,0}
    \usepackage{ssss}
    \newcommand{\aaa}{AAA}
    \def\bea{\begin{eqnarray}}
    \def\eea{\end{eqnarray}}

    \input{sss}

    \bea
    \eea    
    """

    processor = LatexPreprocessor()
    out, tokens = processor.preprocess(text)
    print(out)
