import pytest
from latex2json.parser.handlers.new_definition import NewDefinitionHandler
from latex2json.parser.handlers.command_processor import CommandProcessor
import re


@pytest.fixture
def processor():
    return CommandProcessor()


@pytest.fixture
def newdef_handler():
    return NewDefinitionHandler()


def test_handle_newcommand(processor, newdef_handler):
    processor.clear()

    # Test basic newcommand
    content = r"\newcommand{\cmd}{some definition}"
    token, pos = newdef_handler.handle(content)
    assert token is not None

    processor.process_newcommand(
        token["name"],
        token["content"],
        token["num_args"],
        token["defaults"],
        token["usage_pattern"],
    )

    text = r"\cmd haha"
    out_text, pos = processor.handle(text)
    assert out_text == "some definition"
    assert text[pos:] == " haha"

    # test with optional braces
    text = r"\cmd{} haha"
    out_text, pos = processor.handle(text)
    assert out_text == "some definition"
    assert text[pos:] == "{} haha"

    # test with args
    content = r"\newcommand{\cmdWithArgs}[2]{arg1=#1, arg2=#2}"
    token, pos = newdef_handler.handle(content)
    assert token is not None

    processor.process_newcommand(
        token["name"],
        token["content"],
        token["num_args"],
        token["defaults"],
        token["usage_pattern"],
    )

    # Test with required arguments
    text = r"\cmdWithArgs{first}{second} remaining"
    out_text, pos = processor.handle(text)
    assert out_text == "arg1=first, arg2=second"
    assert text[pos:] == " remaining"

    # defaults to empty str if required arg not supplied
    text = r"\cmdWithArgs{first} remaining"
    out_text, pos = processor.handle(text)
    assert out_text == "arg1=first, arg2="
    assert text[pos:] == " remaining"


def test_paired_delimiter(processor, newdef_handler):
    processor.clear()

    content = r"\DeclarePairedDelimiter{\br}{(}{)}"
    token, pos = newdef_handler.handle(content)
    assert token is not None

    processor.process_paired_delimiter(
        token["name"], token["left_delim"], token["right_delim"]
    )

    content = r"\br{x} POST"
    out_text, pos = processor.handle(content)
    assert out_text == r"(x)"
    assert content[pos:] == " POST"


def test_expand_commands(processor, newdef_handler):
    processor.clear()

    content = r"\DeclarePairedDelimiter{\br}{(}{)}"
    token, pos = newdef_handler.handle(content)
    assert token is not None

    processor.process_paired_delimiter(
        token["name"], token["left_delim"], token["right_delim"]
    )

    content = r"$\br{x}$"
    out_text, _ = processor.expand_commands(content, math_mode=False)
    assert out_text == r"$(x)$"

    # math mode = True pads the output with spaces
    out_text, _ = processor.expand_commands(
        content, ignore_unicode=True, math_mode=True
    )
    assert out_text == r"$( x )$"


if __name__ == "__main__":
    pytest.main([__file__])
