from typing import List, Optional
from src.structure.tokens.base import BaseToken, EnvironmentToken
from src.structure.tokens.types import TokenType


class DocumentToken(EnvironmentToken):
    type: TokenType = TokenType.DOCUMENT


class SectionToken(BaseToken):
    type: TokenType = TokenType.SECTION
    title: str
    labels: Optional[List[str]] = None
    content: Optional[str] = None


class TitleToken(BaseToken):
    type: TokenType = TokenType.TITLE
    content: str


class AbstractToken(EnvironmentToken):
    type: TokenType = TokenType.ABSTRACT


class AppendixToken(BaseToken):
    """Appendix token i.e. \appendix. Not an environment"""

    type: TokenType = TokenType.APPENDIX
    content: Optional[str] = None
