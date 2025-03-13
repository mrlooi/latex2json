from enum import Enum
from typing import List, Optional

from pydantic import Field

from latex2json.structure.tokens.base import BaseToken, EnvironmentToken
from latex2json.structure.tokens.types import TokenType


class CodeToken(BaseToken):
    """Represents verbatim/lstlisting code blocks"""

    type: TokenType = TokenType.CODE
    title: Optional[str] = None
    content: str
    display: Optional[str] = None


# Algorithms
class AlgorithmToken(EnvironmentToken):
    """Represents algorithm environment"""

    type: TokenType = TokenType.ALGORITHM
    content: List[BaseToken] = Field(default_factory=list)
    numbering: Optional[str] = None


class AlgorithmicToken(BaseToken):
    """Represents algorithmic tokens"""

    type: TokenType = TokenType.ALGORITHMIC
    content: str
