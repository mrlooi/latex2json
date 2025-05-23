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

USE_LIB_PATTERN = re.compile(r"\\use(tikz|pgf|pgfplots)library\s*{")

PATTERNS = {
    "uselibrary": USE_LIB_PATTERN,
    "begin_picture": re.compile(r"\\begin\s*\{(tikzpicture|picture|pgfpicture)\}"),
    "pgfplotsset": re.compile(r"\\pgfplotsset\s*{"),
}


class TikzPGFHandler(TokenHandler):
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
                # If a \uselibrary command is found, just ignore it
                if pattern_name == "uselibrary":
                    start_pos = match.end() - 1
                    content, end_pos = extract_nested_content(content[start_pos:])
                    return None, start_pos + end_pos
                elif pattern_name == "pgfplotsset":
                    start_pos = match.end() - 1
                    content, end_pos = extract_nested_content(content[start_pos:])
                    return None, start_pos + end_pos
                elif pattern_name == "begin_picture":
                    env_name = match.group(1)
                    start_pos, end_pos, inner_content = find_matching_env_block(
                        content, env_name
                    )
                    return {
                        "type": "diagram",
                        "name": env_name,
                        "content": inner_content,
                    }, end_pos
                return None, match.end()
        return None, 0


if __name__ == "__main__":
    text = r"""
\begin{tikzpicture}
    \draw (0,0) -- (1,1);
    \draw (0,0) -- (1,1);
\end{tikzpicture}
POST
""".strip()

    handler = TikzPGFHandler()
    out, end_pos = handler.handle(text)
    print(out)
    print(text[end_pos:])
