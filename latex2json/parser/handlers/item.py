from typing import Callable, Dict, List, Optional, Tuple
import re
from latex2json.parser.handlers.environment import (
    BaseEnvironmentHandler,
    find_pattern_while_skipping_nested_envs,
)

# pattern to match \item up to the next \item or end of string
ITEM_PATTERN = re.compile(
    r"\\item\b\s*(?:\[(.*?)\])?\s*([\s\S]*?)(?=\\item\b|$)", re.DOTALL
)


class ItemHandler(BaseEnvironmentHandler):

    def can_handle(self, content: str) -> bool:
        return ITEM_PATTERN.match(content) is not None

    def handle(
        self, content: str, prev_token: Optional[Dict] = None
    ) -> Tuple[Optional[Dict], int]:
        match = ITEM_PATTERN.match(content)
        if match:
            end_of_item = match.group(2)
            end_pos = match.end()
            if end_of_item:
                # check to see and skip any nested environments that may contain inner \item
                start = match.start(2)
                out_end_pos = find_pattern_while_skipping_nested_envs(
                    content, ITEM_PATTERN, start_pos=start
                )
                if out_end_pos != -1:
                    end_pos = out_end_pos

                token = self._handle_environment("item", content[start:end_pos].strip())
                token["type"] = "item"
                del token["name"]
                if match.group(1):
                    token["title"] = match.group(1).strip()
                return token, end_pos

            return None, end_pos

        return None, 0


if __name__ == "__main__":
    item = ItemHandler()

    text = r"""
    \item 1
    \begin{itemize}
    \item
    2
    \end{itemize}
    \item
    3
    """.strip()
    out, pos = item.handle(text)
    print(out)
