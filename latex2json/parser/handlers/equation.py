from collections import OrderedDict
import re
from typing import Callable, Dict, Optional, Tuple
from latex2json.parser.handlers.content_command import ContentCommandHandler
from latex2json.utils.tex_utils import (
    extract_nested_content,
    check_delimiter_balance,
    extract_equation_content,
)
from latex2json.parser.patterns import LABEL_PATTERN
from latex2json.parser.handlers.base import TokenHandler
from latex2json.parser.handlers.environment import convert_any_env_pairs_to_begin_end
from latex2json.parser.handlers.formatting import FormattingHandler

# Define equation environments
EQUATION_ENV = {
    "equation",  # basic numbered equation
    "align",  # aligned equations
    "aligned",  # aligned equations
    "gather",  # centered equations
    "multline",  # long equation split across lines
    "eqnarray",  # old style align (deprecated but used)
    "flalign",  # flush aligned equations
    "alignat",  # aligned with custom spacing
    "dmath",  # display math
}

# Define equation patterns
RAW_PATTERNS = OrderedDict(
    [
        ("equation_display_$$", re.compile(r"\$\$([\s\S]*?)\$\$", re.DOTALL)),
        ("equation_inline_$", re.compile(r"\$([^$]*)\$")),
        ("equation_display_brackets", re.compile(r"\\\[(.*?)\\\]", re.DOTALL)),
        ("equation_inline_brackets", re.compile(r"\\\((.*?)\\\)")),
    ]
)

# Add equation environment patterns
PATTERNS = OrderedDict(
    (
        name,
        re.compile(
            rf"\\begin\s*\{{{name}\*?\}}(.*?)\\end\s*\{{{name}(?:\*)?\}}", re.DOTALL
        ),
    )
    for name in EQUATION_ENV
)
PATTERNS.update(RAW_PATTERNS)


class EquationHandler(TokenHandler):
    should_extract_content_placeholders = True

    """Handler for LaTeX equations and math environments."""

    def __init__(self, process_content_fn: Optional[Callable] = None):
        self.process_content_fn = process_content_fn
        self.formatter = FormattingHandler()
        # content command handler to parse out e.g. includegraphics/eqref etc inside equation/math itself
        self.content_command = ContentCommandHandler()

    def can_handle(self, content: str) -> bool:
        """Check if content contains an equation pattern."""
        return any(pattern.match(content) for pattern in PATTERNS.values())

    def _strip_out_formatting(self, equation: str) -> str:
        """Remove LaTeX formatting commands from equation."""
        backslash_pos = equation.find("\\")
        while backslash_pos >= 0:
            x, end_pos = self.formatter.handle(
                equation[backslash_pos:], exclude_patterns=["spacing"]
            )
            if end_pos > 0:
                content = ""
                if x and isinstance(x.get("content", ""), str):
                    content = x.get("content")
                equation = (
                    equation[:backslash_pos]
                    + content
                    + equation[backslash_pos + end_pos :]
                )
            backslash_pos = equation.find("\\", backslash_pos + 1)
        return equation

    def _handle_labels(self, equation: str) -> Tuple[str, list[str]]:
        """Extract and remove labels from equation."""
        labels = []
        parsed_equation = equation

        label_matches = list(LABEL_PATTERN.finditer(equation))
        if not label_matches:
            return parsed_equation, labels

        for match in reversed(label_matches):
            start_pos = match.end() - 1
            label, end_pos = extract_nested_content(parsed_equation[start_pos:])
            if label:
                labels.append(label)
                parsed_equation = (
                    parsed_equation[: match.start()]
                    + parsed_equation[start_pos + end_pos :]
                )

        return parsed_equation.strip(), list(reversed(labels))

    def _get_equation_delimiter(self, pattern_name: str) -> Optional[str]:
        """Get the delimiter for a given pattern type."""
        delimiters = {
            "equation_display_$$": "$$",
            "equation_inline_$": "$",
            "equation_display_brackets": "\\]",
            "equation_inline_brackets": "\\)",
        }
        return delimiters.get(pattern_name)

    def _extract_contentcommands_as_placeholders(self, eq_token: Dict):
        math = eq_token["content"]

        blocks: Dict[str, Dict] = {}  # key: placeholder_str, value: token
        out_math = ""
        current_pos = 0

        while current_pos < len(math):
            if (
                match_start := self.content_command.search(math[current_pos:])
            ) is not None:
                # Copy text before the command
                if match_start > 0:
                    out_math += math[current_pos : current_pos + match_start]

                token, end_pos = self.content_command.handle(
                    math[current_pos + match_start :]
                )
                if token:
                    # store the token as placeholder
                    placeholder = f"___PLACEHOLDER_{len(blocks)}___"
                    blocks[placeholder] = token
                    out_math += placeholder

                if end_pos > 0:
                    current_pos += match_start + end_pos
                else:
                    current_pos += match_start + 1
            else:
                # Copy remaining text
                out_math += math[current_pos:]
                break

        eq_token["content"] = out_math
        if blocks:
            eq_token["placeholders"] = blocks
        return eq_token

    def handle(
        self, content: str, prev_token: Optional[Dict] = None
    ) -> Tuple[Optional[Dict], int]:
        """Handle equation content and return token."""

        for pattern_name, pattern in PATTERNS.items():
            match = pattern.match(content)
            if not match:
                continue

            equation = match.group(1).strip()
            end_pos = match.end()

            if not equation:
                return None, end_pos

            # Handle unbalanced braces for non-environment equations
            if not pattern_name in EQUATION_ENV and not check_delimiter_balance(
                equation
            ):
                delimiter = self._get_equation_delimiter(pattern_name)
                if not delimiter:
                    return None, 0

                equation, proper_end = extract_equation_content(
                    content[match.start() :], delimiter
                )
                if proper_end > 0:
                    end_pos = match.start() + proper_end

            # Process equation content
            equation, labels = self._handle_labels(equation)
            equation = convert_any_env_pairs_to_begin_end(equation)

            if self.process_content_fn:
                equation = self.process_content_fn(equation)

            equation = self._strip_out_formatting(equation)

            # Create token
            token = {
                "type": "equation",
                "content": equation,
                "display": (
                    "inline" if pattern_name.startswith("equation_inline") else "block"
                ),
            }

            if "align" in pattern_name or "eqnarray" in pattern_name:
                token["align"] = True

            if pattern_name in EQUATION_ENV:
                numbered = not match.group(0).strip().endswith("*}")
                if numbered:
                    token["numbered"] = True

            if labels:
                token["labels"] = labels

            if self.should_extract_content_placeholders:
                token = self._extract_contentcommands_as_placeholders(token)
            return token, end_pos

        return None, 0


if __name__ == "__main__":
    handler = EquationHandler()
    # print(handler.can_handle("$x^2$"))
    content = r"""
    $
    \begin{array}{c}
    \includegraphics[width=0.5\textwidth]{example-image}
    1+1=2, \mbox{as shown in \eqref{eq:sum}}
    \end{array}
    $
    """.strip()
    token, pos = handler.handle(content)
    print(token)
    print(content[pos:])
