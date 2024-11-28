import pytest
from src.handlers.formatting import FormattingHandler


@pytest.fixture
def handler():
    return FormattingHandler()


def test_can_handle_formatting(handler):
    # Test formatting commands
    assert handler.can_handle(r"\usepackage{amsmath}")
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
\colorbox{yellow}{text}       % Colored background box
\fcolorbox{red}{white}{text}  % Framed color box

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
    def check_token(token, pos):
        assert token["type"] == "text"
        assert token["content"] == " "
        assert pos > 0

    token, pos = handler.handle(r"\hspace{10pt}")
    check_token(token, pos)

    token, pos = handler.handle(r"\quad")
    check_token(token, pos)

    token, pos = handler.handle(r"\,")
    check_token(token, pos)


def test_header_stuff(handler):
    text = r"""
    \documentclass[12pt,a4paper,reqno]{amsart}
    \hypersetup{colorlinks,linkcolor={blue},citecolor={blue},urlcolor={red}}  
    \usepackage[noabbrev,capitalize,nameinlink]{cleveref}
    \usepackage{graphicx}
    \pagestyle{empty}
    \setlength{\marginparwidth}{1in}
    \numberwithin{equation}{section}
    \theoremstyle{conjecture}
    \setcounter{theorem}{0}
    \vspace{.5em}
    \noindent
    \bibliographystyle{plain}
    \abovedisplayskip
    \belowdisplayshortskip
    \urlstyle{same}
    \pdfoutput=1
    \pdfsuppresswarningpagegroup=1
    \lstset{breaklines=true, style=\color{blue}}
    """
    content = [l.strip() for l in text.strip().split("\n") if l.strip()]
    for line in content:
        token, pos = handler.handle(line)
        assert pos > 0, f"Failed on line: {line}"


if __name__ == "__main__":
    pytest.main([__file__])
