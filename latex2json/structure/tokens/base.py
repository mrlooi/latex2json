from typing import Callable, List, Optional, Type, Union, Dict, Any
from pydantic import BaseModel, Field
from latex2json.structure.tokens.types import TokenType


class BaseToken(BaseModel):
    """Base class for all LaTeX tokens"""

    type: TokenType
    # e.g. ["color={HTML:FF0000}", "color=red", "bold", "italic", ...]
    styles: Optional[List[str]] = None
    content: Union[str, List["BaseToken"]]
    labels: Optional[List[str]] = None

    @staticmethod
    def serialize_value(val, **kwargs):
        """Helper method to serialize values for JSON dumping"""
        if isinstance(val, BaseToken):
            return val.model_dump(**kwargs)
        elif isinstance(val, (str, int, float, bool, type(None))):
            return val
        elif isinstance(val, (list, tuple)):
            return [BaseToken.serialize_value(v, **kwargs) for v in val]
        elif isinstance(val, dict):
            return {k: BaseToken.serialize_value(v, **kwargs) for k, v in val.items()}
        else:
            # Convert any other types to string representation
            return str(val)

    def model_dump(self, **kwargs) -> Dict[str, Any]:
        """Override model_dump to handle recursive content dumping and ensure JSON serializability"""
        # Get exclude_none from kwargs or default to False
        exclude_none = kwargs.get("exclude_none", False)

        # Get the basic model dump but exclude content as we'll handle it specially
        result = super().model_dump(**kwargs)

        # Handle content field recursively
        if isinstance(self.content, list):
            result["content"] = [
                self.serialize_value(token, **kwargs) for token in self.content
            ]
        else:
            result["content"] = self.serialize_value(self.content, **kwargs)

        # Remove None values if exclude_none is True
        if exclude_none:
            result = {k: v for k, v in result.items() if v is not None}

        return result


TokenCreator = Callable[[Dict[str, Any]], BaseToken]


class EnvironmentToken(BaseToken):
    """Represents LaTeX environments"""

    type: TokenType = TokenType.ENVIRONMENT
    name: Optional[str] = None


class MathEnvToken(BaseToken):
    type: TokenType = TokenType.MATH_ENV
    name: str
    content: List[BaseToken]
    numbering: Optional[str] = None
    title: Optional[List[BaseToken]] = None
    proof: Optional[List[BaseToken]] = None

    def model_dump(self, **kwargs):
        result = super().model_dump(**kwargs)

        if self.title:
            result["title"] = [
                self.serialize_value(token, **kwargs) for token in self.title
            ]
        if self.proof:
            result["proof"] = [
                self.serialize_value(token, **kwargs) for token in self.proof
            ]

        return result

    @classmethod
    def process(
        cls, data: Dict[str, Any], create_token: TokenCreator
    ) -> "MathEnvToken":
        """Process math environment data, filtering for MathEnvTokens only"""
        content = []
        title = None
        proof = None
        if "content" in data:
            for item in data["content"]:
                content.append(create_token(item))
        if "title" in data:
            title = []
            for item in data["title"]:
                title.append(create_token(item))
        if "proof" in data:
            proof = []
            for item in data["proof"]:
                proof.append(create_token(item))

        return cls(
            content=content,
            labels=data.get("labels"),
            styles=data.get("styles"),
            name=data.get("name"),
            numbering=data.get("numbering"),
            title=title,
            proof=proof,
        )


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
