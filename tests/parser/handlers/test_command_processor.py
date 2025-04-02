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

    # math mode = True pads the output with braces
    out_text, _ = processor.expand_commands(
        content, ignore_unicode=True, math_mode=True
    )
    assert out_text == r"$({x})$"


def test_expand_commands_math_mode(processor, newdef_handler):
    processor.clear()

    commands = [
        r"\newcommand{\ti}{\tilde}",
        r"\newcommand{\calR}{\mathcal R}",
        r"\newcommand{\gab}{g^{\alpha\beta}}",
        r"\newcommand{\paa}{\partial_\alpha}",
        r"\newcommand{\f}{\frac}",
    ]

    for cmd in commands:
        token, pos = newdef_handler.handle(cmd)
        assert token is not None
        processor.process_newcommand(
            token["name"],
            token["content"],
            token["num_args"],
            token["defaults"],
            token["usage_pattern"],
        )

    # test \tilde is not wrapped in braces
    content = r"\ti{3}"
    out_text, _ = processor.expand_commands(
        content, ignore_unicode=True, math_mode=True
    )
    assert out_text == r"\tilde{3}"

    # test \mathcal is wrapped in braces since it has a space
    content = r"\frac\calR 2"
    out_text, _ = processor.expand_commands(
        content, ignore_unicode=True, math_mode=True
    )
    assert out_text == r"\frac{\mathcal R} 2"

    # test \gab is wrapped in braces since it doesn't start with \
    content = r"\paa\gab"
    out_text, _ = processor.expand_commands(
        content, ignore_unicode=True, math_mode=True
    )
    assert out_text == r"\partial_\alpha{g^{\alpha\beta}}"

    # test if prefix _ or ^ is wrapped in braces
    content = r"\Delta^\paa"
    out_text, _ = processor.expand_commands(
        content, ignore_unicode=True, math_mode=True
    )
    assert out_text == r"\Delta^{\partial_\alpha}"

    # check \f not wrapped in braces
    content = r"x^\f{1}{2}"
    out_text, _ = processor.expand_commands(
        content, ignore_unicode=True, math_mode=True
    )
    assert out_text == r"x^\frac{1}{2}"


def test_ifstar_definitions(processor, newdef_handler):
    processor.clear()

    content = r"\newcommand{\cmd}{\@ifstar{star}{nostar}}"
    token, pos = newdef_handler.handle(content)
    assert token is not None

    processor.process_newcommand(
        token["name"],
        token["content"],
        token["num_args"],
        token["defaults"],
        token["usage_pattern"],
    )

    assert not processor.can_handle(r"\cmda")

    text = r"\cmd* haha"
    out_text, pos = processor.handle(text)
    assert out_text == "star"
    assert text[pos:] == " haha"

    text = r"\cmd haha"
    out_text, pos = processor.handle(text)
    assert out_text == "nostar"
    assert text[pos:] == " haha"

    # now test with \def
    content = r"\def\cmdxx{\@ifstar{defstar}{nodefstar}}"
    token, pos = newdef_handler.handle(content)
    assert token is not None

    processor.process_newdef(
        token["name"],
        token["content"],
        token["num_args"],
        token["usage_pattern"],
        token["is_edef"],
    )

    text = r"\cmdxx* haha"
    out_text, pos = processor.handle(text)
    assert out_text == "defstar"
    assert text[pos:] == " haha"

    text = r"\cmdxx haha"
    out_text, pos = processor.handle(text)
    assert out_text == "nodefstar"
    assert text[pos:] == " haha"


def test_comparison_operators(processor, newdef_handler):
    processor.clear()

    content = r"\newcommand{\foo}{1}"
    token, pos = newdef_handler.handle(content)
    assert token is not None

    processor.process_newcommand(
        token["name"],
        token["content"],
        token["num_args"],
        token["defaults"],
        token["usage_pattern"],
    )

    # check operator and ignore
    text = r"\foo = 2 POST"
    out_text, pos = processor.handle(text)
    assert out_text == ""
    assert text[pos:] == " POST"

    text = r"\foo = 2.5pt POST"
    out_text, pos = processor.handle(text)
    assert out_text == ""
    assert text[pos:] == " POST"

    text = r"\foo=\somecmd POST"
    out_text, pos = processor.handle(text)
    assert out_text == ""
    assert text[pos:] == " POST"


def test_nested_command_arg_substitution(processor, newdef_handler):
    processor.clear()

    content = r"""
    \newcommand{\outermacro}[2]{
        Outer parameters: #1 and #2

        \newcommand{\innermacro}[2]{
            Outer-inner parameters: #1 and #2
            Inner parameters: ##1 and ##2 \##1
        }
    }
    """.strip()
    token, pos = newdef_handler.handle(content)
    assert token is not None

    processor.process_newcommand(
        token["name"],
        token["content"],
        token["num_args"],
        token["defaults"],
        token["usage_pattern"],
    )

    text = r"\outermacro{outer-first}{outer-second}"
    out_text, pos = processor.handle(text)
    out_text = out_text.strip()
    assert out_text.startswith("Outer parameters: outer-first and outer-second")

    expected_inner = r"""
        \newcommand{\innermacro}[2]{
            Outer-inner parameters: outer-first and outer-second
            Inner parameters: ##1 and ##2 \#outer-first
        }
    """.strip()
    assert out_text.endswith(expected_inner)

    # now add the inner macro
    token, pos = newdef_handler.handle(expected_inner)
    assert token is not None

    processor.process_newcommand(
        token["name"],
        token["content"],
        token["num_args"],
        token["defaults"],
        token["usage_pattern"],
    )

    text = r"\innermacro{inner-first}{inner-second}"
    out_text, pos = processor.handle(text)
    out_text = out_text.strip()
    assert out_text.startswith(r"Outer-inner parameters: outer-first and outer-second")
    assert out_text.endswith(
        r"Inner parameters: inner-first and inner-second \#outer-first"
    )


if __name__ == "__main__":
    pytest.main([__file__])
