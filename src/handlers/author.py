from typing import Callable, Dict, List, Optional, Tuple
import re

from src.handlers.base import TokenHandler
from src.tex_utils import extract_nested_content

AND_PATTERN = re.compile(r"\\and\b", re.IGNORECASE)
BACKSLASH_PATTERN = re.compile(r"\\\\")

compile_as = re.DOTALL | re.IGNORECASE

PATTERNS = {
    "author": re.compile(r"\\author(?:\s*\[(.*?)\])?\s*{", compile_as),
    "email": re.compile(r"\\email\s*{", compile_as),
    "affiliation": re.compile(r"\\affiliation\s*{", compile_as),
    "address": re.compile(r"\\address\s*{", compile_as),
    # \thanks usually found inside author block
    "thanks": re.compile(r"\\thanks\s*{", compile_as),
    "samethanks": re.compile(r"\\samethanks\b", compile_as),
}


class AuthorHandler(TokenHandler):

    last_thanks_token = None

    def clear(self):
        self.last_thanks_token = None

    def can_handle(self, content: str) -> bool:
        for pattern in PATTERNS.values():
            if pattern.match(content):
                return True
        return False

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

    def handle(
        self, content: str, prev_token: Optional[Dict] = None
    ) -> Tuple[Optional[Dict], int]:
        for name, pattern in PATTERNS.items():
            match = pattern.match(content)
            if match:
                if name == "samethanks":
                    if self.last_thanks_token:
                        return self.last_thanks_token, match.end()
                    return {"type": "samethanks"}, match.end()
                elif name == "thanks":
                    start_pos = match.end() - 1
                    content, end_pos = extract_nested_content(content[start_pos:])
                    token = {
                        "type": "footnote",
                        "content": content,
                    }
                    self.last_thanks_token = token
                    return token, start_pos + end_pos
                elif name == "author":
                    # short_author = match.group(1)  # Will be None if no [] present
                    start_pos = match.end() - 1
                    author_content, end_pos = extract_nested_content(
                        content[start_pos:]
                    )

                    tokens = self._parse_author_content(author_content)
                    if self.process_content_fn:
                        parsed_tokens = []
                        for token in tokens:
                            processed = self.process_content_fn(token)
                            if processed:
                                parsed_tokens.append(processed)
                        tokens = parsed_tokens

                    return {
                        "type": "author",
                        "content": tokens,
                    }, start_pos + end_pos
                else:
                    start_pos = match.end() - 1
                    content, end_pos = extract_nested_content(content[start_pos:])
                    if self.process_content_fn:
                        content = self.process_content_fn(content)

                    token = {
                        "type": name,
                        "content": content,
                    }
                    return token, start_pos + end_pos

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
