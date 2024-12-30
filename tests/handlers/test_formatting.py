import datetime
import pytest
from src.handlers.formatting import FormattingHandler, strip_trailing_number_from_token


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
% 1. Basic color commands
\color{red}                    % Change text color
% \textcolor{blue}{text}        % Color specific text

% 2. Color definitions
\definecolor{customred}{RGB}{255,0,0}
\definecolor{customblue}{rgb}{0,0,1}        % rgb format
\definecolor{custompink}{HTML}{FF00FF}      % hex format
\definecolor{customgray}{gray}{0.5}         % grayscale
\definecolor{customcolor}{cmyk}{0,1,0,0}    % cmyk format

% 3. Color packages and their commands
% xcolor package adds these:
\rowcolor{gray}               % Table row color
\columncolor{blue}            % Table column color
\cellcolor{red}               % Single cell color

% 4. Background color commands
\pagecolor{lightgray}         % Page background
\normalcolor                  % Reset to default color

% 5. Color mixing commands (from xcolor)
\color{red!50!blue}          % Mix red and blue 50-50
\color{blue!20}              % 20% blue, 80% white
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
    assert token == {"type": "date", "content": "2024-11-29"}
    assert text[end_pos:] == " sss"

    text = r"\date{} sss"
    token, end_pos = handler.handle(text)
    assert token == {"type": "date", "content": ""}
    assert text[end_pos:] == " sss"

    text = r"\today sss"
    token, end_pos = handler.handle(text)
    assert token == {
        "type": "date",
        "content": datetime.datetime.now().strftime("%Y-%m-%d"),
    }
    assert text[end_pos:] == " sss"


def test_misc_formatting_commands(handler):
    text = r"""
    \documentclass[12pt,a4paper,reqno]{amsart}
    \documentclass{XXX}
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

    \topmargin 0.0cm
    \oddsidemargin 0.2cm
    \textwidth 16cm 
    \textheight 21cm
    \footskip 1.0cm
    \newcolumntype{S}{>{\hsize=.3\hsize}X}
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

    \ProcessOptions
    \PassOptionsToPackage{fleqn}{amsmath}
    \PassOptionsToClass{fleqn}{amsmath}

    \NeedsTeXFormat{LaTeX2e}
    \ProvidesClass{sigma}[2012/01/18]
    \LoadClass[fleqn,11pt,twoside]{article}
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
    \p@
    \z@
    5\p@
    10\z@
    \enlargethispage{2\baselineskip}
    \baselineskip
    2\baselineskip
    \advance\@tempskipa-\@tempdimb
    \advance\section@level-\subsection@level
    \advance\leftmargin by -\rightmargin

    \newcolumntype{x}[1]{>{\centering}p{#1pt}}
    \newcolumntype{y}{>{\centering}p{16pt}}
    \hyphenation{identity notorious underlying surpasses desired residual doubled}

    \DeclareFontFamily{OT1}{rsfs}{}
    \DeclareFontShape{OT1}{rsfs}{n}{it}{<-> rsfs10}{}
    \DeclareMathAlphabet{\mathscr}{OT1}{rsfs}{n}{it}
    \SetMathAlphabet{\mathscr}{OT1}{rsfs}{n}{it}{xxx}

    \penalty1000
    \subjclass{Primary 01A80}
    \subjclass[xx]{Secondary 01A80}

    \typeout{** WARNING: IEEEtran.bst: No hyphenation pattern has been}
    \cmidrule(r{4pt}){2-6}

    \FloatBarrier

    \paperwidth=8.5in
    \paperheight=11in
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


if __name__ == "__main__":
    pytest.main([__file__])
