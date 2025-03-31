from enum import Enum
from typing import Dict, Any, List, Optional
from latex2json.structure.tokens.base import BaseToken, TokenCreator
from latex2json.structure.tokens.types import TokenType


class DisplayType(Enum):
    """Enum for equation display types"""

    INLINE = "inline"
    BLOCK = "block"


class EquationToken(BaseToken):
    """Represents math equations"""

    content: str
    type: TokenType = TokenType.EQUATION
    align: Optional[bool] = None
    display: Optional[DisplayType] = None
    numbering: Optional[str] = None
    placeholders: Optional[Dict[str, List[BaseToken]]] = None

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

    @classmethod
    def process(
        cls, data: Dict[str, Any], create_token: TokenCreator
    ) -> "EquationToken":
        """Process equation data, filtering for EquationItemTokens only"""
        placeholder_dict = None
        if "placeholders" in data:
            placeholder_dict = {}
            for k, v in data["placeholders"].items():
                out = []
                for item in v:
                    out.append(create_token(item))
                placeholder_dict[k] = out

        return cls(
            content=data["content"],
            display=data.get("display"),
            align=data.get("align"),
            numbering=data.get("numbering"),
            placeholders=placeholder_dict,
            labels=data.get("labels"),
            styles=data.get("styles"),
        )
