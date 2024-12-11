from typing import Callable, Dict, List, Optional, Tuple
import re
from src.handlers.environment import BaseEnvironmentHandler

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
            item = match.group(2)
            end_pos = match.end()
            if item:
                start = match.start(2)
                current_pos = start

                # search for inner environments with \item so that we can handle nested items
                next_item = ITEM_PATTERN.search(content[current_pos:])
                while next_item:
                    # check for nested inner envs (since those are the ones that could contain inner \item)
                    env_match = self.search(content[current_pos:])
                    if not env_match:
                        end_pos = current_pos + next_item.start()
                        break

                    start_env = env_match.start()
                    # If we find a nested environment after the next item,
                    # we can safely exit
                    if start_env > next_item.start():
                        end_pos = current_pos + next_item.start()
                        break

                    # Handle and skip the inner environment
                    inner_token, inner_length = super().handle(
                        content[current_pos + start_env :]
                    )
                    if not inner_token:  # should not happen..
                        break

                    current_pos += start_env + inner_length
                    end_pos = current_pos

                    next_item = ITEM_PATTERN.search(content[current_pos:])

                token = self._handle_environment("item", content[start:end_pos].strip())
                token["type"] = "item"
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
