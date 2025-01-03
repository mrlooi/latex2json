from typing import List, Optional, Type, Union, Dict, Any
from pydantic import BaseModel, Field
from latex_parser.structure.tokens.types import TokenType


class BaseToken(BaseModel):
    """Base class for all LaTeX tokens"""

    content: Union[str, List["BaseToken"], Dict[str, "BaseToken"]]
    type: TokenType
    styles: Optional[List[str]] = None

    def model_dump(self, **kwargs) -> Dict[str, Any]:
        """Override model_dump to exclude None values by default"""
        kwargs.setdefault("exclude_none", True)
        return super().model_dump(**kwargs)

    def model_dump_json(self, **kwargs) -> str:
        """Override model_dump_json to exclude None values by default"""
        kwargs.setdefault("exclude_none", True)
        return super().model_dump_json(**kwargs)


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
