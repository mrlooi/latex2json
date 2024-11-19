import pytest
from src.handlers.equation import EquationHandler

@pytest.fixture
def handler():
    return EquationHandler()

def test_can_handle_inline_equations(handler):
    assert handler.can_handle("$x^2$")
    assert handler.can_handle("\\(x^2\\)")
    assert not handler.can_handle("regular text")
    assert not handler.can_handle(r"\begin{equation}x^2\end{equation") # missing closing brace

def test_can_handle_display_equations(handler):
    assert handler.can_handle("$$x^2$$")
    assert handler.can_handle("\\[x^2\\]")
    assert handler.can_handle(r"\begin{equation}x^2\end{equation}")

def test_handle_inline_equations(handler):
    # Test basic inline equation
    token, pos = handler.handle("$x^2$")
    assert token == {"type": "equation", "content": "x^2", "display": "inline"}
    assert pos == 5

    # Test inline equation with parentheses
    token, pos = handler.handle(r"\(y^2\)")
    assert token == {"type": "equation", "content": "y^2", "display": "inline"}
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
    assert token == {"type": "equation", "content": "x^2", "display": "block"}
    assert pos == len(content)

    # Test align environment
    content = r"\begin{align}x &= y\end{align}"
    token, pos = handler.handle(content)
    assert token == {"type": "equation", "content": "x &= y", "display": "block"}
    assert pos == len(content)

def test_handle_equations_with_labels(handler):
    # Test equation with label
    content = r"\begin{equation} x^2 \label{eq:square} \end{equation}"
    token, pos = handler.handle(content)
    assert token == {
        "type": "equation",
        "content": "x^2",
        "display": "block",
        "labels": ["eq:square"]
    }
    assert pos == len(content)

def test_handle_empty_equations(handler):
    # Test empty equation
    token, pos = handler.handle("$$$$")
    assert token is None
    assert pos == 4

def test_equation_with_process_fn():
    def mock_process(eq: str) -> str:
        return eq.replace('x', 'y')
    
    handler = EquationHandler(process_content_fn=mock_process)
    token, pos = handler.handle("$x^2$")
    assert token == {"type": "equation", "content": "y^2", "display": "inline"}
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
        "display": "block"
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

if __name__ == "__main__":
    pytest.main([__file__])