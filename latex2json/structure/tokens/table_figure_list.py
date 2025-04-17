from enum import Enum
from typing import Dict, Any, List, Optional, TypedDict, Union

from pydantic import BaseModel, Field
from latex2json.structure.tokens.base import BaseToken, EnvironmentToken
from latex2json.structure.tokens.types import TokenType


# FIGURE
class FigureToken(BaseToken):
    """Represents figures"""

    type: TokenType = TokenType.FIGURE
    numbering: Optional[str] = None


class SubFigureToken(BaseToken):
    type: TokenType = TokenType.SUBFIGURE


# TABLES
class TableToken(BaseToken):
    """Represents tables"""

    type: TokenType = TokenType.TABLE
    numbering: Optional[str] = None


# CAPTION
class CaptionToken(BaseToken):
    """Represents captions"""

    type: TokenType = TokenType.CAPTION
    title: Optional[str] = None
    content: List[BaseToken]


# LISTS AND ITEMS
class ItemToken(BaseToken):
    """Represents list items"""

    type: TokenType = TokenType.ITEM
    title: Optional[List[BaseToken]] = None


class ListToken(EnvironmentToken):
    """Represents itemize/enumerate/description environments"""

    type: TokenType = TokenType.LIST
    content: List[ItemToken] = Field(default_factory=list)
    depth: int = 1
