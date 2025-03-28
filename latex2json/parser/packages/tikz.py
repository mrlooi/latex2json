import re
from typing import Callable, Dict, List, Optional, Tuple

from latex2json.parser.handlers.base import TokenHandler
from latex2json.parser.handlers.environment import (
    find_pattern_while_skipping_nested_envs,
)
from latex2json.utils.tex_utils import (
    extract_args,
    find_matching_env_block,
    extract_nested_content,
)

# TODO: all the tikz stuff...

TIKZ_USING_PATTERN = re.compile(r"\\usetikzlibrary\s*{")

PATTERNS = {
    "usetikzlibrary": TIKZ_USING_PATTERN,
}


class TikzHandler(TokenHandler):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def can_handle(self, content: str) -> bool:
        return any(pattern.match(content) for pattern in PATTERNS.values())

    def handle(
        self, content: str, prev_token: Optional[Dict] = None
    ) -> Tuple[Optional[Dict], int]:
        for pattern_name, pattern in PATTERNS.items():
            match = pattern.match(content)
            if match:
                # If a \usetikzlibrary command is found, just ignore it
                if pattern_name == "usetikzlibrary":
                    start_pos = match.end() - 1
                    content, end_pos = extract_nested_content(content[start_pos:])
                    return None, start_pos + end_pos
                return None, match.end()
        return None, 0


if __name__ == "__main__":
    text = r"""
\usetikzlibrary{matrix, patterns}
""".strip()

    handler = TikzHandler()
    out, end_pos = handler.handle(text)
    print(out)
    print(text[end_pos:])
