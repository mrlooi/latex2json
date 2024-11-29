import pytest
from src.handlers.legacy_formatting import LegacyFormattingHandler


@pytest.fixture
def handler():
    return LegacyFormattingHandler()


def test_can_handle_valid_commands(handler):
    assert handler.can_handle(r"\bf text}")
    assert handler.can_handle(r"\it text}")
    assert handler.can_handle(r"\large text")


def test_can_handle_invalid_commands(handler):
    assert not handler.can_handle(r"\unknown text}")
    assert not handler.can_handle(r"{text}")
    assert not handler.can_handle(r"haha")


def test_handle_valid_commands(handler):
    text = r"\bf{Hii} bro"
    out, end_pos = handler.handle(text)
    assert out == r"\textbf{Hii}"
    assert text[end_pos:] == " bro"

    text = r"\huge HUGEEE"
    out, end_pos = handler.handle(text)
    assert out == r"\texthuge{HUGEEE}"
    assert text[end_pos:] == ""

    # capture up to trailing closing brace
    text = r"\bf Hello my name isssdas} hahaha"
    out, end_pos = handler.handle(text)
    assert out == r"\textbf{Hello my name isssdas}"
    assert text[end_pos:] == "} hahaha"

    # capture up to next same font command
    text = r"\bf Hello my name {sa} asdsd \sf asdad"
    out, end_pos = handler.handle(text)
    assert out == r"\textbf{Hello my name {sa} asdsd }"
    assert text[end_pos:] == r"\sf asdad"

    # capture up to next same size command (notice the font command \sc is not competing)
    text = r"\small Hello my name {sa} \sc something \large large"
    out, end_pos = handler.handle(text)
    assert out == r"\textsmall{Hello my name {sa} \sc something }"
    assert text[end_pos:] == r"\large large"

    # test with numbers etc after
    text = r"\bf1 hello } ejje"
    out, end_pos = handler.handle(text)
    assert out == r"\textbf{1 hello }"
    assert text[end_pos:] == "} ejje"

    # test with numbers etc after
    text = r"\bf123 { hello }"
    out, end_pos = handler.handle(text)
    assert out == r"\textbf{123 { hello }}"
    assert text[end_pos:] == ""
