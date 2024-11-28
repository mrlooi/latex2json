from collections import OrderedDict
from typing import Callable, Dict, Optional, Tuple

import re

from src.handlers.base import TokenHandler
from src.tex_utils import extract_nested_content

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
LEGACY_FONT_MAPPING: Dict[str, str] = {
    "tt": "texttt",
    "bf": "textbf",
    "it": "textit",
    "sl": "textsl",
    "sc": "textsc",
    "sf": "textsf",
    "rm": "textrm",
    "cal": "mathcal",
    "em": "emph",
    "mit": "mathit",
    "bold": "textbf",
}

# Size mappings
LEGACY_SIZE_MAPPING: Dict[str, str] = {
    "tiny": "texttiny",
    "small": "textsmall",
    "large": "textlarge",
    "Large": "textlarge",
    "LARGE": "textlarge",
    "huge": "texthuge",
    "Huge": "texthuge",
    "normalsize": "textnormal",
    "footnotesize": "textfootnotesize",
    "scriptsize": "textscriptsize",
}

# Old style patterns
# Generate regex patterns from the mappings
FONT_PATTERN = re.compile(
    r"\\(" + "|".join(LEGACY_FONT_MAPPING.keys()) + r")\b\s*\{?", re.DOTALL
)

SIZE_PATTERN = re.compile(
    r"\\(" + "|".join(LEGACY_SIZE_MAPPING.keys()) + r")\b\s*\{?", re.DOTALL
)

PATTERNS = {
    "font": FONT_PATTERN,
    "size": SIZE_PATTERN,
}


LEGACY_FORMAT_MAPPING: Dict[str, str] = {**LEGACY_FONT_MAPPING, **LEGACY_SIZE_MAPPING}


class LegacyFormattingHandler(TokenHandler):
    def can_handle(self, content: str) -> bool:
        return any(pattern.match(content) for pattern in PATTERNS.values())

    def handle(self, content: str) -> Tuple[str, int]:
        for pattern_name, pattern in PATTERNS.items():
            match = pattern.match(content)

            if match:
                command = match.group(1)
                next_pos = match.end(0)
                modern_command = LEGACY_FORMAT_MAPPING.get(command)
                if not modern_command:
                    modern_command = command
                if match.group(0).endswith("{"):
                    text, end_pos = extract_nested_content("{" + content[next_pos:])
                    content_to_format = text.strip()
                    total_pos = next_pos + end_pos - 1
                else:
                    next_content = content[next_pos:]
                    end_pos = len(next_content)

                    # stop until appropriate nested closing brace
                    text, closing_pos = extract_nested_content("{" + next_content)
                    if text:
                        # -2 -> -1 for the extra opening brace, -1 for the final closing brace i.e. capture up to before the closing brace
                        end_pos = closing_pos - 2
                        next_content = next_content[:end_pos]

                    # check for similar patterns
                    match = pattern.search(next_content)
                    if match:
                        # if match, we end before this next pattern
                        end_pos = match.start()
                        next_content = next_content[:end_pos]

                    content_to_format = next_content
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

    text = r"\bf Hello my name isssdas {sa} asdsd \tiny asdad"  # } \noindent \tt"
    out, end_pos = handler.handle(text)
    print(out)
    print(text[end_pos:])
