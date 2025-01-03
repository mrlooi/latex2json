from collections import OrderedDict
from typing import Dict, List, Optional, Tuple
import re

from latex_parser.parser.handlers.base import TokenHandler
from latex_parser.utils.tex_utils import extract_nested_content_sequence_blocks


# ordered dict so that ifthenelse/ifnum etc is matched before general if
PATTERNS = OrderedDict(
    {
        "forloop": re.compile(r"\\forloop\s*\{"),
        "foreach": re.compile(r"\\foreach\s+.+\s*\{"),
    }
)


class ForLoopHandler(TokenHandler):

    def can_handle(self, content: str) -> bool:
        return any(pattern.match(content) for _, pattern in PATTERNS.items())

    def handle(
        self, content: str, prev_token: Optional[Dict] = None
    ) -> Tuple[Optional[Dict], int]:
        for name, pattern in PATTERNS.items():
            match = pattern.match(content)
            if match:
                max_blocks = 4 if name == "forloop" else 2
                start_pos = match.end() - 1  # -1 to exclude the opening brace
                blocks, end_pos = extract_nested_content_sequence_blocks(
                    content[start_pos:], "{", "}", max_blocks=max_blocks
                )
                # skip entirely?
                return None, start_pos + end_pos
        return None, 0


if __name__ == "__main__":
    text = r"""
    \foreach \x in {0,...,4}{
    \draw (3*\x,10)--++(0,-0.2);
    \foreach \j in {1,...,4}
        \draw[draw=blue] ({3*(\x+\j/5)},10)--++(0,-0.2);
}

\foreach \x [count = \xi] in {a,...,c,f,...,z}
{\node at (\xi,0) {$\x$};}
""".strip()

    handler = ForLoopHandler()
    print(handler.handle(text))
