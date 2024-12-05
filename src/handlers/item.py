from typing import Callable, Dict, List, Optional, Tuple
import re
from src.handlers.environment import BaseEnvironmentHandler

ITEM_PATTERN = re.compile(
    r"\\item\b\s*(?:\[(.*?)\])?\s*([\s\S]*?)(?=\\item\b|$)", re.DOTALL
)


class ItemHandler(BaseEnvironmentHandler):

    def can_handle(self, content: str) -> bool:
        return ITEM_PATTERN.match(content) is not None

    def handle(self, content: str) -> Tuple[Optional[Dict], int]:
        match = ITEM_PATTERN.match(content)
        if match:
            item = match.group(2)
            end_pos = match.end()
            if item:
                start = match.start(2)
                # search for inner environments
                current_pos = start

                while True:
                    next_item = ITEM_PATTERN.search(content[current_pos:])
                    if not next_item:
                        end_pos = len(content)
                        break

                    # check for nested inner envs
                    env_match = self.search(content[current_pos:])
                    if not env_match:
                        break

                    pos = env_match.start()
                    # If we find a nested environment after the next item,
                    # we can safely exit
                    if next_item and pos > next_item.start():
                        end_pos = current_pos + next_item.start()
                        break

                    # Handle the inner environment
                    inner_token, inner_length = super().handle(
                        content[current_pos + pos :]
                    )
                    if not inner_token:  # should not happen..
                        break

                    current_pos += pos + inner_length
                    end_pos = current_pos

                token = self._handle_environment("item", content[start:end_pos].strip())
                token["type"] = "item"
                if match.group(1):
                    token["label"] = match.group(1).strip()
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
