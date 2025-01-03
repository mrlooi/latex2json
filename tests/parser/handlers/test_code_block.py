import pytest
from latex_parser.parser.handlers.code_block import CodeBlockHandler


@pytest.fixture
def handler():
    return CodeBlockHandler()


def test_can_handle_code_blocks(handler):
    assert handler.can_handle(r"\begin{verbatim}code here\end{verbatim}")
    assert handler.can_handle(r"\begin{lstlisting}code here\end{lstlisting}")
    assert handler.can_handle(r"\verb|code|")
    assert not handler.can_handle("regular text")


def test_handle_verbatim(handler):
    content = r"""\begin{verbatim}def example():
    print('hello world')
\end{verbatim}"""
    token, pos = handler.handle(content)
    assert token == {
        "type": "code",
        "content": "def example():\n    print('hello world')",
    }
    assert pos == len(content)


def test_handle_lstlisting(handler):
    # Test basic lstlisting
    content = r"""\begin{lstlisting}
int main() {
    return 0;
}
\end{lstlisting}"""
    token, pos = handler.handle(content)
    assert token == {"type": "code", "content": "int main() {\n    return 0;\n}"}

    # Test lstlisting with title/parameters
    content = r"""\begin{lstlisting}[language=Python]
def example():
    pass
\end{lstlisting}"""
    token, pos = handler.handle(content)
    assert token == {
        "type": "code",
        "content": "def example():\n    pass",
        "title": "language=Python",
    }


def test_handle_verb(handler):
    # Test basic verb
    token, pos = handler.handle(r"\verb|code|")
    assert token == {"type": "code", "content": "code"}

    # Test verb with different delimiter
    token, pos = handler.handle(r"\verb#more code#")
    assert token == {"type": "code", "content": "more code"}

    # Test verb*
    token, pos = handler.handle(r"\verb*|code with spaces|")
    assert token == {"type": "code", "content": "code with spaces"}


def test_handle_multiline_code(handler):
    content = r"""\begin{verbatim}
def multiline():
    print('line 1')
    print('line 2')
    return True
\end{verbatim}"""
    token, pos = handler.handle(content)
    assert token == {
        "type": "code",
        "content": "def multiline():\n    print('line 1')\n    print('line 2')\n    return True",
    }


def test_handle_invalid_input(handler):
    # Test with non-command content
    token, pos = handler.handle("regular text")
    assert token is None
    assert pos == 0

    # Test with malformed command
    token, pos = handler.handle(r"\begin{verbatim}Incomplete")
    assert token is None
    assert pos == 0


def test_handle_empty_content(handler):
    # Test empty verbatim
    token, pos = handler.handle(r"\begin{verbatim}\end{verbatim}")
    assert token == {"type": "code", "content": ""}

    # Test empty lstlisting
    token, pos = handler.handle(r"\begin{lstlisting}\end{lstlisting}")
    assert token == {"type": "code", "content": ""}


if __name__ == "__main__":
    pytest.main([__file__])
