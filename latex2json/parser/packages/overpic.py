import re
from typing import Callable, Dict, List, Optional, Tuple

from latex2json.parser.handlers.base import TokenHandler
from latex2json.parser.handlers.environment import (
    find_pattern_while_skipping_nested_envs,
)
from latex2json.utils.tex_utils import extract_args, find_matching_env_block


OVERPIC_PATTERN_START = re.compile(r"\\begin\s*\{overpic\}")
OVERPIC_PATTERN_END = re.compile(r"\\end\s*\{overpic\}")


class OverpicHandler(TokenHandler):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def can_handle(self, content: str) -> bool:
        return OVERPIC_PATTERN_START.match(content) is not None

    def handle(
        self, content: str, prev_token: Optional[Dict] = None
    ) -> Tuple[Optional[Dict], int]:
        match = OVERPIC_PATTERN_START.match(content)
        if not match:
            return None, 0

        start_pos, end_pos, env_content = find_matching_env_block(content, "overpic")

        args, _ = extract_args(env_content, 1, 1)
        if args["req"]:
            file_name = args["req"][0]
            token = {
                "type": "includegraphics",
                "content": file_name,
            }

            # TODO: deal with env_content overlay?

            return token, end_pos

        return None, end_pos


if __name__ == "__main__":
    text = r"""
\begin{overpic}[width=0.5\textwidth]{example-image}
\end{overpic} POST
""".strip()

    handler = OverpicHandler()
    out, end_pos = handler.handle(text)
    print(out)
    print(text[end_pos:])
