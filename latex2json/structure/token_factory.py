import logging
from typing import Dict, List, Type, Any, Callable, Union
from latex2json.structure.tokens.bibliography import BibliographyToken
from latex2json.structure.tokens.equation import EquationToken
from latex2json.structure.tokens.types import TokenType
from latex2json.structure.tokens.base import BaseToken, MathEnvToken
from latex2json.structure.tokens.registry import TokenMap
from latex2json.structure.tokens.tabular import TabularToken


class TokenFactory:
    """Factory class for creating token instances based on their type"""

    def __init__(self, logger: logging.Logger = None):
        self.logger = logger or logging.getLogger(__name__)
        self._token_map = TokenMap.copy()  # Instance-specific token map
        self._custom_type_handlers: Dict[
            str, Callable[[Dict[str, Any]], BaseToken | None]
        ] = {}
        self._init_handlers()

    def _init_handlers(self):
        def handle_date(data: Dict[str, Any]) -> None:
            return None

        self.register_custom_type("date", handle_date)

    def create(self, data: Union[str, Dict[str, Any]]) -> BaseToken | None:
        """Create a token instance based on the provided data"""
        # Handle simple string tokens
        if isinstance(data, str):
            return data

        # Validate input
        if isinstance(data, list):
            raise ValueError("List of tokens is not supported", data)

        # Get and validate token type
        token_type = self._get_token_type(data)
        if not token_type:
            return None

        # Process based on token type
        try:
            return self._create_token(token_type, data)
        except Exception as e:
            self.logger.error(
                f"Failed to create token of type {token_type}: {str(e)}", exc_info=True
            )
            self.logger.error(f"Data: {data}")
            raise

    def _get_token_type(self, data: Dict[str, Any]) -> Union[TokenType, str, None]:
        """Extract and validate the token type"""
        original_type = data.get("type")

        # Handle custom string types
        if isinstance(original_type, str):
            if original_type in self._custom_type_handlers:
                return original_type

            # Try converting to TokenType enum
            try:
                return TokenType(original_type)
            except ValueError:
                self.logger.warning(
                    f"Unknown token type: {original_type}, falling back to BaseToken"
                )
                return None

        return original_type

    def _create_token(
        self, token_type: Union[TokenType, str], data: Dict[str, Any]
    ) -> BaseToken:
        """Create the appropriate token based on type"""
        # Handle custom types
        if isinstance(token_type, str):
            return self._custom_type_handlers[token_type](data)

        # Handle special token types
        if token_type == TokenType.TABULAR:
            return TabularToken.process(data, self.create)
        elif token_type == TokenType.BIBLIOGRAPHY:
            return BibliographyToken.process(data, self.create)
        elif token_type == TokenType.EQUATION:
            return EquationToken.process(data, self.create)
        elif token_type == TokenType.MATH_ENV:
            return MathEnvToken.process(data, self.create)

        # Handle standard tokens
        if "content" in data:
            data = {**data, "content": self._process_content(data["content"])}
        if "title" in data:
            data = {**data, "title": self._process_content(data["title"])}

        token_class = self._token_map.get(token_type, BaseToken)
        return token_class.model_validate(data)

    def _process_content(self, content: Union[Dict, List, str]) -> Any:
        """Helper method to process nested content recursively"""
        if isinstance(content, dict) and "type" in content:
            return self.create(content)
        elif isinstance(content, list):
            output = []
            for item in content:
                if isinstance(item, list):
                    # Recursively process nested lists
                    processed_item = self._process_content(item)
                    output.append(processed_item)
                elif isinstance(item, dict) and "type" in item:
                    processed_item = self.create(item)
                    if processed_item is not None:
                        output.append(processed_item)
                else:
                    output.append(item)
            return output
        return content

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
        token_creator = TokenFactory()
        token = token_creator.create(token_data)
        print(token)
        # # You can also register custom token types
        # class CustomToken(BaseToken):
        #     type: TokenType = TokenType.CUSTOM

        # TokenFactory.register_token_type(TokenType.CUSTOM, CustomToken)

    except ValueError as e:
        print(f"Error creating token: {e}")
