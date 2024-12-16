import pytest
from src.handlers.if_else_statements import IfElseBlockHandler, extract_else_elseif_fi


@pytest.fixture
def handler():
    return IfElseBlockHandler()


def test_simple_if_else():
    text = r"""
\ifsomecondition1
    content1
\else
    content2
\fi

Post IF
""".strip()
    handler = IfElseBlockHandler()
    result, pos = handler.handle(text)

    assert result["condition"] == "somecondition1"
    assert result["if_content"] == "content1"
    assert result["else_content"] == "content2"
    assert result["elsif_branches"] == []

    assert text[pos:].strip() == "Post IF"

    text = r"""
    \@ifsss
    content
    \else
    content2
    \fi
""".strip()
    handler = IfElseBlockHandler()
    result, pos = handler.handle(text)
    assert result["if_content"] == "content"
    assert result["else_content"] == "content2"


def test_if_elsif_else():
    text = r"""
\if{cond1}
    content1
\elseif{cond2}
    content2
\elseif{cond3}
    LAST ELIF
\else
    content4
\fi
""".strip()
    handler = IfElseBlockHandler()
    result, pos = handler.handle(text)

    assert result["condition"] == "{cond1}"
    assert result["if_content"].strip() == "content1"
    assert result["else_content"].strip() == "content4"
    assert len(result["elsif_branches"]) == 2
    assert result["elsif_branches"][0][0] == "{cond2}"
    assert result["elsif_branches"][0][1].strip() == "content2"
    assert result["elsif_branches"][1][0] == "{cond3}"
    assert result["elsif_branches"][1][1].strip() == "LAST ELIF"


def test_nested_if_in_elsif():
    text = r"""
\if{outer}
    outer_content
\elseif{middle}
    \if{inner}
        inner_content
    \else
        inner_else
    \fi
    after_nested
\else
    final_else
\fi
""".strip()
    handler = IfElseBlockHandler()
    result, pos = handler.handle(text)

    assert result["condition"] == "{outer}"
    assert result["if_content"].strip() == "outer_content"
    assert result["else_content"].strip() == "final_else"
    assert len(result["elsif_branches"]) == 1

    elsif_content = result["elsif_branches"][0][1]
    assert r"\if{inner}" in elsif_content
    assert "inner_content" in elsif_content
    assert "inner_else" in elsif_content
    assert "after_nested" in elsif_content


def test_error_unclosed_if():
    text = r"""
\if{unclosed}
    content
\else
    more content
""".strip()
    handler = IfElseBlockHandler()
    token, pos = handler.handle(text)
    assert token is None
    # assert pos == 0


def test_base_if_nested_structure():
    text = r"""
\if{level1}
    \if{level2a}
        nested1
    \else
        nested2
    \fi
\elseif{level1b}
    \if{level2b}
        more_nested
    \elseif{level2c}
        even_more
    \else
        nested_else
    \fi
    after_nested
\else
    final
\fi
""".strip()
    handler = IfElseBlockHandler()
    result, pos = handler.handle(text)

    assert result["condition"] == "{level1}"
    assert r"\if{level2a}" in result["if_content"]
    assert "nested1" in result["if_content"]
    assert "nested2" in result["if_content"]

    elsif_content = result["elsif_branches"][0][1]
    assert r"\if{level2b}" in elsif_content
    assert "more_nested" in elsif_content
    assert "even_more" in elsif_content
    assert "nested_else" in elsif_content
    assert "after_nested" in elsif_content


# def test_ignore_equal():
#     text = r"\equal{cond}{content}"
#     handler = IfElseBlockHandler()
#     result, pos = handler.handle(text)
#     assert result is None
#     assert text[pos:] == "{content}"


def test_ifthenelse():
    text = r"\ifthenelse{cond}{\ifthenelse{inner_cond}{inner_true}{inner_false}}{else_content}"
    handler = IfElseBlockHandler()
    result, pos = handler.handle(text)
    assert result["condition"] == "cond"
    assert result["if_content"] == r"\ifthenelse{inner_cond}{inner_true}{inner_false}"
    assert result["else_content"] == "else_content"


def test_others():
    # ifx
    text = r"""
    \ifx\@h@ld\@empty EERRR 
        aaaa
     \else              
        bbb
     \fi
""".strip()
    handler = IfElseBlockHandler()
    result, pos = handler.handle(text)
    assert result["condition"] == r"\@h@ld\@empty"
    assert result["if_content"].replace(" ", "").replace("\n", "") == "EERRRaaaa"
    assert result["else_content"].replace(" ", "").replace("\n", "") == "bbb"

    text = r"\ifx\@let@token.\else.\null \fi \xspace"
    result, pos = handler.handle(text)
    assert result["condition"] == r"\@let@token."
    assert result["if_content"].strip() == ""
    assert result["else_content"].strip() == r".\null"
    assert text[pos:] == r" \xspace"

    # ifnum
    text = r"\ifnum\lastpenalty=\z@ PENALTY \else NOPE \fi"
    result, pos = handler.handle(text)
    assert result["condition"] == r"\lastpenalty=\z@"
    assert result["if_content"].strip() == "PENALTY"
    assert result["else_content"].strip() == "NOPE"

    text = r"\ifnum 3=\myvar EQUALS 3 \else NOPE \fi"
    result, pos = handler.handle(text)
    assert result["condition"] == r"3=\myvar"
    assert result["if_content"].strip() == "EQUALS 3"
    assert result["else_content"].strip() == "NOPE"

    # ifdefined
    for t in ["\\ifdefined", "\\ifundefined"]:
        text = rf"{t}\@h@ld cccc \else dddd \fi"
        result, pos = handler.handle(text)
        assert result["condition"] == r"\@h@ld"
        assert result["if_content"].strip() == "cccc"
        assert result["else_content"].strip() == "dddd"

    # ifcat
    text = r"\ifcat\lastpenalty\z@ PENALTY \else NOPE \fi"
    result, pos = handler.handle(text)
    assert result["condition"] == r"\lastpenalty\z@"
    assert result["if_content"].strip() == "PENALTY"
    assert result["else_content"].strip() == "NOPE"

    text = r"\ifcat _\ssss aaaa \else bbb \fi"
    result, pos = handler.handle(text)
    assert result["condition"] == r"_\ssss"
    assert result["if_content"].strip() == "aaaa"
    assert result["else_content"].strip() == "bbb"

    # ifdim
    text = r"\ifdim 3pt<\hsize EQUALS 3 \else NOPE \fi"
    result, pos = handler.handle(text)
    assert result["condition"] == r"3pt<\hsize"
    assert result["if_content"].strip() == "EQUALS 3"
    assert result["else_content"].strip() == "NOPE"

    text = r"\ifdim\myvar=3pt EQUALS 3 \else NOPE \fi"
    result, pos = handler.handle(text)
    assert result["condition"] == r"\myvar=3pt"
    assert result["if_content"].strip() == "EQUALS 3"
    assert result["else_content"].strip() == "NOPE"


def test_nested_multi_if_type_structure():
    text = r"""
\ifx\first\empty
    First 
    \ifnum\second<2
        Inner second
    \else
        Inner else
    \fi
\else
    bbb
\fi

post
""".strip()
    handler = IfElseBlockHandler()
    result, pos = handler.handle(text)
    assert result["condition"] == r"\first\empty"

    if_content = result["if_content"]
    assert r"\ifnum\second<2" in if_content
    assert "Inner second" in if_content
    assert "Inner else" in if_content
    assert if_content.strip().endswith(r"\fi")

    assert result["else_content"].strip() == "bbb"
    assert text[pos:].strip() == "post"


def test_with_process_newif():
    handler = IfElseBlockHandler()
    handler.process_newif("test")
    assert handler.has_if("test")

    text = r"""
    \iftest TRUE \else FALSE \fi 
""".strip()
    result, pos = handler.handle(text)
    assert result["condition"] == r"test"
    assert result["if_content"].strip() == "TRUE"
    assert result["else_content"].strip() == "FALSE"

    handler.clear()
    assert not handler.has_if("test")


def test_ifcase():
    text = r"""
\ifcase\value{counter}
  case 0
\or One
  case 1
\or Two
  case 2
\else
  default
\fi
""".strip()
    handler = IfElseBlockHandler()
    result, pos = handler.handle(text)
    assert result["condition"] == r"\value{counter}"
    assert result["if_content"].strip() == "case 0"
    assert result["elsif_branches"][0][1].strip() == "case 1"
    assert result["elsif_branches"][1][1].strip() == "case 2"
    assert result["else_content"].strip() == "default"


def test_with_csname():
    text = r"""\ifx\csname urlstyle\endcsname\relax\fi POST""".strip()
    handler = IfElseBlockHandler()
    result, pos = handler.handle(text)
    assert result["else_content"] == ""
    assert text[pos:] == " POST"
