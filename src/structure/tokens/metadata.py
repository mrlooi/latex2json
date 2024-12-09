from typing import List, Optional
from src.structure.tokens.base import BaseToken, EnvironmentToken
from src.structure.tokens.types import TokenType


class AuthorToken(BaseToken):
    type: TokenType = TokenType.AUTHOR


class EmailToken(BaseToken):
    type: TokenType = TokenType.EMAIL
    content: str


class AffiliationToken(BaseToken):
    type: TokenType = TokenType.AFFILIATION
    content: str


class KeywordsToken(BaseToken):
    type: TokenType = TokenType.KEYWORDS
    content: str
