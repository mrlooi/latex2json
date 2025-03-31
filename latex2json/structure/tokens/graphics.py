from enum import Enum
from typing import Dict, Any, List, Optional, TypedDict, Union

from pydantic import BaseModel, Field
from latex2json.structure.tokens.base import BaseToken, EnvironmentToken
from latex2json.structure.tokens.types import TokenType


# GRAPHICS
class IncludeGraphicsToken(BaseToken):
    """Represents includegraphics"""

    type: TokenType = TokenType.INCLUDEGRAPHICS
    content: str
    page: Optional[int] = None


class IncludePdfToken(BaseToken):
    """Represents includepdf"""

    type: TokenType = TokenType.INCLUDEPDF
    content: str
    pages: Optional[str] = None


class DiagramToken(BaseToken):
    """Represents diagrams e.g. tikzpicture, picture"""

    type: TokenType = TokenType.DIAGRAM
    name: str  # tikzpicture, picture, etc.
    content: str  # raw str of inner content of the begin block i.e. content inside \begin{tikzpicture} ...content... \end{tikzpicture}
