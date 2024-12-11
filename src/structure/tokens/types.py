from enum import Enum


class TokenType(Enum):
    """Enum for token types"""

    # Document/Content Structure
    DOCUMENT = "document"
    TITLE = "title"
    SECTION = "section"
    PARAGRAPH = "paragraph"
    ABSTRACT = "abstract"
    APPENDIX = "appendix"

    COMMAND = "command"

    # Text
    TEXT = "text"
    QUOTE = "quote"

    # ENV related
    ENVIRONMENT = "environment"
    # Tables & Figures
    FIGURE = "figure"
    TABLE = "table"
    TABULAR = "tabular"
    GRAPHICS = "graphics"
    CAPTION = "caption"

    # Lists
    LIST = "list"
    ITEM = "item"

    # Math & Technical
    EQUATION = "equation"
    CODE = "code"
    ALGORITHM = "algorithm"
    ALGORITHMIC = "algorithmic"

    # References & Links
    CITATION = "citation"
    REF = "ref"
    URL = "url"
    FOOTNOTE = "footnote"

    # Bibliography
    BIBLIOGRAPHY = "bibliography"
    BIBITEM = "bibitem"

    # Metadata
    AUTHOR = "author"
    EMAIL = "email"
    AFFILIATION = "affiliation"
    KEYWORDS = "keywords"
    ADDRESS = "address"

    # Other
    GROUP = "group"

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}.{self.value.upper()}"
