from typing import List, Optional
from latex_parser.structure.tokens.base import BaseToken, EnvironmentToken
from latex_parser.structure.tokens.types import TokenType


class DocumentToken(BaseToken):
    type: TokenType = TokenType.DOCUMENT


class TitleToken(BaseToken):
    type: TokenType = TokenType.TITLE
    title: List[BaseToken]
    content: Optional[str] = None


class SectionToken(BaseToken):
    type: TokenType = TokenType.SECTION
    title: List[BaseToken]
    level: int
    numbering: Optional[str] = None  # e.g. 3.1.2
    labels: Optional[List[str]] = None
    content: Optional[List[BaseToken]] = []


class ParagraphToken(SectionToken):
    type: TokenType = TokenType.PARAGRAPH


class AbstractToken(EnvironmentToken):
    type: TokenType = TokenType.ABSTRACT


class AppendixToken(BaseToken):
    type: TokenType = TokenType.APPENDIX
    # if \appendix, then content is empty
    # if \begin{appendices}, then content is the content inside the appendices env
    content: Optional[List[BaseToken]] = []
