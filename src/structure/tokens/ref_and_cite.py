from enum import Enum
from typing import Optional

from src.structure.tokens.base import BaseToken
from src.structure.tokens.types import TokenType


class CitationToken(BaseToken):
    """Represents citations"""

    type: TokenType = TokenType.CITATION
    title: Optional[str] = None
    content: str


class ReferenceToken(BaseToken):
    """Represents references"""

    type: TokenType = TokenType.REF
    title: Optional[str] = None
    content: str


class UrlToken(BaseToken):
    """Represents URLs and hyperlinks"""

    type: TokenType = TokenType.URL
    title: Optional[str] = None
    content: str


class FootnoteToken(BaseToken):
    type: TokenType = TokenType.FOOTNOTE
