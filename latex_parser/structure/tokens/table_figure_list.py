from enum import Enum
from typing import Dict, Any, List, Optional, TypedDict, Union

from pydantic import BaseModel, Field
from latex_parser.structure.tokens.base import BaseToken, EnvironmentToken
from latex_parser.structure.tokens.types import TokenType


# FIGURE
class FigureToken(EnvironmentToken):
    """Represents figures"""

    type: TokenType = TokenType.FIGURE
    numbering: Optional[str] = None


# TABLES
class TableToken(EnvironmentToken):
    """Represents tables"""

    type: TokenType = TokenType.TABLE
    numbering: Optional[str] = None


# CAPTION
class CaptionToken(BaseToken):
    """Represents captions"""

    type: TokenType = TokenType.CAPTION
    title: Optional[str] = None


# GRAPHICS
class IncludeGraphicsToken(BaseToken):
    """Represents includegraphics"""

    type: TokenType = TokenType.INCLUDEGRAPHICS
    content: str
    page: Optional[int] = None


class IncludePdfToken(BaseToken):
    """Represents includepdf"""

    type: TokenType = TokenType.INCLUDEPDF
    content: str
    pages: Optional[str] = None


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
