import pytest
from latex2json.latex_maps.latex_unicode_converter import LatexUnicodeConverter


@pytest.fixture
def converter():
    return LatexUnicodeConverter()


def test_basic_conversion(converter):
    assert converter.convert(r"\textbackslash") == "\\"
    assert converter.convert(r"\#") == "#"
    assert converter.convert(r"\$") == "$"
    assert converter.convert(r"\textpm") == "±"
    assert converter.convert(r"\{ssss\}") == "{ssss}"
    assert converter.convert(r"\S1") == "§1"
    assert converter.convert(r"\dots@") == "...@"
    assert converter.convert(r"\L{}") == "Ł"
    assert converter.convert(r"\textbackslash{}") == "\\"


def test_accented_characters(converter):
    assert converter.convert(r"\H{o}") == "ő"
    assert converter.convert(r"\v{l}") == "ľ"
    assert converter.convert(r"\'{A}") == "Á"


def test_special_letters(converter):
    assert converter.convert(r"\oe") == "œ"
    assert converter.convert(r"\O") == "Ø"
    assert converter.convert(r"\L") == "Ł"
    assert converter.convert(r"\ij") == "ĳ"


def test_multiple_conversions_in_text(converter):
    input_text = r"This is a test \textbackslash with Erd\H{o}s some commands"
    expected = "This is a test \\ with Erdős some commands"
    assert converter.convert(input_text) == expected


def test_currency_symbols(converter):
    assert converter.convert(r"\textdollar") == "$"
    assert converter.convert(r"\textyen") == "¥"
    input_text = r"Multiple \textdollar \textyen symbols"
    expected = "Multiple $ ¥ symbols"
    assert converter.convert(input_text) == expected


def test_math_symbols(converter):
    assert converter.convert(r"\mathbb{E}") == "𝔼"
    assert converter.convert(r"\mathtt{0}") == "𝟶"
    input_text = r"\mathtt{0}\mathbb{E}f"
    expected = "𝟶𝔼f"
    assert converter.convert(input_text) == expected


def test_consecutive_commands(converter):
    input_text = r"\v{l} \l \ij \o \O \L \Leee"
    expected = r"ľ ł ĳ ø Ø Ł \Leee"
    assert converter.convert(input_text) == expected


def test_empty_string(converter):
    assert converter.convert("") == ""


def test_plain_text_no_commands(converter):
    input_text = "This is plain text without any LaTeX commands"
    assert converter.convert(input_text) == input_text


def test_ensuremath_commands(converter):
    input_text = r"\succnsim"
    expected = "⋩"  # This might need adjustment based on actual mapping
    assert converter.convert(input_text) == expected


def test_font_commands(converter):
    input_text = r"{{\fontencoding{LELA}\selectfont\char40}}"
    expected = "{Ħ}"
    assert converter.convert(input_text) == expected
