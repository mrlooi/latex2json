import pytest
from latex2json.parser.packages.tikz import TikzHandler


def test_tikz_handler_can_handle():
    handler = TikzHandler()

    # Should handle tikz library commands
    assert handler.can_handle(r"\usetikzlibrary{matrix}")
    assert handler.can_handle(r"\usetikzlibrary {matrix}")
    assert handler.can_handle(r"\usetikzlibrary  {matrix}")

    # Should not handle other commands
    assert not handler.can_handle(r"\begin{tikzpicture}")
    assert not handler.can_handle(r"\usepackage{tikz}")


def test_tikz_handler_handle():
    handler = TikzHandler()

    # Test with single library
    text = r"\usetikzlibrary{matrix} some text"
    token, end_pos = handler.handle(text)

    assert token is None  # Handler should ignore tikz library commands
    assert text[end_pos:] == " some text"

    # Test with multiple libraries
    text = r"\usetikzlibrary{matrix,patterns,arrows} more text"
    token, end_pos = handler.handle(text)

    assert token is None
    assert text[end_pos:] == " more text"

    # Test with whitespace variations
    text = r"\usetikzlibrary  {  matrix  ,  patterns  }  remaining text"
    token, end_pos = handler.handle(text)

    assert token is None
    assert text[end_pos:] == "  remaining text"
