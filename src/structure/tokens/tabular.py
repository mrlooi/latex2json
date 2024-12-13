from typing import Dict, Any, List, Optional, TypedDict, Union

from pydantic import BaseModel, Field

from src.structure.tokens.types import TokenType
from src.structure.tokens.base import BaseToken


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
