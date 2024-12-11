import logging
from typing import Dict, List, Type, Any, Callable, Union
from src.structure.tokens.table_figure_list import (
    GraphicsToken,
    TableCell,
    TabularContentType,
    TabularRowType,
    TabularToken,
)
from src.structure.tokens.types import TokenType
from src.structure.tokens.base import BaseToken, TextToken
from src.structure.tokens.registry import TOKEN_MAP


class TokenProcessor:
    """Base class for token processing strategies"""

    def process(self, data: Dict[str, Any], factory: "TokenFactory") -> BaseToken:
        """Default processing implementation"""
        return data


class TabularProcessor(TokenProcessor):
    def process(self, data: Dict[str, Any], factory: "TokenFactory") -> BaseToken:
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
                        row_cells.append(factory.create(cell))
                    elif "rowspan" in cell:
                        content = factory.create(cell["content"])
                        c = TableCell(
                            rowspan=cell["rowspan"],
                            colspan=cell["colspan"],
                            content=content,
                        )
                        row_cells.append(c)
                elif isinstance(cell, list):
                    # Recursively process nested lists
                    row_cells.append(self._process_nested_list(cell, factory))
                else:
                    row_cells.append(cell)
            all_cells.append(row_cells)
        return TabularToken(content=all_cells)

    def _process_nested_list(self, nested_list: List, factory: "TokenFactory") -> List:
        """Recursively process a nested list"""
        processed_list = []
        for item in nested_list:
            if isinstance(item, dict) and "type" in item:
                processed_list.append(factory.create(item))
            elif isinstance(item, list):
                # Recursively process further nested lists
                processed_list.append(self._process_nested_list(item, factory))
            else:
                processed_list.append(item)
        return processed_list


class TokenFactory:
    """Factory class for creating token instances based on their type"""

    def __init__(self, logger: logging.Logger = None):
        self.logger = logger or logging.getLogger(__name__)
        self._token_map = TOKEN_MAP.copy()  # Instance-specific token map
        self._processors: Dict[TokenType, TokenProcessor] = {}
        self._custom_type_handlers: Dict[str, Callable[[Dict[str, Any]], BaseToken]] = (
            {}
        )
        self._init_handlers()

    def _init_handlers(self):
        self.register_processor(TokenType.TABULAR, TabularProcessor())

        def handle_includegraphics(data: Dict[str, Any]) -> BaseToken:
            return GraphicsToken(content=data["content"])

        self.register_custom_type("includegraphics", handle_includegraphics)

    def create(self, data: Union[str, Dict[str, Any]]) -> BaseToken:
        if isinstance(data, str):
            return data

        """Create a token instance based on the provided data"""
        original_type = data.get("type")

        # Handle custom string types first
        if (
            isinstance(original_type, str)
            and original_type in self._custom_type_handlers
        ):
            return self._custom_type_handlers[original_type](data)

        # Try to convert to TokenType enum
        try:
            if isinstance(original_type, str):
                converted_type = TokenType(original_type)
                data = {
                    **data,
                    "type": converted_type,
                }  # Create a new dictionary with the converted type
        except ValueError:
            self.logger.warning(
                f"Unknown token type: {original_type}, falling back to BaseToken"
            )
            # Could either raise, or fall back to BaseToken
            return BaseToken.model_validate(data)

        token_type = data.get("type")
        # Get processor or use default
        processor = self._processors.get(token_type, TokenProcessor())
        data = processor.process(data, self)

        # Recursively process content
        if "content" in data:
            data["content"] = self._process_content(data["content"])

        token_class = self._token_map.get(token_type, BaseToken)
        try:
            return token_class.model_validate(data)
        except Exception as e:
            self.logger.error(
                f"Failed to create token of type {data['type']}: {str(e)}"
            )
            self.logger.error(f"Data: {data}")
            raise

    def _process_content(self, content: Union[Dict, List, str]) -> Any:
        """Helper method to process nested content"""
        if isinstance(content, dict) and "type" in content:
            return self.create(content)
        elif isinstance(content, list):
            return [
                self.create(item) if isinstance(item, dict) and "type" in item else item
                for item in content
            ]
        return content

    def register_processor(
        self, token_type: TokenType, processor: TokenProcessor
    ) -> None:
        """Register a processor for a specific token type"""
        self._processors[token_type] = processor

    def register_token_type(
        self, token_type: TokenType, token_class: Type[BaseToken]
    ) -> None:
        """Register a new token type and its corresponding class."""
        if not issubclass(token_class, BaseToken):
            raise ValueError(f"Token class must inherit from BaseToken: {token_class}")
        self._token_map[token_type] = token_class

    def register_custom_type(
        self, type_name: str, handler: Callable[[Dict[str, Any]], BaseToken]
    ) -> None:
        """Register a handler for a custom token type not in TokenType enum"""
        self._custom_type_handlers[type_name] = handler


if __name__ == "__main__":
    # Creating a token
    token_data = {
        "type": "equation",
        "content": "E = mc^2",
        "display": "inline",
        "labels": ["eq:einstein"],
    }

    try:
        token = TokenFactory.create(token_data)
        print(token)
        # # You can also register custom token types
        # class CustomToken(BaseToken):
        #     type: TokenType = TokenType.CUSTOM

        # TokenFactory.register_token_type(TokenType.CUSTOM, CustomToken)

    except ValueError as e:
        print(f"Error creating token: {e}")
