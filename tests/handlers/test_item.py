import pytest
from src.handlers.item import ItemHandler


@pytest.fixture
def handler():
    return ItemHandler()


def test_can_handle_item(handler):
    assert handler.can_handle(r"\item First item")
    assert handler.can_handle(r"\item[1.] First item")
    assert not handler.can_handle("regular text")


def test_basic_item(handler):
    content = r"\item First item"
    token, pos = handler.handle(content)

    assert token["type"] == "item"
    assert token["content"] == "First item"

    # Test with label
    content = r"\item[1.] First item"
    token, pos = handler.handle(content)

    assert token["type"] == "item"
    assert token["content"] == "First item"
    assert token["label"] == "1."


def test_multiple_items(handler):
    content = r"""
    \item First
    \item [] Second
    \item Third
    """.strip()

    # Test first item
    token, pos = handler.handle(content)
    assert token["content"] == "First"

    # Test second item
    remaining = content[pos:].strip()
    token, pos = handler.handle(remaining)
    assert token["content"] == "Second"

    # Test third item
    remaining = remaining[pos:].strip()
    token, pos = handler.handle(remaining)
    assert token["content"] == "Third"


def test_nested_environments(handler):
    content = r"""
    \item First item with nested list
    \begin{itemize}
    \item Nested item 1
    \item Nested item 2
    \end{itemize}
    \item Second item
    """.strip()

    token, pos = handler.handle(content)
    assert token["type"] == "item"
    assert "begin{itemize}" in token["content"]
    assert "Nested item 1" in token["content"]
    assert "Nested item 2" in token["content"]
    assert "end{itemize}" in token["content"]

    # Check that we can handle the next item
    remaining = content[pos:].strip()
    assert remaining.startswith(r"\item Second item")


def test_deeply_nested_environments(handler):
    content = r"""
    \item Top level
    \begin{enumerate}
    \item Level 1
    \begin{itemize}
    \item Level 2
    \end{itemize}
    \end{enumerate}
    \item Next top level
    """.strip()

    token, pos = handler.handle(content)
    assert token["type"] == "item"
    assert "Top level" in token["content"]
    assert "begin{enumerate}" in token["content"]
    assert r"\item Level 1" in token["content"]
    assert "begin{itemize}" in token["content"]
    assert r"\item Level 2" in token["content"]
    assert "end{itemize}" in token["content"]
    assert "end{enumerate}" in token["content"]

    remaining = content[pos:].strip()
    assert remaining.startswith(r"\item Next top level")


if __name__ == "__main__":
    pytest.main([__file__])
