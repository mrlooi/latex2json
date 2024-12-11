from typing import List, Optional
from src.structure.tokens.base import BaseToken, EnvironmentToken
from src.structure.tokens.types import TokenType


class AuthorToken(BaseToken):
    type: TokenType = TokenType.AUTHOR
    content: List[
        List[BaseToken]
    ]  # each row is an author, where each author -> List[BaseToken]


class EmailToken(BaseToken):
    type: TokenType = TokenType.EMAIL
    content: str | List[BaseToken]


class AffiliationToken(BaseToken):
    type: TokenType = TokenType.AFFILIATION
    content: str | List[BaseToken]


class AddressToken(BaseToken):
    type: TokenType = TokenType.ADDRESS
    content: str | List[BaseToken]


class KeywordsToken(BaseToken):
    type: TokenType = TokenType.KEYWORDS
    content: str | List[BaseToken]
