from typing import List, Optional
from latex2json.structure.tokens.base import BaseToken, EnvironmentToken
from latex2json.structure.tokens.types import TokenType


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
    content: Optional[List[BaseToken]] = []

    def model_dump(self, **kwargs):
        result = super().model_dump(**kwargs)

        if self.title:
            result["title"] = [
                self.serialize_value(token, **kwargs) for token in self.title
            ]

        return result


class ParagraphToken(SectionToken):
    type: TokenType = TokenType.PARAGRAPH


class AbstractToken(EnvironmentToken):
    type: TokenType = TokenType.ABSTRACT


class AppendixToken(BaseToken):
    type: TokenType = TokenType.APPENDIX
    content: List[BaseToken] = []
