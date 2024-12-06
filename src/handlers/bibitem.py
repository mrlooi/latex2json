from typing import Callable, Dict, List, Optional, Tuple
import re

from src.handlers.base import TokenHandler

BIBITEM_PATTERN = re.compile(
    r"\\bibitem\s*(?:\[(.*?)\])?\{(.*?)\}\s*([\s\S]*?)(?=\\bibitem|$)", re.DOTALL
)
NEWBLOCK_PATTERN = re.compile(r"\\newblock\b")


class BibItemHandler(TokenHandler):

    def can_handle(self, content: str) -> bool:
        return BIBITEM_PATTERN.match(content) is not None

    def handle(
        self, content: str, prev_token: Optional[Dict] = None
    ) -> Tuple[Optional[Dict], int]:
        match = BIBITEM_PATTERN.match(content)
        if match:
            item = match.group(3).strip()
            if item:
                # remove newblock
                item = NEWBLOCK_PATTERN.sub("", item)
                token = {
                    "type": "bibitem",
                    "content": item,
                    "cite_key": match.group(2).strip(),
                }
                if match.group(1):
                    token["label"] = match.group(1).strip()
                return token, match.end()

            return None, match.end()

        return None, 0


if __name__ == "__main__":
    item = BibItemHandler()

    text = r"""
    \bibitem {sdsss}
    asdasdasas
    """.strip()
    print(item.handle(text))

    text = r"""
\bibitem[sss]{KanekoHoki11}
Tomoyuki Kaneko and Kunihito Hoki.
\newblock Analysis of evaluation-function learning by comparison of sibling
  nodes.
\newblock In {\em Advances in Computer Games - 13th International Conference,
  {ACG} 2011, Tilburg, The Netherlands, November 20-22, 2011, Revised Selected
  Papers}, pages 158--169, 2011.

  \bibitem{asdsa}
  Hi there
  sadss
""".strip()
    print(item.handle(text))
