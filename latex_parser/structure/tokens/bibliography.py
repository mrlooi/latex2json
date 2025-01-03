from enum import Enum
from typing import Dict, Any, List, Optional, Union

from pydantic import Field

from latex_parser.structure.tokens.base import EnvironmentToken, BaseToken
from latex_parser.structure.tokens.types import TokenType
from latex_parser.structure.tokens.tabular import TokenCreator


class BibItemToken(BaseToken):
    """Represents bibliography items"""

    type: TokenType = TokenType.BIBITEM
    cite_key: str
    title: Optional[str] = None


class BibliographyToken(EnvironmentToken):
    """Represents bibliography environment"""

    type: TokenType = TokenType.BIBLIOGRAPHY
    content: List[BibItemToken] = Field(default_factory=list)

    @classmethod
    def process(
        cls, data: Dict[str, Any], create_token: TokenCreator
    ) -> "BibliographyToken":
        """Process bibliography data, filtering for BibItemTokens only"""
        raw_content = data.get("content", [])
        processed_content: List[BibItemToken] = []

        for item in raw_content:
            if isinstance(item, dict) and item.get("type") == TokenType.BIBITEM:
                token = create_token(item)
                if isinstance(token, BibItemToken):
                    processed_content.append(token)

        return cls(content=processed_content)
