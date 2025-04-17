from typing import Dict, Type

from latex2json.structure.tokens.types import TokenType

from latex2json.structure.tokens.base import (
    BaseToken,
    CommandToken,
    MathEnvToken,
    TextToken,
    QuoteToken,
    EnvironmentToken,
    GroupToken,
)

from latex2json.structure.tokens.document import (
    DocumentToken,
    ParagraphToken,
    TitleToken,
    SectionToken,
    AbstractToken,
    AppendixToken,
)
from latex2json.structure.tokens.equation import EquationToken
from latex2json.structure.tokens.table_figure_list import (
    ListToken,
    ItemToken,
    SubFigureToken,
    TableToken,
    FigureToken,
    CaptionToken,
)
from latex2json.structure.tokens.graphics import (
    IncludeGraphicsToken,
    IncludePdfToken,
    DiagramToken,
)
from latex2json.structure.tokens.tabular import TabularToken
from latex2json.structure.tokens.ref_and_cite import (
    CitationToken,
    ReferenceToken,
    UrlToken,
    FootnoteToken,
)
from latex2json.structure.tokens.code_and_algo import (
    CodeToken,
    AlgorithmToken,
    AlgorithmicToken,
)
from latex2json.structure.tokens.bibliography import BibliographyToken, BibItemToken
from latex2json.structure.tokens.metadata import (
    AddressToken,
    AuthorToken,
    EmailToken,
    AffiliationToken,
    KeywordsToken,
)

TokenMap: Dict[TokenType, Type[BaseToken]] = {
    # Document/Content Structure
    TokenType.DOCUMENT: DocumentToken,
    TokenType.TITLE: TitleToken,
    TokenType.SECTION: SectionToken,
    TokenType.PARAGRAPH: ParagraphToken,
    TokenType.ABSTRACT: AbstractToken,
    TokenType.APPENDIX: AppendixToken,
    # command
    TokenType.COMMAND: CommandToken,
    # ENV related
    TokenType.ENVIRONMENT: EnvironmentToken,
    TokenType.MATH_ENV: MathEnvToken,
    # Tables & Figures
    TokenType.FIGURE: FigureToken,
    TokenType.SUBFIGURE: SubFigureToken,
    TokenType.TABLE: TableToken,
    TokenType.TABULAR: TabularToken,
    TokenType.CAPTION: CaptionToken,
    # Graphics
    TokenType.INCLUDEGRAPHICS: IncludeGraphicsToken,
    TokenType.INCLUDEPDF: IncludePdfToken,
    TokenType.DIAGRAM: DiagramToken,
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
    TokenType.ADDRESS: AddressToken,
    # Other
    TokenType.GROUP: GroupToken,
}
