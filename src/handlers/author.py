from typing import Callable, Dict, List, Optional, Tuple
import re

from src.handlers.base import TokenHandler
from src.tex_utils import extract_nested_content


AUTHOR_PATTERN = re.compile(r"\\[Aa]uthor(?:\s*\[(.*?)\])?\s*{", re.DOTALL)
AND_PATTERN = re.compile(r"\\and\b", re.IGNORECASE)
BACKSLASH_PATTERN = re.compile(r"\\\\")


class AuthorHandler(TokenHandler):

    def can_handle(self, content: str) -> bool:
        return AUTHOR_PATTERN.match(content) is not None

    def _parse_author_content(self, content: str) -> Tuple[List[str], int]:
        authors = []
        # First split by \and
        and_parts = AND_PATTERN.split(content)

        # Then process each part for possible \\ separators
        for part in and_parts:
            # Split by \\ and filter out empty strings
            # backslash_parts = [p.strip() for p in BACKSLASH_PATTERN.split(part)]
            part = part.strip()
            if part:
                authors.append(part)

        return authors

    def handle(self, content: str) -> Tuple[Optional[Dict], int]:
        match = AUTHOR_PATTERN.match(content)
        if match:
            # short_author = match.group(1)  # Will be None if no [] present
            start_pos = match.end() - 1
            author_content, end_pos = extract_nested_content(content[start_pos:])

            return {
                "type": "author",
                "content": self._parse_author_content(author_content),
            }, start_pos + end_pos

        return None, 0


if __name__ == "__main__":
    item = AuthorHandler()

    text = r"""
\author{
  \AND
  Ashish Vaswani\thanks{Equal contribution.} \\
  Google Brain\\
  \texttt{avaswani@google.com}\\
  \And
  Noam Shazeer\footnotemark[1]\\
  Google Brain\\
  noam@google.com\\
}

after authors
    """.strip()

    print(item.handle(text))
