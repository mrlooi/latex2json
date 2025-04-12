import re
from typing import Callable, Dict, List, Optional, Tuple

from latex2json.parser.handlers.base import TokenHandler

from latex2json.parser.patterns import OPTIONAL_BRACE_PATTERN, BRACE_CONTENT_PATTERN
from latex2json.parser.handlers.environment import (
    find_pattern_while_skipping_nested_envs,
)
from latex2json.utils.tex_utils import extract_delimited_args

r"""
\titleformat{<command>}[<shape>]{<format>}{<label>}{<sep>}{<before-code>}
\titlespacing*{<command>}{<left>}{<before-sep>}{<after-sep>}
\titlelabel{<format>}
\titleclass{<newcmd>}{<shape>}[<parentcmd>]
\titlecontents{<section>}
  [<left>]{<above-code>}
  {<label>}
  {<before-label>}
  {<after-label>}
\titleline[c]{\titlerule}
"""

PATTERNS = {
    "titleformat": re.compile(r"\\titleformat\s*{", re.DOTALL),
    "titlespacing": re.compile(r"\\titlespacing\*?\s*{", re.DOTALL),
    "titlelabel": re.compile(r"\\titlelabel\s*{", re.DOTALL),
    "titlecontents": re.compile(r"\\titlecontents\s*{", re.DOTALL),
    "titleline": re.compile(
        r"\\titleline\s*%s\s*{" % (OPTIONAL_BRACE_PATTERN), re.DOTALL
    ),
    # "titleclass": re.compile(r"\\titleclass\s*{", re.DOTALL), # TODO: newcommand?
}

DELIMITERS = {
    "titleformat": "{[" + "{" * 4,
    "titlespacing": "{" * 4,
    "titlelabel": "{",
    "titleclass": "{{[",
    "titlecontents": "{[" + "{" * 4,
    "titleline": "{",
}


class TitlesecHandler(TokenHandler):
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
                start_pos = match.end() - 1
                delimiters = DELIMITERS.get(pattern_name)
                if delimiters:
                    # ignore?
                    args, end_pos = extract_delimited_args(
                        content[start_pos:], delimiters
                    )
                    return None, start_pos + end_pos
                return None, start_pos
        return None, 0


if __name__ == "__main__":
    text = r"""
\titlespacing*{\paragraph}
{0pt}{3.25ex plus 1ex minus .2ex}{1.5ex plus .2ex} POST
""".strip()

    handler = TitlesecHandler()
    out, end_pos = handler.handle(text)
    print(out)
    print(text[end_pos:])
