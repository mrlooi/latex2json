from enum import Enum
from typing import List, Optional

from latex2json.structure.tokens.base import BaseToken
from latex2json.structure.tokens.types import TokenType


class CitationToken(BaseToken):
    """Represents citations"""

    type: TokenType = TokenType.CITATION
    title: Optional[str] = None
    content: str


class ReferenceToken(BaseToken):
    """Represents references"""

    type: TokenType = TokenType.REF
    title: Optional[List[BaseToken]] = None
    content: List[str]


class UrlToken(BaseToken):
    """Represents URLs and hyperlinks"""

    type: TokenType = TokenType.URL
    title: Optional[str | List[BaseToken]] = None
    content: str


class FootnoteToken(BaseToken):
    type: TokenType = TokenType.FOOTNOTE
    content: List[BaseToken]
