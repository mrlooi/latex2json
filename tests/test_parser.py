import pytest
from src.patterns import SECTION_LEVELS
from src.tex_parser import LatexParser
from tests.latex_samples_data import TRAINING_SECTION_TEXT


# Replace setUp with fixtures
@pytest.fixture
def parser():
    return LatexParser()


@pytest.fixture
def parsed_training_tokens(parser):
    return parser.parse(TRAINING_SECTION_TEXT)


# Convert test classes to groups of functions
# TestParserText1 class becomes:


def test_parse_sections(parsed_training_tokens):
    sections = [token for token in parsed_training_tokens if token["type"] == "section"]
    assert len(sections) == 7

    start_level = SECTION_LEVELS["section"]
    assert sections[0]["title"] == "Training"
    assert sections[0]["level"] == start_level
    assert sections[1]["title"] == "Training Data and Batching"
    assert sections[1]["level"] == start_level + 1
    assert sections[2]["title"] == "Hardware and Schedule"
    assert sections[2]["level"] == start_level + 1

    regularization_section = None
    for section in sections:
        if section["title"] == "Regularization":
            regularization_section = section
            break
    assert regularization_section is not None

    # check its label is there
    assert regularization_section["labels"] == ["sec:reg"]


def test_parse_subsections(parser):
    text = r"""
    \subsection{Training Data and Batching}
    \subsubsection{Hardware and Schedule}

    \paragraph{Regularization}
    \subparagraph{Sub Regularization}
    """
    parsed_tokens = parser.parse(text)
    sections = [token for token in parsed_tokens if token["type"] == "section"]

    assert sections[0]["title"] == "Training Data and Batching"
    assert sections[0]["level"] == SECTION_LEVELS["section"] + 1
    assert sections[1]["title"] == "Hardware and Schedule"
    assert sections[1]["level"] == SECTION_LEVELS["section"] + 2

    assert sections[2]["title"] == "Regularization"
    assert sections[2]["level"] == SECTION_LEVELS["paragraph"]
    assert sections[3]["title"] == "Sub Regularization"
    assert sections[3]["level"] == SECTION_LEVELS["paragraph"] + 1


def test_parse_equations(parsed_training_tokens):
    equations = [
        token for token in parsed_training_tokens if token["type"] == "equation"
    ]
    # inline equations = 7
    inline_equations = [token for token in equations if token["display"] == "inline"]
    assert len(inline_equations) == 7
    assert len(equations) == 8


def test_parse_citations(parsed_training_tokens):
    # number of citations=5
    citations = [
        token for token in parsed_training_tokens if token["type"] == "citation"
    ]
    assert len(citations) == 5
    assert citations[0]["content"] == "DBLP:journals/corr/BritzGLL17"


def test_parse_refs(parser, parsed_training_tokens):
    refs = [token for token in parsed_training_tokens if token["type"] == "ref"]
    assert len(refs) == 1
    assert refs[0]["content"] == "tab:variations"

    labels = parser.labels
    assert len(labels) == 1
    assert "sec:reg" in labels


# TestParserEquations class becomes:


def test_math_mode_edge_cases(parser):
    text = r"""
    $a_1^2$ and $x_{i,j}^{2n}$ and $\frac{1}{2}$
    $\left(\frac{1}{2}\right)$ and $\left[\frac{1}{2}\right]$
    $\{x : x > 0\}$ and $|x|$ and $\|x\|$
    $\sum_{i=1}^n$ and $\int_0^\infty$ and $\prod_{i=1}^n$
    $\lim_{x \to \infty}$ and $\sup_{x \in X}$
    """
    parsed_tokens = parser.parse(text)
    equations = [t for t in parsed_tokens if t["type"] == "equation"]
    assert len(equations) == 13


# TestParserNewCommands tests:


def test_command_definitions(parser):
    text = r"""
    \newcommand{\HH}{\mathbb{H}} 
    \newcommand{\I}{\mathbb{I}} 
    \newcommand{\E}{\mathbb{E}} 
    \renewcommand{\P}{\mathbb{P}} 
    \newcommand{\pow}[2][2]{#2^{#1}}
    \newcommand{\dmodel}{d_{\text{model}}}

    $\pow[5]{3}$ and $\HH$ and $\I$ and $\dmodel$

    \newcommand*{\goodexample}[1]{#1}
    \goodexample{Single line of text}

    \newcommand{\myedit}[1]{#1 \newline(Edited by me)}
    \myedit{First paragraph

    Second paragraph}
    """
    parsed_tokens = parser.parse(text)
    equations = [token for token in parsed_tokens if token["type"] == "equation"]

    commands = parser.command_processor.commands
    # Check if commands were stored correctly
    assert "HH" in commands
    assert "I" in commands
    assert "E" in commands
    assert "P" in commands
    assert "pow" in commands

    # Check command expansion in equations
    assert equations[0]["content"] == "3^{5}"
    assert equations[1]["content"] == r"\mathbb{H}"
    assert equations[2]["content"] == r"\mathbb{I}"
    assert equations[3]["content"] == r"d_{\text{model}}"

    last_token = parsed_tokens[-1]["content"]
    split_content = [line.strip() for line in last_token.split("\n") if line.strip()]
    assert len(split_content) == 4
    assert split_content[0] == "Single line of text"
    assert split_content[1] == "First paragraph"
    assert split_content[2] == "Second paragraph"
    assert split_content[3] == "(Edited by me)"


def test_recommand_definitions(parser):
    text = r"""
    \renewcommand{\outer}[2]{\inner{#1}{#2}}
    \newcommand{\inner}[2]{(#1,#2)}
    
    \outer{a}{b}
    
    \renewcommand{\inner}[2]{[#1,#2]}
    \outer{x}{y}
    """
    parsed_tokens = parser.parse(text)
    # Verify nested command expansion works correctly
    text_content = []
    for token in parsed_tokens:
        ss = token["content"].split("\n")
        for s in ss:
            if s.strip():
                text_content.append(s.strip())
    assert text_content[0] == "(a,b)"
    assert text_content[1] == "[x,y]"


def test_complex_command_definitions(parser):
    text = r"""
    % Command with 3 required arguments
    \newcommand{\tensor}[3]{\mathbf{#1}_{#2}^{#3}}
    
    % Command with 1 optional and 2 required arguments
    \newcommand{\norm}[3][2]{\|#2\|_{#3}^{#1}}
    
    \newcommand{\integral}[4][0]{\int_{#1}^{#2} #3 \, d#4}
    
    % Command using other defined commands
    \newcommand{\tensorNorm}[4]{\norm{\tensor{#1}{#2}{#3}}{#4}}

    $\tensor{T}{i}{j}$ and $\norm[p]{x}{2}$ and $\norm{y}{1}$
    $\integral{b}{f(x)}{x}$ and $\integral[a]{b}{g(x)}{x}$
    $\tensorNorm{T}{i}{j}{\infty}$
    """
    parsed_tokens = parser.parse(text)
    equations = [token for token in parsed_tokens if token["type"] == "equation"]

    # Check command storage
    commands = parser.command_processor.commands
    assert "tensor" in commands
    assert "norm" in commands
    assert "integral" in commands
    assert "tensorNorm" in commands

    # Check expansions
    expected_results = [
        "\\mathbf{T}_{i}^{j}",  # tensor expansion
        "\\|x\\|_{2}^{p}",  # norm with optional arg
        "\\|y\\|_{1}^{2}",  # norm with default optional arg
        "\\int_{0}^{b} f(x) \\, dx",  # integral with defaults
        "\\int_{a}^{b} g(x) \\, dx",  # integral with one optional
        "\\|\\mathbf{T}_{i}^{j}\\|_{\\infty}^{2}",  # nested command
    ]

    for eq, expected in zip(equations, expected_results):
        assert eq["content"] == expected


def test_command_with_environments(parser):
    text = r"""
        \newcommand{\Fma}{$F=ma$}

        \newcommand{\myenv}[2]{
            \begin{equation*}
                #1 = #2 
                \Fma
            \end{equation*}
        }
        \myenv{E}{mc^2}
    """
    parsed_tokens = parser.parse(text)
    # Check that we got one equation token
    assert len(parsed_tokens) == 1
    equation = parsed_tokens[0]

    # Verify equation properties
    assert equation["type"] == "equation"
    assert equation["display"] == "block"

    # Verify equation content includes both the substituted parameters
    # and the expanded \Fma command
    assert "E = mc^2" in equation["content"]
    assert "F=ma" in equation["content"]


def test_alt_command_definitions(parser):
    """Test command definitions without braces"""
    text = r"""
    \newcommand\eps{\varepsilon}

    $\eps$
    """
    parsed_tokens = parser.parse(text)
    equations = [token for token in parsed_tokens if token["type"] == "equation"]

    # Check command storage
    commands = parser.command_processor.commands
    assert "eps" in commands

    # Check expansion
    assert equations[0]["content"] == r"\varepsilon"
    assert equations[0]["display"] == "inline"


def test_newdef_definitions(parser):
    text = r"""
    \def\foo#1{bar #1}
    \foo{hello}
    """
    parsed_tokens = parser.parse(text)
    assert parsed_tokens[0]["content"].strip() == "bar hello"

    # test that \newcommand overrides \def
    text = r"""
    \def\foo#1{bar #1}
    \newcommand\foo[1]{NOBAR #1}
    \foo{hello}
    """
    parsed_tokens = parser.parse(text)
    assert parsed_tokens[0]["content"].strip() == "NOBAR hello"

    text = r"""
    \newcommand\addme[2]{#1+NONONO+#2}
    \def\addme#1#2{
        #1+#2
    }
    \begin{equation}
        \addme{x}{y}
    \end{equation}
    """
    parsed_tokens = parser.parse(text)
    assert parsed_tokens[0]["content"].strip() == "x+y"


# TestParserEnvironments tests:


def test_nested_environments(parser):
    text = r"""
    \begin{lemma}\label{tb} With probability $1-O(\eps)$, one has 
    \begin{equation}\label{t-bound}
    \t = O_{\eps}(X^\delta).
    \end{equation}
    \end{lemma}
    """
    parsed_tokens = parser.parse(text)

    # Check environments
    environments = [token for token in parsed_tokens if token["type"] == "environment"]
    assert len(environments) == 1

    # Check lemma environment
    lemma = environments[0]
    assert lemma["name"] == "lemma"
    assert lemma["labels"] == ["tb"]

    # Check equation environment
    equation = lemma["content"][0]
    for token in lemma["content"]:
        if token["type"] == "equation" and "labels" in token:
            equation = token
            break
    assert equation["labels"] == ["t-bound"]


def test_multiple_environments(parser):
    text = r"""
    \begin{theorem}
        Statement
        \begin{proof}
            Proof details
            \begin{subproof}
                \item First point
                \item Second point
            \end{subproof}
        \end{proof}
    \end{theorem}

    \begin{corollary}
        \begin{equation}\label{nax}
        \E \left|\sum_{j=1}^n \g(j)\right|^2 \leq C^2
        \end{equation}
        \label{COL}
    \end{corollary}
    """
    parsed_tokens = parser.parse(text)
    theorem = parsed_tokens[0]

    assert theorem["name"] == "theorem"

    # check proof is nested inside theorem
    proof = theorem["content"][1]
    assert proof["name"] == "proof"

    # check subproof is nested inside proof
    assert proof["content"][0]["content"].strip() == "Proof details"
    subproof = proof["content"][1]
    assert subproof["name"] == "subproof"

    corollary = parsed_tokens[1]
    assert corollary["name"] == "corollary"
    assert corollary["labels"] == ["COL"]

    # check equation is nested inside corollary
    equation = corollary["content"][0]
    assert equation["content"] == r"\E \left|\sum_{j=1}^n \g(j)\right|^2 \leq C^2"
    assert equation["labels"] == ["nax"]


def test_split_equation(parser):
    text = r"""
    \begin{equation}\label{jock}
    \begin{split}
    &\frac{1}{H} \sum_{H < H' \leq 2H} \sum_{a \in [1,\q^k], \hbox{ good}} \left|\sum_{m=1}^{H'} \tilde{\boldsymbol{\chi}}(a+m) \sum_{n = a+m \ (\q^k)} \frac{\h(n)}{n^{1+1/\log X}}\right|^2 \\
    &\quad \ll_\eps \frac{\log^2 X}{\q^k} .
    \end{split}
    \end{equation}
    """
    parsed_tokens = parser.parse(text)
    equation = parsed_tokens[0]
    assert equation["type"] == "equation"
    assert equation["labels"] == ["jock"]

    # check begin{split} is nested inside equation
    split = equation["content"]
    assert split.startswith(r"\begin{split}")
    assert split.endswith(r"\end{split}")


def test_parse_equations_with_commands(parser):
    text = r"""
    \newcommand{\pow}[2][2]{#2^{#1}}

    $$F=ma
    E=mc^2
    \pow{ELON}
    $$
    $\pow{x}$

    \[
    BLOCK ME 
    BRO
    \pow[5]{A}
    \]
    \(INLINE, \pow[3]{B}\)
    """
    parsed_tokens = parser.parse(text)
    equations = [token for token in parsed_tokens if token["type"] == "equation"]
    assert len(equations) == 4

    block1 = equations[0]["content"]
    # block1 contains F=ma, E=mc^2 and ELON^{2}
    assert "F=ma" in block1
    assert "E=mc^2" in block1
    assert "ELON^{2}" in block1
    assert equations[0]["display"] == "block"

    assert equations[1]["display"] == "inline"
    assert equations[1]["content"] == "x^{2}"

    block2 = equations[2]["content"]
    assert "BLOCK ME" in block2
    assert "BRO" in block2
    assert "A^{5}" in block2
    assert equations[2]["display"] == "block"

    inline2 = equations[3]["content"]
    assert inline2 == "INLINE, B^{3}"
    assert equations[3]["display"] == "inline"


def test_align_block(parser):
    text = r"""
    \begin{align*}
    \left(\E \left|\sum_{j=1}^n \g(jd)\right|^2\right)^{1/2} &= \left(\E \left| \sum_{i \geq 0: 3^i \leq n} \boldsymbol{\eps}_{i+l} \sum_{m \leq n/3^i} \chi_3(md') \right|^2\right)^{1/2} \\
    &\leq \left(\sum_{i \geq 0: 3^i \leq n} 1\right)^{1/2}\\
    &\ll \sqrt{\log n},
    \end{align*}
    """
    parsed_tokens = parser.parse(text)
    align = parsed_tokens[0]
    assert align["type"] == "equation"
    assert align["display"] == "block"
    content = align["content"]
    assert content.startswith(r"\left(")
    assert content.endswith(r"\sqrt{\log n},")


def test_parse_citations_with_titles(parser):
    text = r"""
    Regular citation \cite{DBLP:journals/corr/BritzGLL17}
    Citation with title \cite[Theorem 2.1]{smith2023}
    Multiple citations \cite{paper1,paper2}
    """
    parsed_tokens = parser.parse(text)
    citations = [token for token in parsed_tokens if token["type"] == "citation"]

    # Test regular citation
    assert citations[0]["content"] == "DBLP:journals/corr/BritzGLL17"
    assert "title" not in citations[0]

    # Test citation with title
    assert citations[1]["content"] == "smith2023"
    assert citations[1]["title"] == "Theorem 2.1"

    # Test multiple citations
    assert citations[2]["content"] == "paper1,paper2"
    assert "title" not in citations[2]


def test_parse_refs_and_urls(parser):
    text = r"""
    \url{https://www.tesla.com}
    \href{https://www.google.com}{Google}

    \hyperref[fig:modalnet]{ModalNet}
    \ref{fig:modalnet}
    """
    parsed_tokens = parser.parse(text)
    refs = [token for token in parsed_tokens]
    assert len(refs) == 4

    assert refs[0]["type"] == "url"
    assert refs[1]["type"] == "url"
    assert refs[2]["type"] == "ref"
    assert refs[3]["type"] == "ref"

    assert refs[0]["content"] == "https://www.tesla.com"
    assert refs[1]["content"] == "https://www.google.com"
    assert refs[2]["title"] == "fig:modalnet"
    assert "title" not in refs[0]
    assert refs[1]["title"] == "Google"
    assert refs[2]["content"] == "ModalNet"
    assert "title" not in refs[3]
    assert refs[3]["content"] == "fig:modalnet"


def test_nested_items(parser):
    text = r"""
    \begin{enumerate}
    \item Here is an item with a nested equation and a graphic:
    \begin{minipage}{0.45\textwidth}
        \begin{equation}
            E = mc^2
        \end{equation}
        \begin{equation}
            F = ma
        \end{equation}
    \end{minipage}%
    \\
    \begin{minipage}{0.45\textwidth}
        \centering
        \includegraphics[width=0.5\textwidth]{example-image}
        \captionof{figure}{Example Image}
    \end{minipage}

    \item $asdasdsads$
    \end{enumerate}
    """
    parsed_tokens = parser.parse(text)

    # Check the enumerate environment
    assert len(parsed_tokens) == 1
    enum_env = parsed_tokens[0]
    assert enum_env["type"] == "list"

    # Check items within enumerate
    items = [token for token in enum_env["content"] if token["type"] == "item"]
    assert len(items) == 2

    # Check first item's nested content
    first_item = items[0]
    minipages = [
        token
        for token in first_item["content"]
        if "name" in token and token["name"] == "minipage"
    ]
    assert len(minipages) == 2

    # Check equations in first minipage
    first_minipage = minipages[0]
    equations = [
        token for token in first_minipage["content"] if token["type"] == "equation"
    ]
    assert len(equations) == 2
    assert equations[0]["content"] == "E = mc^2"
    assert equations[1]["content"] == "F = ma"

    # Check second minipage content
    second_minipage = minipages[1]
    graphics = [
        token
        for token in second_minipage["content"]
        if token["type"] == "includegraphics"
    ]
    assert len(graphics) == 1
    assert graphics[0]["content"] == "example-image"

    # Check second item's equation
    second_item = items[1]
    equations = [
        token for token in second_item["content"] if token["type"] == "equation"
    ]
    assert len(equations) == 1
    assert equations[0]["content"] == "asdasdsads"
    assert equations[0]["display"] == "inline"


def test_item_with_label(parser):
    text = r"""
    \begin{itemize}
    \label{label-top}
    \item[*] First item with custom label
    \item Second item
    \item[+] \label{special-item} Third item with label
    \end{itemize}
    """
    parsed_tokens = parser.parse(text)

    itemize = parsed_tokens[0]
    assert itemize["type"] == "list"
    assert itemize["labels"] == ["label-top"]

    items = [token for token in itemize["content"] if token["type"] == "item"]
    assert len(items) == 3

    # Check custom labels
    assert items[0]["content"][0]["content"] == "First item with custom label"
    assert items[1]["content"][0]["content"] == "Second item"
    assert items[2]["content"][0]["content"] == "Third item with label"

    # Check item with label
    assert items[2]["labels"] == ["special-item"]


def test_figure(parser):
    content = r"""
    \begin{figure*}[h]
    {\includegraphics[width=\textwidth, trim=0 0 0 36, clip]{./vis/making_more_difficult5_new.pdf}}
    \caption{An example of the attention mechanism following long-distance dependencies in the encoder self-attention in layer 5 of 6. Many of the attention heads attend to a distant dependency of the verb `making', completing the phrase `making...more difficult'.  Attentions here shown only for the word `making'. Different colors represent different heads. Best viewed in color.}
    \end{figure*}

    finish
    """.strip()
    tokens = parser.parse(content)
    token = tokens[0]

    assert token["type"] == "figure"
    assert token["name"] == "figure*"
    assert len(token["content"]) == 2

    assert token["content"][0]["type"] == "includegraphics"
    assert token["content"][1]["type"] == "caption"


def test_nested_figures(parser):
    text = r"""
    \begin{figure}[htbp]
        \centering
        \begin{subfigure}[b]{0.45\textwidth}
            \centering
            \includegraphics[width=\textwidth]{image.png}
            \caption{First pendulum design}
            \label{fig:pendulum-a}
        \end{subfigure}
        \hfill
        \begin{subfigure}[b]{0.45\textwidth}
            \centering
            \includegraphics[width=\textwidth]{example-image-b}
            \caption{Second pendulum design}
            \label{fig:pendulum-b}
        \end{subfigure}
        \captionof{figure}{Different pendulum clock designs}
        \label{fig:pendulum-designs}
    \end{figure}
    """
    parsed_tokens = parser.parse(text)

    # Check main figure
    assert len(parsed_tokens) == 1
    figure = parsed_tokens[0]
    assert figure["type"] == "figure"
    assert figure["labels"] == ["fig:pendulum-designs"]

    # Check subfigures
    subfigures = [token for token in figure["content"] if token["type"] == "figure"]
    assert len(subfigures) == 2

    # Check first subfigure
    first_subfig = subfigures[0]
    assert first_subfig["labels"] == ["fig:pendulum-a"]

    # Check first subfigure content
    first_graphics = [
        t for t in first_subfig["content"] if t["type"] == "includegraphics"
    ][0]
    first_caption = [t for t in first_subfig["content"] if t["type"] == "caption"][0]
    assert first_graphics["content"] == "image.png"
    assert first_caption["content"] == "First pendulum design"

    # Check second subfigure
    second_subfig = subfigures[1]
    assert second_subfig["labels"] == ["fig:pendulum-b"]

    # Check second subfigure content
    second_graphics = [
        t for t in second_subfig["content"] if t["type"] == "includegraphics"
    ][0]
    second_caption = [t for t in second_subfig["content"] if t["type"] == "caption"][0]
    assert second_graphics["content"] == "example-image-b"
    assert second_caption["content"] == "Second pendulum design"

    # Check main caption
    main_caption = [t for t in figure["content"] if t["type"] == "caption"][0]
    assert main_caption["content"] == "Different pendulum clock designs"


def test_complex_table(parser):
    text = r"""
    \begin{table}[htbp]
    \centering
    \begin{tabular}{|c|c|c|c|}
        \hline
        \multicolumn{2}{|c|}{\multirow{2}{*}{Region}} & \multicolumn{2}{c|}{Sales} \\
        \cline{3-4}
        \multicolumn{2}{|c|}{} & 2022 & 2023 \\
        \hline
        \multirow{2}{*}{North} & Urban & $x^2 + y^2 = z^2$ & 180 \\
        & Rural & 100 & 120 \\
        \hline
        \multirow{2}{*}{South} & Urban & 200 & \begin{align} \label{eq:1} E = mc^2 \\ $F = ma$ \end{align} \\
        & & 130 & 160 \\
        Thing with \cite{elon_musk} & SpaceX & Tesla & Neuralink \\
        \hline
    \end{tabular}
    \caption{Regional Sales Distribution}
    \label{tab:sales}
    \end{table}
    """
    parsed_tokens = parser.parse(text)
    table = parsed_tokens[0]

    # Check table properties
    assert table["type"] == "table"
    assert table["title"] == "htbp"
    assert table["labels"] == ["tab:sales"]

    # Check tabular content
    tabular = table["content"][0]
    assert tabular["type"] == "tabular"
    assert tabular["column_spec"] == "|c|c|c|c|"

    # Check specific cells
    cells = tabular["content"]

    # Check header cell with multicolumn and multirow
    assert cells[0][0]["content"] == "Region"
    assert cells[0][0]["rowspan"] == 2
    assert cells[0][0]["colspan"] == 2

    assert cells[1][0]["content"] == None
    assert cells[1][0]["colspan"] == 2
    assert cells[1][0]["rowspan"] == 1
    assert cells[1][1:] == ["2022", "2023"]

    assert cells[2][0]["content"] == "North"
    assert cells[2][0]["rowspan"] == 2
    assert cells[2][0]["colspan"] == 1

    # Check inline equation cell
    equation_cell = cells[2][2]
    assert equation_cell["type"] == "equation"
    assert equation_cell["content"] == "x^2 + y^2 = z^2"
    assert equation_cell["display"] == "inline"

    assert cells[3] == [None, "Rural", "100", "120"]

    assert cells[4][0]["rowspan"] == 2
    assert cells[4][0]["content"] == "South"

    # Check align environment cell
    align_cell = cells[4][3]
    assert align_cell["type"] == "equation"
    assert align_cell["display"] == "block"
    assert align_cell["labels"] == ["eq:1"]

    assert cells[5] == [None, None, "130", "160"]

    assert cells[6][1:] == ["SpaceX", "Tesla", "Neuralink"]
    assert cells[6][0] == [
        {"type": "text", "content": "Thing with"},
        {"type": "citation", "content": "elon_musk"},
    ]

    # Check caption
    caption = table["content"][1]
    assert caption["type"] == "caption"
    assert caption["content"] == "Regional Sales Distribution"


def test_nested_newcommands(parser):
    text = r"""
    \newcommand{\pow}[2][2]{#2^{#1}}
    \newcommand{\uno}{1}

    $\pow[5]{\uno}$
    """
    parsed_tokens = parser.parse(text)
    assert parsed_tokens[0]["content"] == "1^{5}"


def test_newcommand_and_grouping(parser):
    text = r"""
    \newcommand\pow[2]{#1^{#2}}

    {
    \begin{figure}[h]
        inside $\pow{3}{2}$
    \end{figure}

    }
    """
    parsed_tokens = parser.parse(text)

    # # Check total number of tokens
    # assert len(parsed_tokens) == 7

    # Check figure environment
    figure = parsed_tokens[0]
    assert figure["type"] == "figure"
    assert figure["title"] == "h"
    assert len(figure["content"]) == 2

    # Check equation inside figure
    equation = figure["content"][1]
    assert equation["type"] == "equation"
    assert equation["content"] == "3^{2}"
    assert equation["display"] == "inline"


def test_comments(parser):
    text = r"""
    % Single line comment
    Text % Comment after text
    $E=mc^2$ % Comment after equation
    \begin{equation} % Comment after environment start
        F=ma % Comment in equation
    \end{equation} % Comment after environment end
    """
    parsed_tokens = parser.parse(text)
    # Verify comments are stripped appropriately
    equations = [t for t in parsed_tokens if t["type"] == "equation"]
    assert equations[0]["content"].strip() == "E=mc^2"
    assert "F=ma" in equations[1]["content"]


def test_footnote_with_environments(parser):
    text = r"""
    \newcommand{\Fma}{$F=ma$}

    \footnote{
        Here's a list: \Fma
        \begin{itemize}
            \item First point
            \item Second point
        \end{itemize}
    }
    """
    parsed_tokens = parser.parse(text)
    assert len(parsed_tokens) == 1
    footnote = parsed_tokens[0]
    assert footnote["type"] == "footnote"

    # Check footnote content structure
    content = footnote["content"]
    assert len(content) == 3

    # Check text component
    assert content[0]["type"] == "text"
    assert content[0]["content"] == "Here's a list: "

    # Check equation component
    assert content[1]["type"] == "equation"
    assert content[1]["content"] == "F=ma"
    assert content[1]["display"] == "inline"

    # Check list component
    list_content = content[2]
    assert list_content["type"] == "list"
    items = list_content["content"]
    assert len(items) == 2

    # Check first item
    assert items[0]["type"] == "item"
    assert items[0]["content"][0]["type"] == "text"
    assert items[0]["content"][0]["content"] == "First point"

    # Check second item
    assert items[1]["type"] == "item"
    assert items[1]["content"][0]["type"] == "text"
    assert items[1]["content"][0]["content"] == "Second point"


def test_verb_and_lstlisting_commands(parser):
    text = r"""
    \begin{verbatim}
    def function():
        # This is code
        return $math$ \command{arg}
    \end{verbatim}
    
    \verb|$math$ \command{arg}|

    \begin{lstlisting}[language=Python]
    def hello():
        print("world")
    \end{lstlisting}

    \begin{lstlisting}
    def hello():
        print("world")
    \end{lstlisting}

    \verb*|ssdsds#|
    """
    parsed_tokens = parser.parse(text)
    assert parsed_tokens[0]["type"] == "code"
    assert "def function():" in parsed_tokens[0]["content"]
    assert parsed_tokens[1]["type"] == "code"
    assert parsed_tokens[1]["content"] == r"$math$ \command{arg}"

    assert parsed_tokens[2]["type"] == "code"
    assert parsed_tokens[2]["title"] == "language=Python"
    assert parsed_tokens[3]["type"] == "code"
    assert "title" not in parsed_tokens[3]

    assert parsed_tokens[4]["type"] == "code"
    assert parsed_tokens[4]["content"] == "ssdsds#"


def test_escaped_special_chars(parser):
    """Test that escaped special characters are preserved correctly"""
    text = r"""
    Price: \$100.00 (save 25\%)
    Table cell A \& B with x\_1 \#5
    Use \{braces\} for \^{superscript} and \~{n} for tilde
    100\% \& 200\$ \#1 x\_2 \{a\} \^{2} \~{n} \\textbackslash
    """
    parsed_tokens = parser.parse(text)

    # Join all text content to check the full string
    content = " ".join(
        token["content"].strip()
        for token in parsed_tokens
        if token["type"] == "text" and token["content"].strip()
    )

    # Check that special characters are preserved
    expected_patterns = [
        r"\$100.00",
        r"25\%",
        r"A \& B",
        r"x\_1",
        r"\#5",
        r"\{braces\}",
        # r'\^{superscript}',
        r"\~{n}",
        r"100\%",
        r"200\$",
        r"\#1",
        r"x\_2",
        r"\{a\}",
        # r'\^{2}',
        r"\~{n}",
        r"textbackslash",
    ]

    for pattern in expected_patterns:
        assert pattern in content, f"Expected to find '{pattern}' in parsed content"

    # Check that the content is parsed as a single text token
    # rather than being split at escaped characters
    text_tokens = [t for t in parsed_tokens if t["type"] == "text"]
    assert len(text_tokens) <= 4, "Text was split incorrectly at escaped characters"


def test_newtheorem(parser):
    text = r"""
    \newtheorem{theorem}{Theorem}[section]
    \newtheorem{lemma}[theorem]{Lemma}
    """
    parsed_tokens = parser.parse(text)
    # we ignore newtheorem commands but make sure they are parsed
    assert len(parsed_tokens) == 0


def test_new_environment(parser):
    text = r"""
    \renewenvironment{boxed}[2][This is a box]
    {
        \begin{center}
        Argument 1 (\#1)=#1\\[1ex]
        \begin{tabular}{|p{0.9\textwidth}|}
        \hline\\
        Argument 2 (\#2)=#2\\[2ex]
    }
    { 
        \\\\\hline
        \end{tabular} 
        \end{center}
    }

    \begin{boxed}[BOX]{BOX2}
    This text is \textit{inside} the environment.
    \end{boxed}
    """
    parsed_tokens = parser.parse(text)
    assert len(parsed_tokens) == 1
    assert parsed_tokens[0]["type"] == "environment"
    assert parsed_tokens[0]["name"] == "boxed"

    # Check center environment
    boxed = parsed_tokens[0]
    assert len(boxed["content"]) == 1
    center = boxed["content"][0]
    # assert center['type'] == 'environment'
    assert center["name"] == "center"

    # Check center content
    assert len(center["content"]) == 2

    # Check argument substitution text
    arg_text = center["content"][0]
    assert arg_text["type"] == "text"
    assert arg_text["content"].strip() == "Argument 1 (\\#1)=BOX"

    # Check tabular
    tabular = center["content"][1]
    assert tabular["type"] == "tabular"
    assert tabular["column_spec"] == "|p{0.9\\textwidth}|"

    # Check tabular content
    assert len(tabular["content"]) == 2

    # First row with argument substitution
    assert tabular["content"][0][0] == "Argument 2 (\\#2)=BOX2"

    # Second row with text and command
    row = tabular["content"][1][0]
    assert len(row) == 3
    assert row[0]["type"] == "text"
    assert row[0]["content"] == "This text is "
    # assert row[1]["type"] == "command"
    # assert row[1]["content"] == "\\textit{inside} "
    assert row[2]["type"] == "text"
    assert row[2]["content"] == "the environment."


def test_bibliography(parser):
    text = r"""
    \begin{thebibliography}{99}
\bibitem[sss]{KanekoHoki11}
Tomoyuki Kaneko and Kunihito Hoki.
\newblock Analysis of evaluation-function learning by comparison of sibling
  nodes.
\newblock In {\em Advances in Computer Games - 13th International Conference,
  {ACG} 2011, Tilburg, The Netherlands, November 20-22, 2011, Revised Selected
  Papers}, pages 158--169, 2011.

  \bibitem{asdsa}
  Hi there
  sadss
  \end{thebibliography}

    Hi there
    """
    parsed_tokens = parser.parse(text)
    assert len(parsed_tokens) == 2
    bibliography = parsed_tokens[0]
    assert bibliography["type"] == "bibliography"
    assert len(bibliography["content"]) == 2
    assert bibliography["content"][0]["type"] == "bibitem"
    assert bibliography["content"][1]["type"] == "bibitem"
    assert bibliography["content"][0]["cite_key"] == "KanekoHoki11"
    assert bibliography["content"][1]["cite_key"] == "asdsa"

    assert parsed_tokens[1]["type"] == "text"
    assert parsed_tokens[1]["content"].strip() == "Hi there"


def test_user_defined_commands_override(parser):
    text = r"""
    \noindent % should be ignored by formatter

    \def\noindent{NO INDENT TEXT} % but let's redefine it here

    \noindent % should now be NO INDENT TEXT
    """
    parsed_tokens = parser.parse(text)
    assert len(parsed_tokens) == 1
    assert parsed_tokens[0]["type"] == "text"
    assert parsed_tokens[0]["content"].strip() == "NO INDENT TEXT"


def test_user_defined_commands_w_legacy_formatting(parser):
    text = r"""
    \def\textbf#1{<b>#1</b>\newline}
    \textbf{Hello}
    {\bf Muhaha}
    """
    parsed_tokens = parser.parse(text)

    content = []
    for t in parsed_tokens:
        c = t["content"]
        content.extend([l.strip() for l in c.split("\n") if l.strip()])
    assert len(content) == 2
    assert content[0] == r"<b>Hello</b>"
    assert content[1] == r"<b>Muhaha</b>"
    # assert content[2] == r"\texttt{mamaa}"

    text = r"""
    \def\arxiv#1{  {\href{http://arxiv.org/abs/#1}
    {{\mdseries\ttfamily arXiv:#1}}}}

    \arxiv{1234567}
    """
    parsed_tokens = parser.parse(text)
    assert len(parsed_tokens) == 1
    assert parsed_tokens[0]["type"] == "url"
    assert parsed_tokens[0]["title"] == "arXiv:1234567"
    assert parsed_tokens[0]["content"] == "http://arxiv.org/abs/1234567"


# TODO
# def test_unknown_commands_preservation(parser):
#     """Test that unknown commands are preserved exactly as they appear"""
#     test_cases = [
#         r"\textbf{bold}",
#         r"\textcolor{red}{Colored text}",
#         r"\textsc{Small Caps}",
#         r"\textbf{\textit{nested}}",
#         r"\command{with}{multiple}{args}",
#     ]

#     for cmd in test_cases:
#         parsed = parser.parse(cmd)
#         assert 1 == len(parsed), f"Expected single token for {cmd}"
#         assert (
#             cmd == parsed[0]["content"]
#         ), f"Command not preserved exactly: expected '{cmd}', got '{parsed[0]['content']}'"


if __name__ == "__main__":
    pytest.main([__file__])
