import pytest
from latex2json.parser.packages.titlesec import TitlesecHandler


def test_titlespacing():
    text = r"""
\titlespacing*{\paragraph}
{0pt}{3.25ex plus 1ex minus .2ex}{1.5ex plus .2ex} POST
""".strip()

    handler = TitlesecHandler()
    out, end_pos = handler.handle(text)
    assert out is None
    assert text[end_pos:] == " POST"


def test_titleformat():
    text = r"""
\titleformat{\section}[hang]
{\normalfont\Large\bfseries}{\thesection}{1em}{} POST
""".strip()

    handler = TitlesecHandler()
    out, end_pos = handler.handle(text)
    assert out is None
    assert text[end_pos:] == " POST"


def test_titlelabel():
    text = r"""
\titlelabel{(\thesubsection)} POST
""".strip()

    handler = TitlesecHandler()
    out, end_pos = handler.handle(text)
    assert out is None
    assert text[end_pos:] == " POST"


def test_titlecontents():
    text = r"""
\titlecontents{section}[2.3em]
{\normalfont\bfseries}
{\contentslabel{2.3em}}
{\hspace*{-2.3em}}
{\titlerule*[1pc]{.}\contentspage} POST
""".strip()

    handler = TitlesecHandler()
    out, end_pos = handler.handle(text)
    assert out is None
    assert text[end_pos:] == " POST"


def test_titleline():
    text = r"""
\titleline[c]{\titlerule} POST
""".strip()

    handler = TitlesecHandler()
    out, end_pos = handler.handle(text)
    assert out is None
    assert text[end_pos:] == " POST"
