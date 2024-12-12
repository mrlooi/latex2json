from collections import OrderedDict
from typing import Callable, Dict, Optional, Tuple

import re

from src.handlers.base import TokenHandler
from src.tex_utils import extract_nested_content
from src.handlers.environment import (
    BaseEnvironmentHandler,
    find_pattern_while_skipping_nested_envs,
)

r"""
% Old Style        Modern Equivalent
{\tt text}         \texttt{text}      % Typewriter text
{\bf text}         \textbf{text}      % Bold face
{\it text}         \textit{text}      % Italic
{\sl text}         \textsl{text}      % Slanted
{\sc text}         \textsc{text}      % Small Caps
{\sf text}         \textsf{text}      % Sans serif
{\rm text}         \textrm{text}      % Roman (normal) text
{\cal text}        \mathcal{text}     % Calligraphic (only in math mode)

{\tiny text}       \texttiny{text}
{\small text}      \textsmall{text}
{\large text}      \textlarge{text}
{\huge text}       \texthuge{text}

{\em text}         \emph{text}        % Emphasized text
{\mit text}        \mathit{text}      % Math italic
{\bold text}       \textbf{text}      % Another bold variant
{\normalsize text} \textnormal{text}  % Normal size

{\footnotesize text}
{\scriptsize text}
{\Large text}      % Note capital L
{\LARGE text}
{\Huge text}       % Note capital H
"""

# Font style mappings
# NOTE: we IGNORE math mode ones
LEGACY_FONT_MAPPING: Dict[str, str] = {
    # Basic text style commands
    "tt": "texttt",
    "bf": "textbf",
    "it": "textit",
    "sl": "textsl",
    "sc": "textsc",
    "sf": "textsf",
    "rm": "textrm",
    "em": "emph",
    "bold": "textbf",
    # Font family declarations
    "rmfamily": "textrm",
    "sffamily": "textsf",
    "ttfamily": "texttt",
    # Font shape declarations
    "itshape": "textit",
    "scshape": "textsc",  # Added scshape
    "upshape": "textrm",  # Added upshape (upright shape)
    "slshape": "textsl",  # Added slshape (slanted shape)
    # Font series declarations
    "bfseries": "textbf",
    "mdseries": "textrm",  # Changed to textrm as it's the closest equivalent
    # Font combinations and resets
    "normalfont": "textrm",  # Changed to textrm as it's the closest equivalent
    # Additional text mode variants
    "textup": "textrm",
    "textnormal": "textrm",
    "textmd": "textrm",
    # math stuff (often used directly before math mode)
    "unboldmath": "textrm",
    "boldmath": "textbf",
    "mathversion{bold}": "textbf",
    "mathversion{normal}": "textrm",
}

# Size mappings
LEGACY_SIZE_MAPPING: Dict[str, str] = {
    # Basic size commands
    "tiny": "texttiny",
    "scriptsize": "textscriptsize",
    "footnotesize": "textfootnotesize",
    "small": "textsmall",
    "normalsize": "textnormal",
    "large": "textlarge",
    "Large": "textlarge",
    "LARGE": "textlarge",
    "huge": "texthuge",
    "Huge": "texthuge",
    # Additional size declarations
    "smaller": "textsmall",
    "larger": "textlarge",
}

# Old style patterns
# Generate regex patterns from the mappings
FONT_PATTERN = re.compile(
    r"\\(" + "|".join(LEGACY_FONT_MAPPING.keys()) + r")(?![a-zA-Z])\s*\{?"
)

SIZE_PATTERN = re.compile(
    r"\\(" + "|".join(LEGACY_SIZE_MAPPING.keys()) + r")(?![a-zA-Z])\s*\{?"
)

PATTERNS = {
    "font": FONT_PATTERN,
    "size": SIZE_PATTERN,
}


LEGACY_FORMAT_MAPPING: Dict[str, str] = {**LEGACY_FONT_MAPPING, **LEGACY_SIZE_MAPPING}

# negative lookbehind that ensures the preceding character is not a backslash
OPENING_BRACE_PATTERN = re.compile(r"(?<!\\)\{")


class LegacyFormattingHandler(TokenHandler):
    def can_handle(self, content: str) -> bool:
        return any(pattern.match(content) for pattern in PATTERNS.values())

    def handle(
        self, content: str, prev_token: Optional[Dict] = None
    ) -> Tuple[str, int]:
        for pattern_name, pattern in PATTERNS.items():
            match = pattern.match(content)

            if match:
                command = match.group(1)
                next_pos = match.end(0)
                modern_command = LEGACY_FORMAT_MAPPING.get(command)
                if not modern_command:
                    modern_command = command

                if match.group(0).endswith("{"):
                    # simple \tt{text}
                    text, end_pos = extract_nested_content("{" + content[next_pos:])
                    content_to_format = text.strip()
                    total_pos = next_pos + end_pos - 1
                else:
                    # Handle cases like
                    # \tt ... {...} ... }  # up to the closing brace
                    # \tt ... \bf ...  # next formatting i.e. \bf override
                    next_content = content[next_pos:]
                    end_pos = len(next_content)

                    # stop until appropriate nested closing brace
                    text, closing_pos = extract_nested_content("{" + next_content)
                    if text:
                        # -2 -> -1 for the extra opening brace, -1 for the final closing brace i.e. capture up to before the closing brace
                        end_pos = closing_pos - 2
                        next_content = next_content[:end_pos]

                    # check for similar patterns that aren't nested in braces

                    pattern_or_open_brace_pattern = re.compile(
                        pattern.pattern + "|" + OPENING_BRACE_PATTERN.pattern
                    )

                    pos = -1
                    while pos < len(next_content):
                        out_end_pos = find_pattern_while_skipping_nested_envs(
                            next_content, pattern_or_open_brace_pattern, max(pos, 0)
                        )
                        if out_end_pos != -1:
                            pos = out_end_pos
                            if pos < len(next_content) and next_content[pos] == "{":
                                _, skip_len = extract_nested_content(next_content[pos:])
                                pos += skip_len
                                continue
                            else:
                                # found same legacy pattern
                                break
                        else:
                            pos += 1

                    if pos != -1:
                        end_pos = pos

                    content_to_format = next_content[:end_pos]
                    total_pos = next_pos + end_pos

                formatted_text = rf"\{modern_command}" + "{" + content_to_format + "}"
                return formatted_text, total_pos

        return None, 0


if __name__ == "__main__":
    handler = LegacyFormattingHandler()

    # text = r" { \tt text} YOLO"
    # out, end_pos = handler.handle(text)
    # print(out)
    # print(text[end_pos:])

    text = r"\bf1 hello } ejje"  # } \noindent \tt"
    out, end_pos = handler.handle(text)
    print(out)
    print(text[end_pos:])
