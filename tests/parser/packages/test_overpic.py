import pytest
from latex2json.parser.packages.overpic import OverpicHandler


def test_overpic_handler_can_handle():
    handler = OverpicHandler()

    # Should handle overpic environments
    assert handler.can_handle(r"\begin{overpic}")
    assert handler.can_handle(r"\begin {overpic}")
    assert handler.can_handle(r"\begin  {overpic}")

    # Should not handle other environments
    assert not handler.can_handle(r"\begin{figure}")
    assert not handler.can_handle(r"\includegraphics")


def test_overpic_handler_handle():
    handler = OverpicHandler()

    # Test with content after the environment
    text = r"""
    \begin{overpic}[width=0.5\textwidth]{example-image}
    \put(33,29){\tiny Faster R-CNN}
    \end{overpic} 
    POST
    """.strip()
    token, end_pos = handler.handle(text)

    assert token is not None
    assert token["type"] == "includegraphics"
    assert token["content"] == "example-image"
    assert text[end_pos:].strip() == "POST"
