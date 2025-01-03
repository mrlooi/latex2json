from collections import OrderedDict
import re
from typing import Callable, Dict, Optional, Tuple
from latex_parser.utils.tex_utils import extract_nested_content
from latex_parser.parser.patterns import LABEL_PATTERN
from latex_parser.parser.handlers.base import TokenHandler
from latex_parser.parser.handlers.environment import convert_any_env_pairs_to_begin_end

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

RAW_PATTERNS = OrderedDict(
    [
        ("equation_display_$$", re.compile(r"\$\$([\s\S]*?)\$\$", re.DOTALL)),
        ("equation_inline_$", re.compile(r"\$([^$]*)\$")),
        ("equation_display_brackets", re.compile(r"\\\[(.*?)\\\]", re.DOTALL)),
        ("equation_inline_brackets", re.compile(r"\\\((.*?)\\\)")),
    ]
)

# Add equation patterns dynamically
equation_env_dict = {
    name: rf"\\begin\s*\{{{name}\*?\}}(.*?)\\end\s*\{{{name}(?:\*)?\}}"
    for name in EQUATION_ENV
}

PATTERNS = OrderedDict(
    (key, re.compile(pattern, re.DOTALL)) for key, pattern in equation_env_dict.items()
)
PATTERNS.update(RAW_PATTERNS)


class EquationHandler(TokenHandler):

    def can_handle(self, content: str) -> bool:
        # Check each pattern individually
        return any(pattern.match(content) for pattern in PATTERNS.values())

    def _handle_labels(self, equation: str) -> Tuple[str, list[str]]:
        # Find all labels in the equation
        labels = []
        parsed_equation = equation

        # Find all label matches
        label_matches = list(LABEL_PATTERN.finditer(equation))

        # If no labels found, return original equation
        if not label_matches:
            return parsed_equation, labels

        # Extract labels and remove them from equation (reversed is used to maintain string indices)
        for match in reversed(label_matches):
            start_pos = match.end() - 1  # -1 to account for the opening '{'
            label, end_pos = extract_nested_content(parsed_equation[start_pos:])
            if label:
                labels.append(label)
                # Remove the entire \label{...} command
                parsed_equation = (
                    parsed_equation[: match.start()]
                    + parsed_equation[start_pos + end_pos :]
                )

        # Clean up any double spaces and trim
        parsed_equation = parsed_equation.strip()

        return parsed_equation, list(reversed(labels))

    def handle(
        self, content: str, prev_token: Optional[Dict] = None
    ) -> Tuple[Optional[Dict], int]:

        # Try each pattern until we find a match
        for pattern_name, pattern in PATTERNS.items():
            match = pattern.match(content)
            if match:
                equation = match.group(1).strip()
                if not equation:
                    return None, match.end()

                # Extract label if present
                equation, labels = self._handle_labels(equation)

                # convert any \aa \endaa pairs to \begin{aa} \end{aa} (to standardize)
                equation = convert_any_env_pairs_to_begin_end(equation)

                # Expand any commands in the equation
                if self.process_content_fn:
                    equation = self.process_content_fn(equation)

                # Create token
                inline = pattern_name.startswith("equation_inline")
                display = "inline" if inline else "block"
                # if inline:
                #     token = {
                #         "type": "text",
                #         "content": "$" + equation + "$ "
                #     }
                # else:
                token = {"type": "equation", "content": equation, "display": display}

                if "align" in pattern_name:
                    token["align"] = True

                if pattern_name in equation_env_dict:
                    numbered = not match.group(0).strip().endswith("*}")
                    if numbered:
                        token["numbered"] = True

                if labels:
                    token["labels"] = labels

                return token, match.end()

        return None, 0


if __name__ == "__main__":
    handler = EquationHandler()
    # print(handler.can_handle("$x^2$"))
    content = r"""
    \begin{equation*} 
    x^2 \label{eq:square} 
    E=mc^2 \label{eq:energy}
    \end{equation*}
    """.strip()
    token, pos = handler.handle(content)
    print(token)
    print(content[pos:])
