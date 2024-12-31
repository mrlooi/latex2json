import pytest
from src.parser.handlers.legacy_formatting import LegacyFormattingHandler


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

    text = r"\tiny tiny \large large X"
    out, end_pos = handler.handle(text)
    assert out == r"\texttiny{tiny }"
    assert text[end_pos:] == r"\large large X"

    text = text[end_pos:]
    out, end_pos = handler.handle(text)
    assert out == r"\textlarge{large X}"
    assert text[end_pos:] == ""


def test_complex_non_nested_cases(handler):
    # here, \large is not competing with the inner \tiny, because \tiny is nested inside \textbf
    text = r"\large \textbf{\tiny inner} middle \huge last_huge"
    out, end_pos = handler.handle(text)
    assert out == r"\textlarge{\textbf{\tiny inner} middle }"

    assert text[end_pos:] == r"\huge last_huge"

    # first \large and 2nd \tiny are useless here due to 3rd \large
    text = r"""
    \large
    \tiny
    \large {
    \sc{hello}
    }

    Outside block
    """.strip()
    out, end_pos = handler.handle(text)
    assert out == r"\textlarge{}"
    assert text[end_pos:].startswith(r"\tiny")

    text = text[end_pos:]
    out, end_pos = handler.handle(text)
    assert out == r"\texttiny{}"
    assert text[end_pos:].startswith(r"\large")

    text = text[end_pos:]
    out, end_pos = handler.handle(text)
    assert out.replace("\n", "").strip() == r"\textlarge{\sc{hello}}"
    # assert out == r"\textlarge{}"

    assert text[end_pos:].strip() == "Outside block"


def test_pre_mathmode_cases(handler):
    text = r"\boldmath $1+1=2$"
    out, end_pos = handler.handle(text)
    assert out == r"\textbf{$1+1=2$}"

    text = r"\unboldmath $1+1=2$"
    out, end_pos = handler.handle(text)
    assert out == r"\textrm{$1+1=2$}"

    text = r"\mathversion{bold} $1+1=2$"
    out, end_pos = handler.handle(text)
    assert out == r"\textbf{$1+1=2$}"

    text = r"\mathversion{normal} $1+1=2$"
    out, end_pos = handler.handle(text)
    assert out == r"\textrm{$1+1=2$}"


def test_nested_cases(handler):
    tabular_content = r"""
\begin{center}
\begin{tabular}{l|c c}
\hline
\large 1 % notice the large here should be contained
\end{tabular}
\end{center}
""".strip()
    text = (
        r"""\small
    %s

    helloworld
    \huge HUGE
    """
        % (tabular_content)
    ).strip()
    out, end_pos = handler.handle(text)
    out = out.strip().replace("\n", "")
    assert out.startswith(r"\textsmall{%s" % (tabular_content.replace("\n", "")))
    assert out.replace(" ", "").endswith("helloworld}")

    assert text[end_pos:].strip() == r"\huge HUGE"
