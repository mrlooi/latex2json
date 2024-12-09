from enum import Enum
from typing import Dict, Any, List, Optional, Union

from pydantic import Field
from src.structure.tokens.base import BaseToken, EnvironmentToken
from src.structure.tokens.types import TokenType


# FIGURE
class FigureToken(EnvironmentToken):
    """Represents figures"""

    type: TokenType = TokenType.FIGURE


# TABLES
class TableToken(EnvironmentToken):
    """Represents tables"""

    type: TokenType = TokenType.TABLE


class TabularToken(EnvironmentToken):
    """Represents tabular environments"""

    type: TokenType = TokenType.TABULAR
    column_spec: str
    content: List[List[Union[str, Dict, List]]] = Field(default_factory=list)


# CAPTION
class CaptionToken(BaseToken):
    """Represents captions"""

    type: TokenType = TokenType.CAPTION
    title: Optional[str] = None


# GRAPHICS
class GraphicsToken(BaseToken):
    """Represents graphics"""

    type: TokenType = TokenType.GRAPHICS
    content: str


# LISTS AND ITEMS
class ItemToken(BaseToken):
    """Represents list items"""

    type: TokenType = TokenType.ITEM
    title: Optional[str] = None
    labels: Optional[List[str]] = None


class ListToken(EnvironmentToken):
    """Represents itemize/enumerate/description environments"""

    type: TokenType = TokenType.LIST
    content: List[ItemToken] = Field(default_factory=list)
