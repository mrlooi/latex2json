import pytest
from latex2json.parser.handlers.new_definition import NewDefinitionHandler
import re


@pytest.fixture
def handler():
    return NewDefinitionHandler()


def test_can_handle_definitions(handler):
    assert handler.can_handle(r"\newcommand{\cmd}{definition}")
    assert handler.can_handle(r"\renewcommand\cmd{definition}")
    assert handler.can_handle(r"\newtheorem{thm}{Theorem}")
    assert not handler.can_handle("regular text")
    # assert handler.can_handle(r"\newenvironment{env}{begin}{end}")


def test_handle_newcommand(handler):
    # Test basic newcommand
    content = r"\newcommand{\cmd}{some definition}"
    token, pos = handler.handle(content)
    assert token["type"] == "newcommand"
    assert token["name"] == "cmd"
    assert token["content"] == "some definition"

    # Test with number of arguments
    content = r"\newcommand{\cmd}[2]{arg1=#1, arg2=#2}"
    token, pos = handler.handle(content)
    assert token["type"] == "newcommand"
    assert token["name"] == "cmd"
    assert token["num_args"] == 2
    assert token["content"] == "arg1=#1, arg2=#2"

    # Test with default values
    content = r"\newcommand{\cmd}[2][default]{arg1=#1, arg2=#2} POST"
    token, pos = handler.handle(content)
    assert token["defaults"] == ["default"]
    assert token["content"] == "arg1=#1, arg2=#2"
    assert content[pos:] == " POST"


def test_handle_newcommand_special_characters(handler):
    # special characters
    content = r"\newcommand{\<}{\langle} POST"
    token, pos = handler.handle(content)
    assert token["name"] == "<"
    assert token["content"] == r"\langle"
    assert content[pos:] == " POST"

    text = r"\<a"
    match = re.match(token["usage_pattern"], text)
    assert match and text[match.end() :] == "a"

    content = r"\newcommand{\(}{\left(} POST"
    token, pos = handler.handle(content)
    assert token["name"] == "("
    assert token["content"] == r"\left("
    assert content[pos:] == " POST"

    assert re.match(token["usage_pattern"], r"\(")
    text = r"\(a"
    match = re.match(token["usage_pattern"], text)
    assert match and text[match.end() :] == "a"

    # single digit
    content = r"\newcommand{\0}{\emptyset}"
    token, pos = handler.handle(content)
    assert token["name"] == "0"
    assert token["content"] == r"\emptyset"


def test_handle_renewcommand(handler):
    content = r"\renewcommand{\cmd}{new definition}"
    token, pos = handler.handle(content)

    assert token["type"] == "newcommand"
    assert token["name"] == "cmd"
    assert token["content"] == "new definition"


def test_handle_floatname(handler):
    content = r"\floatname{figure}{FigureX} after"
    token, pos = handler.handle(content)
    assert token == {"type": "floatname", "name": "figure", "title": "FigureX"}

    assert content[pos:] == " after"


def test_handle_newtheorem(handler):
    # Test basic newtheorem
    content = r"\newtheorem{theorem}{Theorem}"
    token, pos = handler.handle(content)
    assert token == {"type": "newtheorem", "name": "theorem", "title": "Theorem"}

    # Test with counter specification
    content = r"\newtheorem*{lemma}[theorem]{Lemma}"
    token, pos = handler.handle(content)
    assert token == {
        "type": "newtheorem",
        "name": "lemma",
        "counter": "theorem",
        "title": "Lemma",
    }

    # Test with numbering within
    content = r"\newtheorem{proposition}{Proposition}[section]"
    token, pos = handler.handle(content)
    assert token == {
        "type": "newtheorem",
        "name": "proposition",
        "title": "Proposition",
        "within": "section",
    }


def test_handle_newif(handler):
    content = r"\newif\ifvar\after"
    token, pos = handler.handle(content)
    assert token == {"type": "newif", "name": "var"}
    assert content[pos:] == r"\after"

    content = r"\renewif\ifxx@@x x"
    token, pos = handler.handle(content)
    assert token == {"type": "newif", "name": "xx@@x"}
    assert content[pos:] == " x"


def test_handle_newlength_setlength(handler):

    contents = [
        r"\newlength{\len} after",
        r"\newlength\len after",
        r"\renewlength{\len} after",
        r"\setlength{\len}{10pt} after",
        r"\setlength\len{1.5pt} after",
        r"\settoheight{\len}{text} after",
        r"\settoheight\len{\hbox{ssss}} after",
    ]
    for content in contents:
        token, pos = handler.handle(content)
        assert token == {"type": "newlength", "name": "len"}
        assert content[pos:] == " after"


def test_handle_newcounter(handler):
    content = r"\newcounter{counter} aaa"
    token, pos = handler.handle(content)
    assert token == {"type": "newcounter", "name": "counter"}
    assert content[pos:] == " aaa"


def test_handle_invalid_input(handler):
    # Test with non-command content
    token, pos = handler.handle("regular text")
    assert token is None
    assert pos == 0

    # Test with malformed commands
    assert not handler.can_handle(r"\newcommand{\cmd")

    # token, pos = handler.handle(r"\newenvironment{env}{begin")
    # assert token is None
    # assert pos > 0


def test_handle_complex_definitions(handler):
    # Test newcommand with nested braces
    content = r"\newcommand{\complex}[2]{outer{nested{#1}}{#2}}"
    token, pos = handler.handle(content)

    assert token["type"] == "newcommand"
    assert token["name"] == "complex"
    assert token["num_args"] == 2
    assert token["content"] == "outer{nested{#1}}{#2}"


def test_declare_operators(handler):
    content = r"\DeclareMathOperator\sin{cos}"
    token, pos = handler.handle(content)

    assert token is not None
    assert token["type"] == "newcommand"
    assert token["name"] == "sin"
    assert token["content"] == "cos"

    content = r"\DeclareRobustCommand\sin{cos}"
    token, pos = handler.handle(content)

    assert token is not None
    assert token["type"] == "newcommand"
    assert token["name"] == "sin"
    assert token["content"] == "cos"

    content = r"\DeclareRobustCommandxxx\sin{cos}"
    token, pos = handler.handle(content)
    assert token is None


def clean_groups(match):
    """Remove None values from regex match groups"""
    if match:
        return tuple(g for g in match.groups() if g is not None)
    return tuple()


def test_def_command_usage_patterns(handler):
    # Basic command without parameters
    content = r"\def\gaga{LADY GAGA}"
    token, _ = handler.handle(content)
    pattern = token["usage_pattern"]

    assert re.match(pattern, r"\gaga")
    assert re.match(pattern, r"\gaga ")
    assert not re.match(pattern, r"\gagaa")

    # Simple parameter pattern
    content = r"\def\fullname#1#2{#1 #2}"
    token, _ = handler.handle(content)
    pattern = token["usage_pattern"]

    assert re.match(pattern, r"\fullname{John}{Doe}")
    assert re.match(pattern, r"\fullname John Doe")
    assert re.match(pattern, r"\fullname{John} Doe")
    assert not re.match(pattern, r"\fullnameJohn Doe")
    assert not re.match(pattern, r"\fullname")

    # Delimiter pattern with colon
    content = r"\def\ratio#1:#2{#1 divided by #2}"
    token, _ = handler.handle(content)
    pattern = token["usage_pattern"]

    assert re.match(pattern, r"\ratio{4}:{42}")
    assert re.match(pattern, r"\ratio 55:42")
    assert re.match(pattern, r"\ratio{3.14}:{2.718}")
    assert not re.match(pattern, r"\ratio{4}")

    # Complex delimiters with parentheses and comma
    content = r"\def\pair(#1,#2){#1 and #2}"
    token, _ = handler.handle(content)
    pattern = token["usage_pattern"]

    assert re.match(pattern, r"\pair(asd sd ,b)")
    assert re.match(pattern, r"\pair({complex}, {args})")
    assert re.match(pattern, r"\pair(a,b)")
    assert not re.match(pattern, r"\pair(a)")

    # Exclamation marks as delimiters
    content = r"\def\foo!#1!{shout #1}"
    token, _ = handler.handle(content)
    pattern = token["usage_pattern"]

    assert re.match(pattern, r"\foo! hello!")
    assert re.match(pattern, r"\foo!{hell  o!}!")
    assert re.match(pattern, r"\foo!scream!")
    assert not re.match(pattern, r"\foo!")

    # Special case with \end as delimiter
    content = r"\def\until#1\end#2{This text until #1 #2}"
    token, _ = handler.handle(content)
    pattern = token["usage_pattern"]

    assert re.match(pattern, r"\until some \end3")
    assert re.match(pattern, r"\until{text}\end{section}")
    assert re.match(pattern, r"\until stuff \end more")
    assert not re.match(pattern, r"\until text")


def test_namedef(handler):
    # similar to def

    # Complex delimiters with parentheses and comma
    content = r"\@namedef{pair}(#1,#2){#1 and #2} POST"
    token, pos = handler.handle(content)
    assert token["type"] == "def"
    assert content[pos:] == " POST"

    pattern = token["usage_pattern"]

    assert re.match(pattern, r"\pair(asd sd ,b)")
    assert re.match(pattern, r"\pair({complex}, {args})")
    assert re.match(pattern, r"\pair(a,b)")
    assert not re.match(pattern, r"\pair(a)")

    # Special case with \end as delimiter
    content = r"\@namedef{until}#1\end#2{This text until #1 #2} POST"
    token, pos = handler.handle(content)
    assert token["type"] == "def"
    assert content[pos:] == " POST"

    pattern = token["usage_pattern"]

    assert re.match(pattern, r"\until some \end3")
    assert re.match(pattern, r"\until{text}\end{section}")
    assert re.match(pattern, r"\until stuff \end more")
    assert not re.match(pattern, r"\until text")

    # Special case for stuff with special chars e.g. @/. (usage via csname)
    content = r"\@namedef{ver@everyshi.sty}{}POST"
    token, pos = handler.handle(content)
    assert token["type"] == "def"
    assert content[pos:] == "POST"

    content = r"\@namedef{ver@everyshi.sty}{Hi there}POST"
    token, pos = handler.handle(content)
    assert token["type"] == "def"
    assert content[pos:] == "POST"

    pattern = token["usage_pattern"]

    assert re.match(pattern, r"\csname ver@everyshi.sty \endcsname")
    assert content[pos:] == "POST"


def test_let_command(handler):
    content = r"\let\foo=bar"
    token, _ = handler.handle(content)
    assert token["type"] == "let"
    assert token["name"] == "foo"
    assert token["content"] == "bar"

    content = r"\let\foo=\bar"
    token, _ = handler.handle(content)
    assert token["type"] == "let"
    assert token["name"] == "foo"
    assert token["content"] == r"\bar"

    # test without =
    content = r"\let\foo\bar"
    token, _ = handler.handle(content)
    assert token["type"] == "let"
    assert token["name"] == "foo"
    assert token["content"] == r"\bar"

    content = r"\let\foobar"
    token, _ = handler.handle(content)
    assert token is None

    content = r"""
    \let\arXiv\arxiv
    \def\doi
    """.strip()

    token, _ = handler.handle(content)
    assert token["name"] == "arXiv"
    assert token["content"] == r"\arxiv"

    # futurelet (treat as newcommand?)
    content = r"\futurelet\arXiv\arxiv"
    token, _ = handler.handle(content)
    # assert token["type"] == "let"
    assert token["name"] == "arXiv"
    assert token["content"] == r"\arxiv"


def test_crefname(handler):
    content = r"\crefname{equation}{333}{aaaa} hahaha"
    token, pos = handler.handle(content)
    assert token["type"] == "crefname"
    assert token["name"] == "equation"
    assert token["singular"] == "333"
    assert token["plural"] == "aaaa"

    assert content[pos:].strip() == "hahaha"

    content = r"\Crefname{theorem}{Theorem} POST"
    token, pos = handler.handle(content)
    assert token["type"] == "crefname"
    assert token["name"] == "theorem"
    assert token["singular"] == "Theorem"
    assert content[pos:] == " POST"


def test_def_usage_outputs(handler):
    def extract_def_args(text, search):
        token, end_pos = handler.handle(text)
        if token:
            if token["usage_pattern"]:
                regex = re.compile(token["usage_pattern"])
                match = regex.match(search)
                # print(token["usage_pattern"], token["content"])
                if match:
                    return clean_groups(match)
        return None

    assert extract_def_args(
        r"\def\ratio#1:#2{#1 divided by #2}", r"\ratio{4}:{42}"
    ) == ("4", "42")

    assert extract_def_args(
        r"\long\def\ratio#1:#2{#1 divided by #2}", r"\ratio{4}:{42}"
    ) == ("4", "42")

    # for 2nd arg, only 4 is captured (like in latex) since it is not in braces
    assert extract_def_args(r"\def\ratio#1:#2{#1 divided by #2}", r"\ratio55:42") == (
        "55",
        "4",
    )

    assert extract_def_args(r"\edef\foo!#1!{shout #1}", r"\foo! hello!") == ("hello",)
    assert extract_def_args(r"\edef\foo!#1!{shout #1}", r"\foo!{hell  o!}!") == (
        "hell  o!",
    )
    assert extract_def_args(r"\def\swap#1#2{#2#1}", r"\swap a b") == ("a", "b")
    assert extract_def_args(r"\def\fullname#1#2{#1 #2}", r"\fullname{John}{Doe}") == (
        "John",
        "Doe",
    )
    assert extract_def_args(r"\def\pair(#1,#2){#1 and #2}", r"\pair(asd sd ,b)") == (
        "asd sd ",
        "b",
    )
    assert extract_def_args(r"\edef\grab#1.#2]{#1 and #2}", r"\grab first.second]") == (
        "first",
        "second",
    )
    assert extract_def_args(
        r"\def\until#1\end#2{This text until #1 #2}", r"\until some \end3"
    ) == ("some ", "3")
    assert extract_def_args(
        r"\def\until#1\end#2{This text until #1 #2}", r"\until some \end {333}"
    ) == ("some ", "333")
    assert extract_def_args(r"\edef\gaga{LADY GAGA}", r"\gaga") is not None

    assert extract_def_args(r"\def\gaga{LADY GAGA}", r"\gagaa") is None
    assert extract_def_args(r"\def\fullname#1#2{#1 #2}", r"\fullname") is None
    assert extract_def_args(r"\def\fullname#1#2{#1 #2}", r"\fullname32") == ("3", "2")

    # Mathematical notation tests
    assert extract_def_args(r"\def\norm#1{\left\|#1\right\|}", r"\norm{x}") == ("x",)
    assert extract_def_args(r"\def\abs#1{\left|#1\right|}", r"\abs{x + y}") == (
        "x + y",
    )
    assert extract_def_args(r"\def\set#1{\{#1\}}", r"\set{x \in \mathbb{R}}") == (
        r"x \in \mathbb{R}",
    )

    # Multi-parameter math operators
    assert extract_def_args(
        r"\def\inner#1#2{\langle#1,#2\rangle}", r"\inner{u}{v}"
    ) == ("u", "v")
    assert extract_def_args(
        r"\def\pfrac#1#2{\frac{\partial #1}{\partial #2}}", r"\pfrac{f}{x}"
    ) == ("f", "x")

    # Subscript/superscript patterns
    assert extract_def_args(
        r"\def\tensor#1_#2^#3{#1_{#2}^{#3}}", r"\tensor{T}_i^j"
    ) == ("T", "i", "j")
    assert extract_def_args(
        r"\def\tensor#1_#2^#3{#1_{#2}^{#3}}", r"\tensor{\{T\}}_i^j"
    ) == (r"\{T\}", "i", "j")
    assert extract_def_args(
        r"\def\evalat#1|#2{\left.#1\right|_{#2}}", r"\evalat{f(x)}|{x=0}"
    ) == ("f(x)", "x=0")

    # Common text formatting
    assert extract_def_args(
        r"\def\emphtext#1{\textit{\textbf{#1}}}", r"\emphtext{important}"
    ) == ("important",)

    # Multiple optional parts
    assert extract_def_args(
        r"\def\theorem#1[#2]#3{Theorem #1 (#2): #3}", r"\theorem{1}[Name]{Statement}"
    ) == ("1", "Name", "Statement")


def test_with_csname_and_expandafter(handler):
    content = r"\def \csname \expandafter test\endcsname#1{VALID COMMAND #1} POST"
    token, pos = handler.handle(content)
    assert token["type"] == "def"
    assert token["name"] == "test"
    assert token["num_args"] == 1
    assert token["content"] == "VALID COMMAND #1"
    assert content[pos:] == " POST"

    pattern = re.compile(token["usage_pattern"])
    match = pattern.match(r"\test{1}")
    assert match is not None
    match = pattern.match(r"\csname  test\endcsname{1}")  # valid (check spacing)
    assert match is not None

    match = pattern.match(r"\csname test \endcsname{1}")  # invalid, watch for spacing
    assert match is None

    # with let (double csname blocks)
    content = r"\let\noexpand\csname oldschool\expandafter\noexpand\endcsname\csname school\endcsname POST"
    token, pos = handler.handle(content)
    assert token["type"] == "let"
    assert token["name"] == "oldschool"
    assert token["content"] == r"\school"
    pattern = re.compile(token["usage_pattern"])
    assert pattern.match(r"\csname oldschool\endcsname")
    assert not pattern.match(r"\csname oldschool   \endcsname")
    assert content[pos:] == " POST"


def test_other_newX_commands(handler):
    content = r"\newcount\cvpr@rulercount aaa"
    token, pos = handler.handle(content)
    assert token["name"] == "cvpr@rulercount"
    assert content[pos:] == " aaa"

    content = r"\newdimen\cvpr@ruleroffset"
    token, pos = handler.handle(content)
    assert token["name"] == "cvpr@ruleroffset"

    content = r"\newbox\cvpr@rulerbox"
    token, pos = handler.handle(content)
    assert token["name"] == "cvpr@rulerbox"


def test_paired_delimiter(handler):
    content = r"\DeclarePairedDelimiter\br{(}{)} POST"
    token, pos = handler.handle(content)
    assert token["type"] == "paired_delimiter"
    assert token["name"] == "br"
    assert token["left_delim"] == "("
    assert token["right_delim"] == ")"

    assert content[pos:] == " POST"

    content = r"\DeclarePairedDelimiter\abs{\lvert}{\rvert} POST"
    token, pos = handler.handle(content)
    assert token["type"] == "paired_delimiter"
    assert token["name"] == "abs"
    assert token["left_delim"] == r"\lvert"
    assert token["right_delim"] == r"\rvert"
    assert content[pos:] == " POST"


def test_definecolor(handler):
    content = r"\definecolor{linkcolor}{HTML}{ED1C24} POST"
    token, pos = handler.handle(content)
    assert token["type"] == "definecolor"
    assert token["name"] == "linkcolor"
    assert token["format"] == "HTML"
    assert token["value"] == "ED1C24"
    assert content[pos:] == " POST"


def test_newtoks(handler):
    content = r"\newtoks\foo"
    token, pos = handler.handle(content)
    assert token["type"] == "newtoks"
    assert token["name"] == "foo"

    content = r"\newtoks{\bar}"
    token, pos = handler.handle(content)
    assert token["type"] == "newtoks"
    assert token["name"] == "bar"


def test_newfam(handler):
    content = r"\newfam\bboardfam"
    token, pos = handler.handle(content)
    assert token["type"] == "newfam"
    assert token["name"] == "bboardfam"


def test_new_columntype(handler):
    content = r"\newcolumntype{L}[1]{>{\raggedright\let\newline\\\arraybackslash\hspace{0pt}}m{#1}} POST"
    token, pos = handler.handle(content)
    assert content[pos:] == " POST"

    content = r"\newcolumntype{S}{>{\hsize=.3\hsize}X} POST"
    token, pos = handler.handle(content)
    assert content[pos:] == " POST"


def test_font(handler):
    content = r"\font\myfont=cmr12 at 20pt POST"
    token, pos = handler.handle(content)
    assert token["type"] == "font"
    assert token["name"] == "myfont"
    assert content[pos:] == " POST"

    content = r"\font\myfont=mbbb POST"
    token, pos = handler.handle(content)
    assert token["type"] == "font"
    assert token["name"] == "myfont"
    assert token["source"] == "mbbb"
    assert content[pos:] == " POST"
    # assert token["unit"] == "pt"


def test_declare_alphabets(handler):
    content = r"\DeclareMathAlphabet{\mathbf}{OT1}{cmr}{b}{n} POST"
    token, pos = handler.handle(content)
    assert token["type"] == "newcommand"
    assert token["name"] == "mathbf"
    assert token["math_mode_only"]
    assert content[pos:] == " POST"

    content = r"\DeclareSymbolFontAlphabet{\mathbf}{OT1} POST"
    token, pos = handler.handle(content)
    assert token["type"] == "newcommand"
    assert token["name"] == "mathbf"
    assert token["math_mode_only"]


if __name__ == "__main__":
    pytest.main([__file__])
