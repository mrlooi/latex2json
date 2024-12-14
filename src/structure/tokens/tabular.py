from typing import Callable, Dict, Any, List, Optional, TypeVar, TypedDict, Union

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

TokenCreator = Callable[[Dict[str, Any]], BaseToken]


class TabularToken(BaseToken):
    """Represents tabular environments"""

    type: TokenType = TokenType.TABULAR
    content: TabularContentType = Field(default_factory=list)

    @classmethod
    def process(
        cls, data: Dict[str, Any], create_token: TokenCreator
    ) -> "TabularToken":
        """Process tabular data recursively"""
        content: List[List[Union[str, dict, List]]] = data["content"]
        all_cells: TabularContentType = []
        for row in content:
            row_cells: TabularRowType = []
            for cell in row:
                if cell is None or isinstance(cell, str):
                    row_cells.append(cell)
                elif isinstance(cell, dict):
                    if "type" in cell:
                        row_cells.append(create_token(cell))
                    elif "rowspan" in cell or "colspan" in cell:
                        cell_content = cell["content"]
                        if isinstance(cell_content, list):
                            cell_content = cls._process_nested_list(
                                cell_content, create_token
                            )
                        c = TableCell(
                            rowspan=cell.get("rowspan", 1),
                            colspan=cell.get("colspan", 1),
                            content=cell_content,
                        )
                        row_cells.append(c)
                elif isinstance(cell, list):
                    row_cells.append(cls._process_nested_list(cell, create_token))
                else:
                    row_cells.append(cell)
            all_cells.append(row_cells)
        return cls(content=all_cells)

    @classmethod
    def _process_nested_list(
        cls, nested_list: List, create_token: TokenCreator
    ) -> List:
        """Recursively process a nested list"""
        processed_list = []
        for item in nested_list:
            if isinstance(item, dict) and "type" in item:
                processed_list.append(create_token(item))
            elif isinstance(item, list):
                processed_list.append(cls._process_nested_list(item, create_token))
            else:
                processed_list.append(item)
        return processed_list
