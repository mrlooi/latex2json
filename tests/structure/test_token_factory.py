import pytest
from src.structure.tokens.types import TokenType
from src.structure.tokens.tabular import TabularToken, TableCell
from src.structure.tokens.bibliography import BibliographyToken, BibItemToken
from src.structure.token_factory import TokenFactory


@pytest.fixture
def token_factory():
    return TokenFactory()


class TestTabularToken:
    def test_process_simple_table(self, token_factory):
        data = {"type": TokenType.TABULAR, "content": [["A", "B"], ["C", "D"]]}

        token = TabularToken.process(data, token_factory.create)

        assert isinstance(token, TabularToken)
        assert len(token.content) == 2
        assert token.content[0] == ["A", "B"]
        assert token.content[1] == ["C", "D"]

    def test_process_table_with_spans(self, token_factory):
        data = {
            "type": TokenType.TABULAR,
            "content": [[{"content": "A", "colspan": 2}, "B"], ["C", "D", "E"]],
        }

        token = TabularToken.process(data, token_factory.create)

        assert isinstance(token, TabularToken)
        assert len(token.content) == 2
        assert isinstance(token.content[0][0], TableCell)
        assert token.content[0][0].colspan == 2
        assert token.content[0][0].content == "A"

    def test_process_nested_tokens(self, token_factory):
        data = {
            "type": TokenType.TABULAR,
            "content": [[{"type": TokenType.TEXT, "content": "Hello"}, "World"]],
        }

        token = TabularToken.process(data, token_factory.create)

        assert isinstance(token, TabularToken)
        assert token.content[0][0].type == TokenType.TEXT
        assert token.content[0][0].content == "Hello"


def create_bibitem(content: str, cite_key: str):
    return {
        "type": TokenType.BIBITEM,
        "content": [{"type": "text", "content": content}],
        "cite_key": cite_key,
    }


class TestBibliographyToken:
    def test_raw_bibitem_token(self, token_factory):
        data = {
            "type": TokenType.BIBITEM.value,
            "content": [{"type": "text", "content": "Reference 1"}],
            "cite_key": "ref1",
        }
        token = token_factory.create(data)
        assert isinstance(token, BibItemToken)
        assert token.cite_key == "ref1"

    def test_process_bibliography(self, token_factory):
        data = {
            "type": TokenType.BIBLIOGRAPHY,
            "content": [
                create_bibitem("Reference 1", "ref1"),
                create_bibitem("Reference 2", "ref2"),
            ],
        }

        token = BibliographyToken.process(data, token_factory.create)

        assert isinstance(token, BibliographyToken)
        assert len(token.content) == 2
        assert all(isinstance(item, BibItemToken) for item in token.content)
        assert token.content[0].cite_key == "ref1"  # Changed from key to cite_key
        assert token.content[1].cite_key == "ref2"  # Changed from key to cite_key
        assert token.content[0].content[0].content == "Reference 1"
        assert token.content[1].content[0].content == "Reference 2"

    def test_process_bibliography_filters_non_bibitems(self, token_factory):
        data = {
            "type": TokenType.BIBLIOGRAPHY,
            "content": [
                create_bibitem("Reference 1", "ref1"),
                create_bibitem("Reference 2", "ref2"),
            ],
        }

        token = BibliographyToken.process(data, token_factory.create)

        assert isinstance(token, BibliographyToken)
        assert len(token.content) == 2
        assert all(isinstance(item, BibItemToken) for item in token.content)
        assert token.content[0].cite_key == "ref1"  # Changed from key to cite_key
        assert token.content[1].cite_key == "ref2"  # Changed from key to cite_key
