import pytest
from latex2json.parser.handlers.text_formatting import (
    TextFormattingHandler,
    FRONTEND_STYLE_MAPPING,
)


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


def test_handle_outputs(handler):
    text = r"\textbf{hello} sss"
    out, end_pos = handler.handle(text)
    assert out == {
        "type": "text",
        "styles": [FRONTEND_STYLE_MAPPING["textbf"]],
        "content": "hello",
    }
    assert text[end_pos:] == " sss"

    text = r"\textsc ABC"
    out, end_pos = handler.handle(text)
    assert out == {
        "type": "text",
        "styles": [FRONTEND_STYLE_MAPPING["textsc"]],
        "content": "A",
    }
    assert text[end_pos:] == "BC"

    text = r"\textsuperscript{123}"
    out, end_pos = handler.handle(text)
    assert out == {
        "type": "text",
        "styles": [FRONTEND_STYLE_MAPPING["textsuperscript"]],
        "content": "123",
    }

    #     r"\textbf123 {sds}",
    # r"\textbf {sds",
    # r"\textbf",
    # r"\textbf{",
    # r"\textbfsss",

    text = r"\textbf123 {sds}"
    out, end_pos = handler.handle(text)
    assert out == {
        "type": "text",
        "styles": [FRONTEND_STYLE_MAPPING["textbf"]],
        "content": "1",
    }
    assert text[end_pos:] == "23 {sds}"

    # no proper closing brace, only capture up to first brace
    text = r"\textbf {sds"
    out, end_pos = handler.handle(text)
    assert out == {
        "type": "text",
        "styles": [FRONTEND_STYLE_MAPPING["textbf"]],
        "content": "{",
    }
    assert text[end_pos:] == "sds"

    # no args
    text = r"\textbf"
    out, end_pos = handler.handle(text)
    assert out == {
        "type": "text",
        "styles": [FRONTEND_STYLE_MAPPING["textbf"]],
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

    text = r"\text{sds} pos"
    out, end_pos = handler.handle(text)
    assert out == {"type": "text", "content": "sds"}
    assert text[end_pos:] == " pos"

    text = r"\natexlab{123}"
    out, end_pos = handler.handle(text)
    assert out == {"type": "text", "content": "123"}
    assert text[end_pos:] == ""


def test_frac(handler):
    assert not handler.can_handle(r"\fracsss{pdf version}{text version}")

    text = r"\frac{1}{2} postfrac"
    out, end_pos = handler.handle(text)
    assert out == {"type": "text", "content": "1 / 2"}
    assert text[end_pos:] == " postfrac"

    text = r"""
    \nicefrac{
        FIRST    
        BLOCK
    } {
        SECOND
        BLOCK
    }after frac
""".strip()
    out, end_pos = handler.handle(text)
    assert out == {"type": "text", "content": "FIRST BLOCK / SECOND BLOCK"}
    assert text[end_pos:] == "after frac"

    # frac in frac
    text = r"\textfrac{1}{\frac{2}{3}} postfrac"
    out, end_pos = handler.handle(text)
    assert out == {"type": "text", "content": r"1 / \frac{2}{3}"}
    assert text[end_pos:] == " postfrac"


def test_texorpdfstring(handler):
    assert not handler.can_handle(r"\texorpdfstringssss{pdf version}{text version}")

    text = r"\texorpdfstring{pdf version}{text version} postfrac"
    out, end_pos = handler.handle(text)
    assert out == {"type": "text", "content": "text version"}
    assert text[end_pos:] == " postfrac"


def test_ignore_custom_fonts(handler):
    text = r"\usefont{T1}{phv}{b}{n} This text s"
    token, pos = handler.handle(text)
    assert token is None
    assert text[pos:] == " This text s"

    text = r"\selectfont This text s"
    token, pos = handler.handle(text)
    assert token is None
    assert text[pos:] == " This text s"

    text = r"\fontsize{12pt}{14pt} This text s"
    token, pos = handler.handle(text)
    assert token is None
    assert text[pos:] == " This text s"


def test_color(handler):
    text = r"\textcolor{red}{This text s} POST"
    token, pos = handler.handle(text)
    assert token["styles"] == ["color=red"]
    assert token["content"] == "This text s"
    assert text[pos:] == " POST"

    text = r"\textcolor[HTML]{FF0000}{This text s} POST"
    token, pos = handler.handle(text)
    assert token["styles"] == ["color={HTML:FF0000}"]
    assert token["content"] == "This text s"
    assert text[pos:] == " POST"


def test_columns(handler):
    text = r"\onecolumn POST"
    token, pos = handler.handle(text)
    assert text[pos:] == " POST"

    text = r"\twocolumn[This text s] POST"
    token, pos = handler.handle(text)
    assert token["content"] == "This text s"
    assert text[pos:] == " POST"


def test_subfloat(handler):
    text = r"\subfloat[Caption]{Content} POST"
    token, pos = handler.handle(text)
    assert token["type"] == "group"
    assert token["content"] == [
        {"type": "caption", "content": [{"type": "text", "content": "Caption"}]},
        {"type": "text", "content": "Content"},
    ]
    assert text[pos:] == " POST"


def test_roman_numerals(handler):
    text = r"\romannumeral 123 POST"
    token, pos = handler.handle(text)
    assert token["type"] == "text"
    assert token["content"] == "cxxiii"
    assert text[pos:] == " POST"


def test_upper_lower_case(handler):
    text = r"\uppercase{Hello} POST"
    token, pos = handler.handle(text)
    assert token["type"] == "text"
    assert token["content"] == "Hello"
    assert token["styles"] == ["uppercase"]
    assert text[pos:] == " POST"

    text = r"\lowercase\expandafter{Hello} POST"
    token, pos = handler.handle(text)
    assert token["type"] == "text"
    assert token["content"] == "Hello"
    assert token["styles"] == ["lowercase"]
    assert text[pos:] == " POST"
