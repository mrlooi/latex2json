import re
import sys, os
import logging
from typing import Dict

from latex2json.parser.handlers.formatting import FormattingHandler
from latex2json.parser.handlers.if_else_statements import IfElseBlockHandler
from latex2json.parser.patterns import (
    USEPACKAGE_PATTERN,
    WHITELISTED_COMMANDS,
    DELIM_PATTERN,
    DOCUMENTCLASS_PATTERN,
)

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from latex2json.parser.handlers.code_block import PATTERNS as VERBATIM_PATTERNS

from latex2json.parser.handlers import (
    EquationHandler,
)
from latex2json.utils.tex_utils import (
    check_string_has_hash_number,
    strip_latex_comments,
    normalize_whitespace_and_lines,
)
from latex2json.parser.sty_parser import LatexStyParser
from latex2json.parser.handlers.command_manager import CommandManager


ADD_TO_PATTERN = re.compile(r"\\addto\s*(?:{?\\[^}\s]+}?)\s*\{")  # e.g. \addto\cmd{...}

ALL_VERBATIM_PATTERNS = list(VERBATIM_PATTERNS.values())
ALL_VERBATIM_PATTERNS.append(
    re.compile(r"\\begin\s*\{algorithm\}(.*?)\\end\s*\{algorithm\}", re.DOTALL)
)
ALL_VERBATIM_PATTERNS.append(
    re.compile(r"\\begin\s*\{algorithmic\}(.*?)\\end\s*\{algorithmic\}", re.DOTALL)
)
ALL_VERBATIM_PATTERNS.append(
    re.compile(
        r"\\begin\s*\{(picture|tikzpicture|pgfpicture)\}(.*?)\\end\s*\{\1\}", re.DOTALL
    )
)

DELIM_PATTERN_WITH_QUOTES = re.compile(DELIM_PATTERN.pattern + r"|`")

QUOTE_PATTERNS = {
    "double_quotes": re.compile(
        r"``(.*?)''", re.DOTALL
    ),  # latex quotes e.g. ``aaa'' -> "aaa"
    "single_quotes": re.compile(
        r"`(.*?)'", re.DOTALL
    ),  # latex quotes e.g. `aaa' -> 'aaa'
}


def restore_placeholder_blocks(content: str, blocks: dict) -> str:
    """
    Restores the blocks in the content by replacing placeholders with the original blocks.
    """
    for placeholder, block in blocks.items():
        content = content.replace(placeholder, block)
    return content


class LatexPreprocessor:
    def __init__(self, logger=None):
        self.logger = logger or logging.getLogger(__name__)

        self.command_manager = CommandManager(logger=self.logger)
        self.formatting_handler = FormattingHandler()
        self.if_else_block_handler = IfElseBlockHandler(logger=self.logger)
        self.sty_parser = LatexStyParser(logger=self.logger)

        # added equation handler to parse out math mode
        self.equation_handler = EquationHandler()

    def clear(self):
        self.if_else_block_handler.clear()
        self.command_manager.clear()
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

        # 4. After all expansions, normalize whitespace and lines
        # But make sure to not normalize verbatim environments (VERBATIM_PATTERNS)
        # so we first need to find all verbatim environments, extract them out, normalize the rest, then put the verbatim environments back in
        content, verbatim_blocks = self._extract_verbatim_blocks(content)
        content = normalize_whitespace_and_lines(content)
        content = restore_placeholder_blocks(content, verbatim_blocks)

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

            # Process the token using command_manager instead of directly
            token_type = token.get("type", "")

            # Special handling for "newif" to maintain compatibility with if_else_block_handler
            if token_type == "newif":
                self.if_else_block_handler.process_newif(cmd_name)

            # Using command_manager for proper registration of the command

            self.command_manager.register_command(token)

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

        math_blocks = {}

        while current_pos < len(content):
            # find the next delimiter (this block allows us to quickly identify and process chunks of text between special LaTeX delimiters
            # without it, we would have to parse the entire content string character by character. which would be slower.)
            # if next delimiter exists, we need to store the text before the next delimiter (or all remaining text if no delimiter)
            next_delimiter = DELIM_PATTERN_WITH_QUOTES.search(content[current_pos:])
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

            # check math mode to ignore expansion of math mode commands
            if self.equation_handler.can_handle(content[current_pos:]):
                token, end_pos = self.equation_handler.handle(content[current_pos:])
                if end_pos > 0:
                    # store the math block as placeholder to restore later
                    placeholder = f"__MATH_BLOCK_{len(math_blocks)}__"
                    math_blocks[placeholder] = content[
                        current_pos : current_pos + end_pos
                    ]
                    content = (
                        content[:current_pos]
                        + placeholder
                        + content[current_pos + end_pos :]
                    )
                    continue

            # check quotes
            for quote_type, pattern in QUOTE_PATTERNS.items():
                match = pattern.match(content[current_pos:])
                if match:
                    quote_content = match.group(1)
                    if quote_type == "double_quotes":
                        quote_content = '"' + quote_content + '"'
                    elif quote_type == "single_quotes":
                        quote_content = "'" + quote_content + "'"
                    content = (
                        content[:current_pos]
                        + quote_content
                        + content[current_pos + match.end() :]
                    )
                    continue

            # Process definitions
            token, end_pos = self.command_manager.process_definition(
                content[current_pos:], register=False
            )
            if token:
                if token.get("type", "").startswith("keyval"):
                    current_pos += end_pos
                    continue
                # Skip macro definitions that have parameters (#1, #2) or take arguments,
                # as these need to be expanded later when actual values are provided
                if token.get("num_args", 0) > 0 or check_string_has_hash_number(
                    token.get("content", "")
                ):
                    current_pos += end_pos
                    continue
                self._process_new_definition_token(token)
                tokens.append(token)
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

            # Expand commands using command_manager instead of command_processor
            if self.command_manager.can_handle(content[current_pos:]):
                expanded_text, end_pos = self.command_manager.handle(
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

            # check for formatting
            if self.formatting_handler.can_handle(content[current_pos:]):
                token, end_pos = self.formatting_handler.handle(content[current_pos:])
                if end_pos > 0:
                    block = ""
                    if token:
                        block = token.get("content", "")
                    content = (
                        content[:current_pos] + block + content[current_pos + end_pos :]
                    )
                    continue

            current_pos += 1

        # restore math blocks
        content = restore_placeholder_blocks(content, math_blocks)

        return content, tokens

    def _extract_verbatim_blocks(self, content: str) -> tuple[str, dict]:
        """
        Extracts verbatim environments from the content and replaces them with placeholders.
        Returns the modified content and a dictionary mapping placeholders to the original verbatim blocks.
        """
        blocks = {}
        placeholder_prefix = "__VERBATIM_BLOCK__"
        output = []
        pos = 0
        placeholder_index = 0

        while pos < len(content):
            earliest_match = None
            earliest_start = len(content)
            # Look for the earliest occurrence from any of the verbatim patterns
            for pattern in ALL_VERBATIM_PATTERNS:
                m = pattern.search(content, pos)
                if m and m.start() < earliest_start:
                    earliest_match = m
                    earliest_start = m.start()

            if earliest_match:
                # Append the text before the match
                output.append(content[pos : earliest_match.start()])
                # Create a unique placeholder
                placeholder = f"{placeholder_prefix}{placeholder_index}__"
                output.append(placeholder)
                blocks[placeholder] = earliest_match.group(0)
                placeholder_index += 1
                pos = earliest_match.end()
            else:
                output.append(content[pos:])
                break

        return "".join(output), blocks


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

    HAHAHA 

    AAAA \newline
    BBB
    CCC

    \begin{lstlisting}
def binary_search(arr, target):
    left, right = 0, len(arr) - 1
    
    while left <= right:  # Main search loop
        mid = (left + right) // 2
        if arr[mid] == target:
            return mid    # Found the target
        elif arr[mid] < target:
            left = mid + 1
        else:
            right = mid - 1
            
    return -1  # Target not found
\end{lstlisting}
    """

    processor = LatexPreprocessor()
    out, tokens = processor.preprocess(text)
    print(out)
