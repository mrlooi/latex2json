import pytest
from latex_parser.parser.handlers.text_formatting import (
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


def test_box_commands(handler):
    # Test that box commands only return their text content
    test_cases = [
        (r"\makebox{Simple text}", "Simple text"),
        (r"\framebox{Simple text}", "Simple text"),
        (r"\raisebox{2pt}{Raised text}", "Raised text"),
        (r"\makebox[3cm]{Fixed width}", "Fixed width"),
        (r"\framebox[3cm][l]{Left in frame}", "Left in frame"),
        (r"\parbox{5cm}{Simple parbox text}", "Simple parbox text"),
        (r"\parbox[t][3cm][s]{5cm}{Stretched vertically}", "Stretched vertically"),
        (r"\fbox{Framed text}", "Framed text"),
        (r"\colorbox{yellow}{Colored box}", "Colored box"),
        (
            r"\parbox[c][3cm]{5cm}{Center aligned with fixed height}",
            "Center aligned with fixed height",
        ),
        (
            r"""\mbox{
            All
            One line ajajaja
            }""",
            "All One line ajajaja",
        ),
        (r"\hbox to 3in{Some text}", "Some text"),
        (r"\sbox\@tempboxa{Some text}", "Some text"),
        (r"\pbox{3cm}{Some text}", "Some text"),
    ]

    for command, expected_text in test_cases:
        token, pos = handler.handle(command)
        assert token and token["content"].strip() == expected_text
        assert pos > 0  # Should advance past the command

    text = r"""
    \parbox[c][3cm]{5cm}{Center aligned with fixed height} STUFF AFTER
    """.strip()
    token, pos = handler.handle(text)
    assert token and token["content"].strip() == "Center aligned with fixed height"
    assert text[pos:] == " STUFF AFTER"


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
