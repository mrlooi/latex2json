from collections import OrderedDict
from typing import Callable, Dict, Optional, Tuple

import re

from src.handlers.base import TokenHandler

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

# Old style to modern LaTeX command mappings
LEGACY_FORMAT_MAPPING: Dict[str, str] = {
    'tt': 'texttt',
    'bf': 'textbf',
    'it': 'textit',
    'sl': 'textsl',
    'sc': 'textsc',
    'sf': 'textsf',
    'rm': 'textrm',
    'cal': 'mathcal',
    'tiny': 'texttiny',
    'small': 'textsmall',
    'large': 'textlarge',
    'Large': 'textlarge',
    'LARGE': 'textlarge',
    'huge': 'texthuge',
    'Huge': 'texthuge',
    'em': 'emph',
    'mit': 'mathit',
    'bold': 'textbf',
    'normalsize': 'textnormal',
    'footnotesize': 'textfootnotesize',
    'scriptsize': 'textscriptsize',
}


# Old style patterns
LEGACY_PATTERNS = re.compile(r'(\s*){[\s\\]*('
        r'tt|bf|it|sl|sc|sf|rm|cal|'  # Basic formatting
        r'tiny|small|large|huge|'      # Size commands
        r'em|mit|bold|normalsize|'     # Other formatting
        r'footnotesize|scriptsize|'    # More sizes
        r'Large|LARGE|Huge'            # Capital variants
        r')\s*([^}]+)}', re.DOTALL)

class LegacyFormattingHandler(TokenHandler):
    def can_handle(self, content: str) -> bool:
        return LEGACY_PATTERNS.match(content) is not None
    
    def handle(self, content: str) -> Tuple[Optional[Dict], int]:
        match = LEGACY_PATTERNS.match(content)
        if match:
            # Extract the whitespace, command and text
            whitespace = match.group(1)
            command = match.group(2).strip()
            text = match.group(3).strip()
            
            # Convert to modern format, preserving leading whitespace
            modern_command = LEGACY_FORMAT_MAPPING.get(command)
            if modern_command:
                output = {
                    'type': 'command',
                    'content': whitespace + r'\\' + modern_command + '{' + text + '}'
                }
            else:
                output = {
                    'type': 'text',
                    'content': match.group(0)
                }
            return output, match.end()
        
        return None, 0

if __name__ == "__main__":
    handler = LegacyFormattingHandler()

    # text = r" { \tt text} YOLO"
    # out, end_pos = handler.handle(text)
    # print(out)
    # print(text[end_pos:])

    print(handler.handle(r"{\large text}"))
