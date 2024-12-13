from enum import Enum
from typing import List, Optional

from pydantic import Field

from src.structure.tokens.base import BaseToken, EnvironmentToken
from src.structure.tokens.types import TokenType


class CodeToken(BaseToken):
    """Represents verbatim/lstlisting code blocks"""

    type: TokenType = TokenType.CODE
    title: Optional[str] = None
    content: str


# Algorithms
class AlgorithmToken(EnvironmentToken):
    """Represents algorithm environment"""

    type: TokenType = TokenType.ALGORITHM
    content: List[BaseToken] = Field(default_factory=list)


class AlgorithmicToken(BaseToken):
    """Represents algorithmic tokens"""

    type: TokenType = TokenType.ALGORITHMIC
    content: str
