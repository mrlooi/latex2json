import logging
from typing import Dict, Type, Any
from src.structure.tokens.types import TokenType
from src.structure.tokens.base import BaseToken
from src.structure.tokens.registry import TOKEN_MAP


class TokenFactory:
    """Factory class for creating token instances based on their type"""

    _token_map = TOKEN_MAP

    def __init__(self, logger: logging.Logger = None):
        self.logger = logger

    @classmethod
    def create(cls, data: Dict[str, Any]) -> BaseToken:
        """Create a token instance based on the provided data."""
        if isinstance(data.get("type"), str):
            try:
                data["type"] = TokenType(data["type"])
            except ValueError as e:
                raise ValueError(f"Invalid token type: {data['type']}") from e

        token_class = cls._token_map.get(data["type"], BaseToken)

        try:
            return token_class.model_validate(data)
        except Exception as e:
            raise ValueError(
                f"Failed to create token of type {data['type']}: {str(e)}"
            ) from e

    @classmethod
    def register_token_type(
        cls, token_type: TokenType, token_class: Type[BaseToken]
    ) -> None:
        """Register a new token type and its corresponding class."""
        if not issubclass(token_class, BaseToken):
            raise ValueError(f"Token class must inherit from BaseToken: {token_class}")
        cls._token_map[token_type] = token_class


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
