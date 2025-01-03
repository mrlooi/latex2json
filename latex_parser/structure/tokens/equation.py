from enum import Enum
from typing import Dict, Any, List, Optional
from latex_parser.structure.tokens.base import BaseToken
from latex_parser.structure.tokens.types import TokenType


class DisplayType(Enum):
    """Enum for equation display types"""

    INLINE = "inline"
    BLOCK = "block"


class EquationToken(BaseToken):
    """Represents math equations"""

    content: str
    type: TokenType = TokenType.EQUATION
    align: Optional[bool] = None
    display: DisplayType = DisplayType.INLINE
    labels: Optional[List[str]] = None
    numbering: Optional[str] = None

    @classmethod
    def preprocess_data(cls, data: Dict[str, Any]) -> Dict[str, Any]:
        """Preprocess equation-specific data before validation"""
        if isinstance(data.get("display"), str):
            data["display"] = DisplayType(data["display"])
        return data

    @classmethod
    def model_validate(cls, data: Dict[str, Any]) -> "EquationToken":
        """Override model_validate to handle preprocessing"""
        processed_data = cls.preprocess_data(data)
        return super().model_validate(processed_data)
