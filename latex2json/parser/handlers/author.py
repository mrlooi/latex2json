from typing import Callable, Dict, List, Optional, Tuple
import re

from latex2json.parser.handlers.base import TokenHandler
from latex2json.utils.tex_utils import extract_nested_content

AND_PATTERN = re.compile(r"\\and\b", re.IGNORECASE)
BACKSLASH_PATTERN = re.compile(r"\\\\")

compile_as = re.DOTALL | re.IGNORECASE

PATTERNS = {
    "author": re.compile(r"\\author(?:\s*\[(.*?)\])?\s*{", compile_as),
    # "correspondingauthor": re.compile(r"\\correspondingauthor\s*{", compile_as),
    "email": re.compile(r"\\email\s*{", compile_as),
    "affiliation": re.compile(
        r"\\(?:affil|affiliation)(?:\s*\[(.*?)\])?\s*{", compile_as
    ),
    "address": re.compile(r"\\address\s*{", compile_as),
    "curraddr": re.compile(r"\\curraddr(?:\{\}|\b)"),
    # \thanks usually found inside author block
    "thanks": re.compile(r"\\thanks\s*{", compile_as),
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

    def _parse_author_tokens(self, content: str) -> Tuple[Optional[Dict], int]:
        # short_author = match.group(1)  # Will be None if no [] present
        tokens = self._parse_author_content(content)
        if self.process_content_fn:
            parsed_tokens = []
            for token in tokens:
                processed = self.process_content_fn(token)
                if processed:
                    parsed_tokens.append(processed)
            tokens = parsed_tokens
        return tokens

    def handle(
        self, content: str, prev_token: Optional[Dict] = None
    ) -> Tuple[Optional[Dict], int]:
        for name, pattern in PATTERNS.items():
            match = pattern.match(content)
            if match:
                start_pos = match.end() - 1
                content, end_pos = extract_nested_content(content[start_pos:])
                total_pos = start_pos + end_pos

                if name == "thanks":
                    token = {
                        "type": "footnote",
                        "content": content,
                    }
                    self.last_thanks_token = token
                    return token, total_pos
                elif name == "author":
                    # short_author = match.group(1)  # Will be None if no [] present
                    tokens = self._parse_author_tokens(content)

                    return {
                        "type": "author",
                        "content": tokens,
                    }, total_pos
                elif name == "curraddr":
                    return None, match.end()
                else:
                    if self.process_content_fn:
                        content = self.process_content_fn(content)

                    token = {
                        "type": name,
                        "content": content,
                    }
                    return token, total_pos

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
