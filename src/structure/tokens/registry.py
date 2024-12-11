from typing import Dict, Type

from src.structure.tokens.types import TokenType

from src.structure.tokens.base import (
    BaseToken,
    TextToken,
    QuoteToken,
    EnvironmentToken,
    GroupToken,
)

from src.structure.tokens.document import (
    DocumentToken,
    ParagraphToken,
    TitleToken,
    SectionToken,
    AbstractToken,
    AppendixToken,
)
from src.structure.tokens.equation import EquationToken
from src.structure.tokens.table_figure_list import (
    ListToken,
    ItemToken,
    TableToken,
    TabularToken,
    FigureToken,
    GraphicsToken,
    CaptionToken,
)
from src.structure.tokens.ref_and_cite import (
    CitationToken,
    ReferenceToken,
    UrlToken,
    FootnoteToken,
)
from src.structure.tokens.code_and_algo import (
    CodeToken,
    AlgorithmToken,
    AlgorithmicToken,
)
from src.structure.tokens.bibliography import BibliographyToken, BibItemToken
from src.structure.tokens.metadata import (
    AuthorToken,
    EmailToken,
    AffiliationToken,
    KeywordsToken,
)

TOKEN_MAP: Dict[TokenType, Type[BaseToken]] = {
    # Document/Content Structure
    TokenType.DOCUMENT: DocumentToken,
    TokenType.TITLE: TitleToken,
    TokenType.SECTION: SectionToken,
    TokenType.PARAGRAPH: ParagraphToken,
    TokenType.ABSTRACT: AbstractToken,
    TokenType.APPENDIX: AppendixToken,
    # ENV related
    TokenType.ENVIRONMENT: EnvironmentToken,
    # Tables & Figures
    TokenType.FIGURE: FigureToken,
    TokenType.TABLE: TableToken,
    TokenType.TABULAR: TabularToken,
    TokenType.GRAPHICS: GraphicsToken,
    TokenType.CAPTION: CaptionToken,
    # Lists
    TokenType.LIST: ListToken,
    TokenType.ITEM: ItemToken,
    # Text
    TokenType.TEXT: TextToken,
    TokenType.QUOTE: QuoteToken,
    # Math & Technical
    TokenType.EQUATION: EquationToken,
    TokenType.CODE: CodeToken,
    TokenType.ALGORITHM: AlgorithmToken,
    TokenType.ALGORITHMIC: AlgorithmicToken,
    # References & Links
    TokenType.CITATION: CitationToken,
    TokenType.REF: ReferenceToken,
    TokenType.URL: UrlToken,
    TokenType.FOOTNOTE: FootnoteToken,
    # Bibliography
    TokenType.BIBLIOGRAPHY: BibliographyToken,
    TokenType.BIBITEM: BibItemToken,
    # Metadata
    TokenType.AUTHOR: AuthorToken,
    TokenType.EMAIL: EmailToken,
    TokenType.AFFILIATION: AffiliationToken,
    TokenType.KEYWORDS: KeywordsToken,
    # Other
    TokenType.GROUP: GroupToken,
}
