from typing import Callable, Dict, Any, List, Optional, TypeVar, TypedDict, Union

from pydantic import BaseModel, Field

from latex2json.structure.tokens.types import TokenType
from latex2json.structure.tokens.base import BaseToken


# Each tabular cell can be a string, a BaseToken, or None
ContentElement = Union[str, List[BaseToken], None]


class TableCell(BaseModel):
    content: ContentElement  # The cell's content
    rowspan: Optional[int]
    colspan: Optional[int]


CellType = Union[TableCell, ContentElement]
TabularRowType = List[CellType]
TabularContentType = List[TabularRowType]

TokenCreator = Callable[[Dict[str, Any]], BaseToken]


class TabularToken(BaseToken):
    """Represents tabular environments"""

    type: TokenType = TokenType.TABULAR
    content: TabularContentType = Field(default_factory=list)

    def model_dump(self, **kwargs) -> Dict[str, Any]:
        """Override model_dump to handle TableCell instances"""
        kwargs["exclude_none"] = False  # we need to keep None values in content
        result = super().model_dump(**kwargs)

        kwargs_base = kwargs.copy()
        kwargs_base["exclude_none"] = True

        def process_cell(cell: CellType):
            if isinstance(cell, TableCell):
                cell_dict = cell.model_dump(**kwargs)
                cell_dict["content"] = process_cell(cell.content)
                return cell_dict
            elif isinstance(cell, BaseToken):
                out = cell.model_dump(**kwargs_base)
                if "styles" in out and out["styles"] is None:
                    del out["styles"]
                return out
            elif isinstance(cell, list):
                return [process_cell(item) for item in cell]
            return cell

        # Process each cell in the tabular content
        result["content"] = [
            [process_cell(cell) for cell in row] for row in self.content
        ]
        if result.get("styles") is None:
            del result["styles"]
        return result

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
