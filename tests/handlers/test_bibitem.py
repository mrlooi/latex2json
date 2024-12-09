import pytest
from src.handlers.bibitem import BibItemHandler


@pytest.fixture
def handler():
    return BibItemHandler()


def test_can_handle_bibitem(handler):
    assert handler.can_handle(r"\bibitem{key}")
    assert handler.can_handle(r"\bibitem[Title]{key}")
    assert not handler.can_handle("regular text")


def test_basic_bibitem(handler):
    content = r"\bibitem{key} Some content"
    token, pos = handler.handle(content)

    assert token["type"] == "bibitem"
    assert token["content"] == "Some content"
    assert token["cite_key"] == "key"

    # Test with title
    content = r"\bibitem[Title]{key} Some content"
    token, pos = handler.handle(content)

    assert token["type"] == "bibitem"
    assert token["content"] == "Some content"
    assert token["cite_key"] == "key"
    assert token["title"] == "Title"


def test_bibitem_with_newblock(handler):
    content = r"\bibitem{key} Some content \newblock More content"
    token, pos = handler.handle(content)

    assert token["type"] == "bibitem"
    assert token["content"] == "Some content  More content"
    assert token["cite_key"] == "key"


def test_multiple_bibitems(handler):
    content = r"""
    \bibitem{key1} First item
    \bibitem[Title2]{key2} Second item
    """.strip()

    # Test first bibitem
    token, pos = handler.handle(content)
    assert token["content"] == "First item"

    # Test second bibitem
    remaining = content[pos:].strip()
    token, pos = handler.handle(remaining)
    assert token["content"] == "Second item"
    assert token["title"] == "Title2"


if __name__ == "__main__":
    pytest.main([__file__])
