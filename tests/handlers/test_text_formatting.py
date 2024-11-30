import pytest
from src.handlers.text_formatting import TextFormattingHandler, FRONTEND_STYLE_MAPPING


@pytest.fixture
def handler():
    return TextFormattingHandler()


def test_can_handle_valid(handler):
    assert handler.can_handle(r"\textbf{text}")
    assert handler.can_handle(r"\textsc sss")
    assert handler.can_handle(r"\textlarge {text}")


def test_can_handle_invalid(handler):
    assert not handler.can_handle(r"\textbfa")
    assert not handler.can_handle(r"\unknown text}")
    assert not handler.can_handle(r"{\text")


OUTPUT_TYPE = "styled"


def test_handle_outputs(handler):
    text = r"\textbf{hello} sss"
    out, end_pos = handler.handle(text)
    assert out == {
        "type": OUTPUT_TYPE,
        "style": FRONTEND_STYLE_MAPPING["textbf"],
        "content": "hello",
    }
    assert text[end_pos:] == " sss"

    text = r"\textsc ABC"
    out, end_pos = handler.handle(text)
    assert out == {
        "type": OUTPUT_TYPE,
        "style": FRONTEND_STYLE_MAPPING["textsc"],
        "content": "A",
    }
    assert text[end_pos:] == "BC"

    #     r"\textbf123 {sds}",
    # r"\textbf {sds",
    # r"\textbf",
    # r"\textbf{",
    # r"\textbfsss",

    text = r"\textbf123 {sds}"
    out, end_pos = handler.handle(text)
    assert out == {
        "type": OUTPUT_TYPE,
        "style": FRONTEND_STYLE_MAPPING["textbf"],
        "content": "1",
    }
    assert text[end_pos:] == "23 {sds}"

    # no proper closing brace, only capture up to first brace
    text = r"\textbf {sds"
    out, end_pos = handler.handle(text)
    assert out == {
        "type": OUTPUT_TYPE,
        "style": FRONTEND_STYLE_MAPPING["textbf"],
        "content": "{",
    }
    assert text[end_pos:] == "sds"

    # no args
    text = r"\textbf"
    out, end_pos = handler.handle(text)
    assert out == {
        "type": OUTPUT_TYPE,
        "style": FRONTEND_STYLE_MAPPING["textbf"],
        "content": "",
    }
    assert text[end_pos:] == ""

    # test empty content
    text = r"\textbf{   } afterwards"
    out, end_pos = handler.handle(text)
    assert out is None
    assert text[end_pos:] == " afterwards"

    # different command
    text = r"\textbfsss{}"
    out, end_pos = handler.handle(text)
    assert out is None
    assert end_pos == 0
