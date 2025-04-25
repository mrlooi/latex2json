from enum import Enum
from typing import Dict, Any, List, Optional, Union

from pydantic import BaseModel, Field

from latex2json.structure.tokens.base import EnvironmentToken, BaseToken, TokenCreator
from latex2json.structure.tokens.types import TokenType


class BibItemToken(BaseToken):
    """Represents bibliography items"""

    type: TokenType = TokenType.BIBITEM
    format: str = "bibitem"
    cite_key: str
    content: Union[str, List[BaseToken]]
    label: Optional[str] = None

    fields: Optional[Dict[str, str]] = (
        None  # e.g. author=John Doe, year=2021, title=xxx
    )


class BibliographyToken(BaseToken):
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
