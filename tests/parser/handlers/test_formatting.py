import datetime
import pytest
from latex2json.parser.handlers.formatting import (
    FormattingHandler,
    strip_trailing_number_from_token,
)


@pytest.fixture
def handler():
    return FormattingHandler()


def test_can_handle_formatting(handler):
    # Test formatting commands
    assert handler.can_handle(r"\centering")
    assert handler.can_handle(r"\raggedright")
    assert handler.can_handle(r"\noindent")
    assert handler.can_handle(r"\clearpage")
    assert handler.can_handle(r"\linebreak")
    assert handler.can_handle(r"\bigskip")
    assert not handler.can_handle("regular text")


def test_can_handle_comments(handler):
    assert handler.can_handle("% This is a comment")
    assert handler.can_handle("%Another comment")
    assert not handler.can_handle("Not a % comment")


def test_can_handle_separators(handler):
    # Test various separator commands
    assert handler.can_handle(r"\hline")
    assert handler.can_handle(r"\cline{2-4}")
    assert handler.can_handle(r"\midrule")
    assert handler.can_handle(r"\toprule")
    assert handler.can_handle(r"\bottomrule")
    assert handler.can_handle(r"\cmidrule{1-2}")
    assert handler.can_handle(r"\cmidrule[2pt]{1-2}")
    assert handler.can_handle(r"\hdashline")
    assert handler.can_handle(r"\cdashline{2-4}")
    assert handler.can_handle(r"\specialrule{.2em}{.1em}{.1em}")
    assert handler.can_handle(r"\addlinespace")
    assert handler.can_handle(r"\addlinespace[5pt]")
    assert handler.can_handle(r"\morecmidrules")


def test_handle_formatting_commands(handler):
    # Test handling of formatting commands
    token, pos = handler.handle(r"\centering Some text")
    # assert token is None
    assert pos == len(r"\centering")  # Length of "\centering"

    token, pos = handler.handle(r"\noindent Text")
    # assert token is None
    assert pos == len(r"\noindent")  # Length of "\noindent"


def test_handle_comments(handler):
    # Test handling of comments
    comment = "% This is a comment\nNext line"
    token, pos = handler.handle(comment)
    # assert token is None
    assert pos == len(comment.split("\n")[0])  # Length of comment up to \n


def test_handle_numbers(handler):
    token, pos = handler.handle(r"\num[round-precision=1]{1.33}")
    assert token["content"] == "1.3"


def test_handle_separators(handler):
    # Test handling of separator commands
    token, pos = handler.handle(r"\hline some text")
    # assert token is None
    assert pos == len(r"\hline")

    token, pos = handler.handle(r"\cline{2-4} text")
    # assert token is None
    assert pos == len(r"\cline{2-4}")

    token, pos = handler.handle(r"\midrule[2pt] text")
    # assert token is None
    assert pos == len(r"\midrule[2pt]")


def test_handle_invalid_input(handler):
    # Test with non-command content
    token, pos = handler.handle("regular text")
    # assert token is None
    assert pos == 0


def test_handle_color_commands(handler):
    color_text = r"""
% 1. Color packages and their commands
% xcolor package adds these:
\rowcolor{gray}               % Table row color
\columncolor{blue}            % Table column color
\cellcolor{red}               % Single cell color
\cellcolor[HTML]{656565}{Hi}
"""

    lines = color_text.strip().split("\n")
    lines = [
        line.strip()
        for line in lines
        if line.strip() and not line.strip().startswith("%")
    ]
    for line in lines:
        token, pos = handler.handle(line)
        # assert token is None
        assert pos > 0


def test_spacing_commands(handler):
    def check_token(token, pos, s=" "):
        assert token["type"] == "text"
        assert token["content"] == s
        assert pos > 0

    token, pos = handler.handle(r"\hspace{10pt}")
    check_token(token, pos)

    token, pos = handler.handle(r"\quad")
    check_token(token, pos)

    token, pos = handler.handle(r"\,")
    check_token(token, pos)

    token, pos = handler.handle(r"\:")
    check_token(token, pos)

    token, pos = handler.handle(r"\;")
    check_token(token, pos)

    text = r"\!  aaa"
    token, pos = handler.handle(text)
    assert token is None
    assert text[pos:] == "  aaa"

    text = r"\vspace{10pt} postvspace"
    token, pos = handler.handle(text)
    check_token(token, pos, "\n")
    assert text[pos:] == " postvspace"


def test_date_command(handler):

    text = r"\date{2024-11-29} sss"
    token, end_pos = handler.handle(text)
    # assert token == {"type": "date", "content": "2024-11-29"}
    assert text[end_pos:] == " sss"

    text = r"\date{} sss"
    token, end_pos = handler.handle(text)
    # assert token == {"type": "date", "content": ""}
    assert text[end_pos:] == " sss"

    text = r"\today sss"
    token, end_pos = handler.handle(text)
    # assert token == {
    #     "type": "date",
    #     "content": datetime.datetime.now().strftime("%Y-%m-%d"),
    # }
    assert text[end_pos:] == " sss"


def test_misc_formatting_commands(handler):
    text = r"""
    \hypersetup{colorlinks,linkcolor={blue},citecolor={blue},urlcolor={red}}  
    \pagestyle{empty}
    \numberwithin{equation}{section}
    \theoremstyle{conjecture}
    \noindent
    \bibliographystyle{plain}
    \abovedisplayskip
    \belowdisplayshortskip
    \urlstyle{same}
    \pdfoutput=1
    \pdfsuppresswarningpagegroup=1
    \lstset{breaklines=true, style=\color{blue}}
    \fboxsep{1pt}
    \value{section}
    \allowdisplaybreaks
    \itemsep=0pt
    \itemsep-0.2em

    \topmargin 0.0cm
    \oddsidemargin 0.2cm
    \textwidth 16cm 
    \textheight 21cm
    \footskip 1.0cm
    \linewidth
    \addtocontents{toc}{\protect\setcounter{tocdepth}{1}}
    \protect\setcounter{tocdepth}{1}
    \protect\foo
    \protect\command{arg}
    \specialrule{.2em}{.1em}{.1em}
    \addtocounter{figure}{-2}
    \colrule
    \rightmargin
    \leftmargin
    \captionsetup[figure]{labelsep=quad}
    \captionsetup{font={small}}
    \thispagestyle{empty}

    \DeclareOption*{\PassOptionsToClass{\CurrentOption}{article}}
    \DeclareOption{tocmacros}{\AtEndOfClass{\toc@setup@predefines}}
    \DeclareGraphicsExtensions{.mps}

    \ProcessOptions
    \PassOptionsToPackage{fleqn}{amsmath}
    \PassOptionsToClass{fleqn}{amsmath}

    \NeedsTeXFormat{LaTeX2e}
    \ProvidesClass{sigma}[2012/01/18]
    \vskip -\parskip

    \parindent 4mm
    \parskip    4mm
    
    \vskip 10pt
    \vskip10pt
    \labelsep
    \topsep
    \relax
    \linenumbers
    \linebreak
    \linebreak[1]
    \smallbreak
    \bigbreak
    \p@
    \z@
    5\p@
    10\z@
    \enlargethispage{2\baselineskip}
    \baselineskip
    \baselineskip 18pt
    2\baselineskip
    \lineskip .75em

    \advance by
    \divide by
    \multiply by
    \advance\@tempskipa-\@tempdimb
    \advance\section@level-\subsection@level
    \advance\leftmargin by -\rightmargin
    \advance\topskip-1cm

    \hyphenation{identity notorious underlying surpasses desired residual doubled}

    \DeclareFontFamily{OT1}{rsfs}{}
    \DeclareFontShape{OT1}{rsfs}{n}{it}{<-> rsfs10}{}
    \SetMathAlphabet{\mathscr}{OT1}{rsfs}{n}{it}{xxx}
    \DeclareSymbolFont{bbold}{U}{bbold}{m}{n}
    
    \renewbibmacro{in:}{}
    \stackMath
    \hrulefill

    \@addtoreset{equation}{section}

    \penalty1000
    \clubpenalty=0 
    \widowpenalty=0
    \interfootnotelinepenalty=1000
    \subjclass{Primary 01A80}
    \subjclass[xx]{Secondary 01A80}

    \typeout{** WARNING: IEEEtran.bst: No hyphenation pattern has been}
    \cmidrule(r{4pt}){2-6}
    \cmidrule(lr){3-11}

    \FloatBarrier
    \string
    \escapechar
    \paperwidth
    \paperwidth=8.5in
    \paperheight=11in
    \tableofcontents
    \counterwithin{table}{section}
    \counterwithout{table}{section}
    \linespread{1.5}
    \raise.17ex
    \setlist[enumerate]{itemsep=-0.5mm,partopsep=0pt}
    \pagecolor{lightgray}
    \pacs{98.70.Vc}
    \parindent = 0 pt
    \itemindent=14pt
    \parskip = 5 pt
    \kern.4ex
    \pdfinfo{/Author (OK-Robot)}
    \phantom{0}
    \Xhline{1.5pt}
    \midrule[\heavyrulewidth]

    \arrayrulewidth 1pt
    \overfullrule = 1pt

    \vspace{}
    \vspace{10pt}

    \refstepcounter{section}

    \pagenumbering{arabic}

    \hoffset=-1.1cm 
    \voffset=-0.5cm

    \Hy@MakeCurrentHref{\@currenvir.\the\Hy@linkcounter}
    \Hy@raisedlink{\hyper@anchorstart{\@currentHref}\hyper@anchorend}

    \AddEnumerateCounter{\fwbw}{\@fwbw}
    \AddEnumerateCounter{customenum}{\arabic}{enum}

    \geometry{a4paper}
    \unvbox0
    \unvbox\box
    \addcontentsline{toc}{chapter}{Bibliography}
    \mathtoolsset{mathic}


    \textfont\bboardfam=\tenbboard
    \scriptfont\bboardfam=\sevenbboard

    \setmathfont[range=\setminus, Scale=MatchUppercase]{Asana-Math.otf}
    \ExecuteBibliographyOptions{safeinputenc=true,backref=true,giveninits,useprefix=true,maxnames=5,doi=false,eprint=true,isbn=false,url=false}

    \setdefaultlanguage{english}
    \tracinglostchars=3

    \startcontents
    \printcontents{}{1}{\setcounter{tocdepth}{2}}

    \tcbset{colback=pink!50!20, colframe=white, boxrule=0mm, sharp corners}
    \tcbuselibrary{skins}

    \wd0
    \wd\mybox
    \the
    \showthe
    """
    content = [l.strip() for l in text.strip().split("\n") if l.strip()]
    for line in content:
        token, pos = handler.handle(line)
        assert pos == len(line), f"Failed on line: {line}"


def test_strip_trailing_number_from_token(handler):
    token = strip_trailing_number_from_token({"type": "text", "content": "1234567890"})
    assert token["content"] == ""

    token = strip_trailing_number_from_token(
        {"type": "text", "content": "1234567890abc"}
    )
    assert token["content"] == "1234567890abc"

    token = strip_trailing_number_from_token(
        {"type": "text", "content": "1234567890abc123"}
    )
    assert token["content"] == "1234567890abc"

    token = strip_trailing_number_from_token({"type": "text", "content": "FIRST 333"})
    assert token["content"] == "FIRST "

    token = strip_trailing_number_from_token({"type": "text", "content": "FIRST -0.5"})
    assert token["content"] == "FIRST "


def test_pzat_with_prevtoken(handler):
    for cmd in [r"\p@", r"\z@"]:
        prev_token = {"type": "text", "content": "FIRST -123.5"}

        token, pos = handler.handle(cmd, prev_token)
        assert token is None
        assert pos > 0
        assert prev_token["content"] == "FIRST "


def test_newmdenv(handler):
    text = r"""
\newmdenv[
  font=\ttfamily\small,
  linewidth=0.5pt,
  innerleftmargin=10pt,
  innerrightmargin=10pt,
  innertopmargin=10pt,
  innerbottommargin=10pt,
]{monobox}
POST
""".strip()
    token, pos = handler.handle(text)
    assert token is None
    assert text[pos:].strip() == "POST"


def test_titlecontents(handler):
    text = r"""
\titlecontents{section}
[0em]
{\vspace{0.4em}}
{\contentslabel{2em}}
{\bfseries}
{\bfseries\titlerule*[0.5pc]{$\cdot$}\contentspage}
[0.2em]
POST
    """.strip()
    token, pos = handler.handle(text)
    assert token is None
    assert text[pos:].strip() == "POST"

    text = r"""
\titlecontents{section}
[0em]
{\vspace{0.4em}}
{\contentslabel{2em}}
{\bfseries}
{\bfseries\titlerule*[0.5pc]{$\cdot$}\contentspage}
POST
    """.strip()
    token, pos = handler.handle(text)
    assert token is None
    assert text[pos:].strip() == "POST"


if __name__ == "__main__":
    pytest.main([__file__])
