from typing import List, Optional, Type, Union, Dict, Any
from pydantic import BaseModel, Field
from src.structure.tokens.types import TokenType


class BaseToken(BaseModel):
    """Base class for all LaTeX tokens"""

    content: Union[str, List["BaseToken"], Dict[str, "BaseToken"]]
    type: TokenType

    def model_dump(self, **kwargs) -> Dict[str, Any]:
        """Override model_dump to exclude None values by default"""
        kwargs.setdefault("exclude_none", True)
        return super().model_dump(**kwargs)


class EnvironmentToken(BaseToken):
    """Represents LaTeX environments"""

    type: TokenType = TokenType.ENVIRONMENT
    name: Optional[str] = None
    title: Optional[str] = None
    labels: Optional[List[str]] = None
    numbered: bool = False


class TextToken(BaseToken):
    type: TokenType = TokenType.TEXT
    content: str
    styles: Optional[List[str]] = None


class QuoteToken(BaseToken):
    type: TokenType = TokenType.QUOTE
    content: str


class GroupToken(BaseToken):
    type: TokenType = TokenType.GROUP
    content: List[BaseToken]
    styles: Optional[List[str]] = None
