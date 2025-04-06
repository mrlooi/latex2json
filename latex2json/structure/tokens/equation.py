from enum import Enum
from typing import Dict, Any, List, Optional
from latex2json.structure.tokens.base import BaseToken, TokenCreator
from latex2json.structure.tokens.types import TokenType


class DisplayType(Enum):
    """Enum for equation display types"""

    INLINE = "inline"
    BLOCK = "block"

    def __str__(self) -> str:
        return self.value


class EquationToken(BaseToken):
    """Represents math equations"""

    content: str
    type: TokenType = TokenType.EQUATION
    align: Optional[bool] = None
    display: Optional[DisplayType] = None
    numbering: Optional[str] = None
    placeholders: Optional[Dict[str, List[BaseToken]]] = None

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
