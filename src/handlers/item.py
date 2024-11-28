from typing import Callable, Dict, List, Optional, Tuple
import re
from src.handlers.environment import BaseEnvironmentHandler

ITEM_PATTERN = re.compile(r"\\item(?:\[(.*?)\])?\s*([\s\S]*?)(?=\\item|$)", re.DOTALL)


class ItemHandler(BaseEnvironmentHandler):

    def can_handle(self, content: str) -> bool:
        return ITEM_PATTERN.match(content) is not None

    def handle(self, content: str) -> Tuple[Optional[Dict], int]:
        match = ITEM_PATTERN.match(content)
        if match:
            item = match.group(2).strip()
            if item:
                token = self._handle_environment("item", item)
                token["type"] = "item"
                if match.group(1):
                    token["label"] = match.group(1).strip()
                return token, match.end()

            return None, match.end()

        return None, 0


if __name__ == "__main__":
    item = ItemHandler()
    print(item.handle(r"\item[hello] content"))
    print(item.handle(r"\item MAMA"))
