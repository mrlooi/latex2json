from enum import Enum
from typing import Dict, Any, List, Optional, Union

from pydantic import Field

from src.structure.tokens.base import EnvironmentToken, BaseToken
from src.structure.tokens.types import TokenType


class BibItemToken(BaseToken):
    """Represents bibliography items"""

    type: TokenType = TokenType.BIBITEM
    cite_key: str


class BibliographyToken(EnvironmentToken):
    """Represents bibliography environment"""

    type: TokenType = TokenType.BIBLIOGRAPHY
    content: List[BibItemToken] = Field(default_factory=list)
