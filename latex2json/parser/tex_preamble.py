import re
import sys, os
import logging
from typing import Dict

from latex2json.parser.patterns import (
    OPTIONAL_BRACE_PATTERN,
    USEPACKAGE_PATTERN,
    DOCUMENTCLASS_PATTERN,
    BRACE_CONTENT_PATTERN,
)
from latex2json.utils.tex_utils import read_tex_file_content, strip_latex_comments

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from latex2json.parser.handlers import NewDefinitionHandler


BEGIN_DOCUMENT_PATTERN = re.compile(r"\\begin\s*\{document\}", re.DOTALL)

USE_PATTERN = re.compile(
    USEPACKAGE_PATTERN.pattern
    + r"|"
    + r"\\use[a-zA-Z]+\s*%s\s*%s" % (OPTIONAL_BRACE_PATTERN, BRACE_CONTENT_PATTERN),
    re.DOTALL,
)
DELIM_PATTERN = re.compile(r"\\(?=[a-zA-Z@])[a-zA-Z@]+")


class LatexPreamble:
    def __init__(self, logger=None):
        self.logger = logger or logging.getLogger(__name__)

        self.new_definition_handler = NewDefinitionHandler()

    def clear(self):
        self.new_definition_handler.clear()

    def _preprocess_content(self, content: str) -> str:
        content = strip_latex_comments(content)

        # get all content before begin document
        begin_doc_search = re.search(BEGIN_DOCUMENT_PATTERN, content)
        if begin_doc_search:
            content = content[: begin_doc_search.start()]
        return content.strip()

    def get_preamble(
        self, content: str, file_dir: str = None
    ) -> tuple[str, list[Dict]]:
        """Handle all definitions and command expansions

        Returns:
            tuple: (processed_content, list of definition tokens)
        """

        content = self._preprocess_content(content)

        current_pos = 0

        output_preamble = ""

        # find from documentclass onwards
        doc_class_match = DOCUMENTCLASS_PATTERN.search(content)
        if doc_class_match:
            output_preamble += doc_class_match.group(0) + "\n\n"
            current_pos = doc_class_match.end()

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

            use_pattern_match = USE_PATTERN.match(content[current_pos:])
            if use_pattern_match:
                end_pos = use_pattern_match.end()
                output_preamble += use_pattern_match.group(0) + "\n"
                current_pos += end_pos
                continue

            # Expand commands using command_manager instead of command_processor
            if self.new_definition_handler.can_handle(content[current_pos:]):
                token, end_pos = self.new_definition_handler.handle(
                    content[current_pos:]
                )
                if end_pos > 0:
                    output_preamble += (
                        content[current_pos : current_pos + end_pos] + "\n"
                    )
                    current_pos += end_pos
                    continue

            current_pos += 1

        return output_preamble

    def get_preamble_from_file(self, file_path: str) -> str:
        try:
            content = read_tex_file_content(file_path, extension=".tex")
            return self.get_preamble(content)
        except FileNotFoundError:
            self.logger.error(f"File not found: {file_path}", exc_info=True)
            return ""


if __name__ == "__main__":
    text = r"""
\documentclass{article}

\newcommand{\aaa}{AAA}
\def\bea{\begin{eqnarray}}
\def\eea{\end{eqnarray}}

\usepackage{xcolor, tikz}
\usepackage[xxxx]{pgfplots}
\usetikzlibrary{arrows.meta}

\begin{document}
\end{document}
    """

    processor = LatexPreamble()

    # out = processor.get_preamble(text)
    # print(out)

    out = processor.get_preamble_from_file("papers/new/arXiv-2304.02643v1/segany.tex")
    print(out)
