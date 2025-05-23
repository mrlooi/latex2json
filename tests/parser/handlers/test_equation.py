import pytest
from latex2json.parser.handlers.equation import EquationHandler


@pytest.fixture
def handler():
    return EquationHandler()


def test_can_handle_inline_equations(handler):
    assert handler.can_handle("$x^2$")
    assert handler.can_handle("\\(x^2\\)")
    assert not handler.can_handle("regular text")
    assert not handler.can_handle(
        r"\begin{equation}x^2\end{equation"
    )  # missing closing brace


def test_can_handle_display_equations(handler):
    assert handler.can_handle("$$x^2$$")
    assert handler.can_handle("\\[x^2\\]")
    assert handler.can_handle(r"\begin{equation}x^2\end{equation}")


def test_handle_inline_equations(handler):
    # Test basic inline equation
    token, pos = handler.handle("$x^2$")
    assert token == {"type": "equation", "content": "x^2"}
    assert pos == 5

    # Test inline equation with parentheses
    token, pos = handler.handle(r"\(y^2\)")
    assert token == {"type": "equation", "content": "y^2"}
    assert pos == 7


def test_handle_display_equations(handler):
    # Test display equation with $$
    token, pos = handler.handle("$$x^2$$")
    assert token == {"type": "equation", "content": "x^2", "display": "block"}
    assert pos == 7

    # Test display equation with \[ \]
    token, pos = handler.handle(r"\[y^2\]")
    assert token == {"type": "equation", "content": "y^2", "display": "block"}
    assert pos == 7

    content = r"""\[
        3+3
    \]"""
    assert handler.can_handle(content)
    token, pos = handler.handle(content)
    assert token == {"type": "equation", "content": "3+3", "display": "block"}
    assert pos == len(content)


def test_handle_equation_environments(handler):
    # Test basic equation environment
    content = r"\begin{equation}x^2\end{equation}"
    token, pos = handler.handle(content)
    assert token == {
        "type": "equation",
        "content": "x^2",
        "display": "block",
        "numbered": True,
    }
    assert pos == len(content)

    # Test align environment
    content = r"\begin{align}x &= y\end{align}"
    token, pos = handler.handle(content)
    assert token == {
        "type": "equation",
        "content": "x &= y",
        "display": "block",
        "numbered": True,
        "align": True,
    }
    assert pos == len(content)

    # test alignat with 1 req arg
    content = r"\begin{alignat} {1} x &= y\end{alignat} POST"
    token, pos = handler.handle(content)
    assert token == {
        "type": "equation",
        "content": "x &= y",
        "display": "block",
        "numbered": True,
        "align": True,
    }

    assert content[pos:] == " POST"


def test_handle_equations_with_labels(handler):
    # Test equation with label
    content = r"\begin{equation*} x^2 \label{eq:square} \end{equation*}"
    token, pos = handler.handle(content)
    assert token == {
        "type": "equation",
        "content": "x^2",
        "display": "block",
        "labels": ["eq:square"],
    }
    assert pos == len(content)


def test_handle_empty_equations(handler):
    # Test empty equation
    token, pos = handler.handle("$$$$")
    assert token is None
    assert pos == 4


def test_equation_with_process_fn():
    def mock_process(eq: str) -> str:
        return eq.replace("x", "y")

    handler = EquationHandler(process_content_fn=mock_process)
    token, pos = handler.handle("$x^2$")
    assert token == {"type": "equation", "content": "y^2"}
    assert pos == 5


def test_handle_multiline_equations(handler):
    content = """$$
    x = y + z
    y = 2x
    $$"""
    token, pos = handler.handle(content)
    assert token == {
        "type": "equation",
        "content": "x = y + z\n    y = 2x",
        "display": "block",
    }
    assert pos == len(content)


def test_handle_invalid_input(handler):
    # Test with non-equation content
    token, pos = handler.handle("regular text")
    assert token is None
    assert pos == 0

    # Test with malformed equation
    token, pos = handler.handle("$x^2")  # Missing closing $
    assert token is None
    assert pos == 0


def test_env_equations(handler):
    content = r"""
    \begin{multline*} 
    x^2 \label{eq:square} + 3+3
    E=mc^2 \label{eq:energy}
    \end{multline*}
    """.strip()
    assert handler.can_handle(content)
    token, pos = handler.handle(content)
    assert token["labels"] == ["eq:square", "eq:energy"]
    assert token["content"].replace(" ", "") == "x^2+3+3\nE=mc^2"
    assert content[pos:].strip() == ""


def test_equation_with_env_pairs(handler):
    content = r"""
\begin{eqnarray*}
\array{ccc}
a & b & c \\\\
d & e & f \\\\
g & h & i
\endarray
\end{eqnarray*}

Post align
    """.strip()
    assert handler.can_handle(content)
    token, pos = handler.handle(content)
    assert token
    assert token["align"] is True
    assert r"\array" not in token["content"]
    assert r"\begin{array" in token["content"]
    assert content[pos:].strip() == "Post align"


def test_equation_with_nested_delimiters(handler):
    content = r"""
    $$
    {
    $$1+1$$
    }
    $$
    """.strip()
    assert handler.can_handle(content)
    token, pos = handler.handle(content)
    assert token
    assert token["content"].replace(" ", "").replace("\n", "") == r"{$$1+1$$}"
    # assert content[pos:] == " POST"


def test_equation_strip_formatting(handler):
    # test that \raise.17ex is stripped
    content = r"""
    \begin{equation*}
    \raise.17ex 1+1
    \end{equation*}
    """.strip()
    token, pos = handler.handle(content)
    assert token
    assert token["content"].strip() == "1+1"
    assert content[pos:].strip() == ""

    # but not spacing related e.g. \;
    content = r"""
    \begin{equation*}
    1+1\;222 \hline
    \end{equation*}
    """.strip()
    token, pos = handler.handle(content)
    assert token
    assert token["content"].strip() == r"1+1\;222"


def test_equation_with_includegraphics(handler):
    handler.should_extract_content_placeholders = True
    content = r"""
    \begin{equation*}
    \includegraphics[width=0.5\textwidth]{example-image}
    1+1=2
    \eqref{eq:sum}
    \end{equation*}
    AFTER
    """.strip()
    assert handler.can_handle(content)
    token, pos = handler.handle(content)
    assert token
    assert r"\includegraphics" not in token["content"]
    assert r"\eqref" not in token["content"]
    placeholders = token.get("placeholders", {})
    assert len(placeholders) == 2
    for key, value in placeholders.items():
        assert key in token["content"]

    placeholder_values = list(placeholders.values())
    pl1 = placeholder_values[0]
    assert pl1 == [{"type": "includegraphics", "content": r"example-image"}]
    pl2 = placeholder_values[1]
    assert pl2 == [{"type": "ref", "content": ["eq:sum"]}]
    assert content[pos:].strip() == "AFTER"


def test_equation_with_boxes(handler):
    content = r"$$ \raisebox{\depth}{1+1} $$ POST"
    assert handler.can_handle(content)
    token, pos = handler.handle(content)
    assert token
    assert token["content"] == "1+1"
    assert content[pos:] == " POST"

    # more complex setbox cases
    content = r"$$\setbox0=\hbox{1+1} \hbox{1+1} \kern-.6\wd0 $$ POST"
    assert handler.can_handle(content)
    token, pos = handler.handle(content)
    assert token
    assert token["content"] == "1+1"
    assert content[pos:] == " POST"


if __name__ == "__main__":
    pytest.main([__file__])
