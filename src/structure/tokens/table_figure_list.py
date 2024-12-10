from enum import Enum
from typing import Dict, Any, List, Optional, TypedDict, Union

from pydantic import BaseModel, Field
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


class TableCell(BaseModel):
    content: Union[str, BaseToken, List[Union[str, BaseToken]]]  # The cell's content
    rowspan: Optional[int]  # Optional as not all cells have it
    colspan: Optional[int]


# The actual cell can be either the TypedDict or simple types
ContentElement = Union[str, BaseToken]
CellType = Union[TableCell, ContentElement, List[ContentElement], None]
TabularRowType = List[CellType]
TabularContentType = List[TabularRowType]


class TabularToken(BaseToken):
    """Represents tabular environments"""

    type: TokenType = TokenType.TABULAR
    # column_spec: str
    content: TabularContentType = Field(default_factory=list)


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
