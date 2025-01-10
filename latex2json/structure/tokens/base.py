from typing import List, Optional, Type, Union, Dict, Any
from pydantic import BaseModel, Field
from latex2json.structure.tokens.types import TokenType


class BaseToken(BaseModel):
    """Base class for all LaTeX tokens"""

    type: TokenType
    styles: Optional[List[str]] = None
    content: Union[str, List["BaseToken"]]

    def model_dump(self, **kwargs) -> Dict[str, Any]:
        """Override model_dump to handle recursive content dumping and ensure JSON serializability"""
        # Get exclude_none from kwargs or default to False
        exclude_none = kwargs.get("exclude_none", False)

        # Get the basic model dump but exclude content as we'll handle it specially
        result = super().model_dump(**kwargs)

        # Helper function to ensure value is JSON serializable
        def serialize_value(val):
            if isinstance(val, BaseToken):
                return val.model_dump(**kwargs)
            elif isinstance(val, (str, int, float, bool, type(None))):
                return val
            elif isinstance(val, (list, tuple)):
                return [serialize_value(v) for v in val]
            elif isinstance(val, dict):
                return {k: serialize_value(v) for k, v in val.items()}
            else:
                # Convert any other types to string representation
                return str(val)

        # Handle content field recursively
        if isinstance(self.content, list):
            result["content"] = [serialize_value(token) for token in self.content]
        else:
            result["content"] = serialize_value(self.content)

        # Remove None values if exclude_none is True
        if exclude_none:
            result = {k: v for k, v in result.items() if v is not None}

        return result


class EnvironmentToken(BaseToken):
    """Represents LaTeX environments"""

    type: TokenType = TokenType.ENVIRONMENT
    name: Optional[str] = None
    title: Optional[str] = None
    labels: Optional[List[str]] = None


class MathEnvToken(EnvironmentToken):
    type: TokenType = TokenType.MATH_ENV
    name: str
    numbering: Optional[str] = None


class TextToken(BaseToken):
    type: TokenType = TokenType.TEXT
    content: str

    def __repr__(self):
        if self.styles:
            return f'STYLED:{self.styles} -> "{self.content}"'
        return f'"{self.content}"'


class QuoteToken(BaseToken):
    type: TokenType = TokenType.QUOTE


class GroupToken(BaseToken):
    type: TokenType = TokenType.GROUP
    content: List[BaseToken]


# usually for unknown commands
class CommandToken(BaseToken):
    type: TokenType = TokenType.COMMAND
    command: str
    content: Optional[str] = None
