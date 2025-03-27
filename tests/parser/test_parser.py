import pytest
import os
from latex2json.parser import FRONTEND_STYLE_MAPPING, SECTION_LEVELS, PARAGRAPH_LEVELS
from latex2json.parser.tex_parser import LatexParser
from latex2json.utils.tex_utils import flatten_all_to_string
from tests.parser.latex_samples_data import TRAINING_SECTION_TEXT


# Replace setUp with fixtures
@pytest.fixture
def parser():
    return LatexParser()


@pytest.fixture
def parsed_training_tokens(parser):
    return parser.parse(TRAINING_SECTION_TEXT)


dir_path = os.path.dirname(os.path.abspath(__file__))
samples_dir_path = os.path.join(dir_path, "samples")

# Convert test classes to groups of functions
# TestParserText1 class becomes:


def get_title(token):
    return flatten_all_to_string(token["title"])


def test_parse_sections(parsed_training_tokens):
    sections = [token for token in parsed_training_tokens if token["type"] == "section"]
    assert len(sections) == 5

    start_level = SECTION_LEVELS["section"]
    assert get_title(sections[0]) == "Training"
    assert sections[0]["level"] == start_level
    assert get_title(sections[1]) == "Training Data and Batching"
    assert sections[1]["level"] == start_level + 1
    assert get_title(sections[2]) == "Hardware and Schedule"
    assert sections[2]["level"] == start_level + 1

    regularization_section = None
    for section in sections:
        if get_title(section) == "Regularization":
            regularization_section = section
            break
    assert regularization_section is not None

    # check its label is there
    assert regularization_section["labels"] == ["sec:reg"]

    # check paragraphs
    paragraphs = [
        token for token in parsed_training_tokens if token["type"] == "paragraph"
    ]
    assert len(paragraphs) == 2
    assert get_title(paragraphs[0]) == "Residual Dropout"
    assert paragraphs[0]["level"] == PARAGRAPH_LEVELS["paragraph"]
    assert get_title(paragraphs[1]) == "Label Smoothing"
    assert paragraphs[1]["level"] == PARAGRAPH_LEVELS["paragraph"]


def test_parse_subsections(parser):
    text = r"""
    \subsection{Training Data and Batching}
    \subsubsection{Hardware and Schedule}

    \paragraph{Regularization}
    \subparagraph{Sub Regularization}
    """
    parsed_tokens = parser.parse(text)

    assert get_title(parsed_tokens[0]) == "Training Data and Batching"
    assert parsed_tokens[0]["level"] == SECTION_LEVELS["section"] + 1
    assert get_title(parsed_tokens[1]) == "Hardware and Schedule"
    assert parsed_tokens[1]["level"] == SECTION_LEVELS["section"] + 2

    assert get_title(parsed_tokens[2]) == "Regularization"
    assert parsed_tokens[2]["level"] == PARAGRAPH_LEVELS["paragraph"]
    assert get_title(parsed_tokens[3]) == "Sub Regularization"
    assert parsed_tokens[3]["level"] == PARAGRAPH_LEVELS["subparagraph"]


def test_parse_equations(parsed_training_tokens):
    equations = [
        token for token in parsed_training_tokens if token["type"] == "equation"
    ]
    # inline equations = 7
    inline_equations = [token for token in equations if token.get("display") != "block"]
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

    commands = parser.commands
    # Check if commands were stored correctly
    assert "HH" in commands
    assert "I" in commands
    assert "E" in commands
    assert "P" in commands
    assert "pow" in commands

    # Check command expansion in equations
    assert equations[0]["content"].strip() == "{3}^{{5}}"
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

    # command with required arg but if not given default to empty string
    text = r"""
    \newcommand{\ccc}[2]{arg1=#1, arg2=#2}
    \ccc / \ccc{3} / \ccc{3}{4}
    """
    parsed_tokens = parser.parse(text)
    assert len(parsed_tokens) == 1
    # split content
    split_content = parsed_tokens[0]["content"].split("/")
    assert len(split_content) == 3
    assert split_content[0].strip() == "arg1=, arg2="
    assert split_content[1].strip() == "arg1=3, arg2="
    assert split_content[2].strip() == "arg1=3, arg2=4"

    text = r"""
    \newcommand{\successrate}{58.5\%}
    \successrate{} success rate
    """
    parsed_tokens = parser.parse(text)
    assert parsed_tokens[0]["content"].strip() == r"58.5% success rate"


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


def test_complex_math_command_definitions(parser):
    text = r"""
    % Command with 3 required arguments
    \newcommand{\tensor}[3]{\mathbf{#1}_{#2}^{#3}}
    
    % Command with 1 optional and 2 required arguments
    \newcommand{\norm}[3][2]{\|#2\|_{#3}^{#1}}
    
    \newcommand{\integral}[4][0]{\int_{#1}^{#2} #3 d#4}
    
    % Command using other defined commands
    \newcommand{\tensorNorm}[4]{\norm{\tensor{#1}{#2}{#3}}{#4}}

    $\tensor{T}{i}{j}$ and $\norm[p]{x}{2}$ and $\norm{y}{1}$
    $\integral{b}{f(x)}{x}$ and $\integral[a]{b}{g(x)}{x}$
    $\tensorNorm{T}{i}{j}{\infty}$
    """
    parsed_tokens = parser.parse(text)
    equations = [token for token in parsed_tokens if token["type"] == "equation"]

    # Check command storage
    commands = parser.commands
    assert "tensor" in commands
    assert "norm" in commands
    assert "integral" in commands
    assert "tensorNorm" in commands

    # Check expansions
    expected_results = [
        r"\mathbf{{T}}_{{i}}^{{j}}",  # tensor expansion
        r"\|{x}\|_{{2}}^{{p}}",  # norm with optional arg
        r"\|{y}\|_{{1}}^{{2}}",  # norm with default optional arg
        r"\int_{{0}}^{{b}}{f(x)}d{x}",  # integral with defaults
        r"\int_{{a}}^{{b}}{g(x)}d{x}",  # integral with one optional
        r"\|{\mathbf{{T}}_{{i}}^{{j}}}\|_{{\infty}}^{{2}}",  # nested command
    ]

    for eq, expected in zip(equations, expected_results):
        assert eq["content"].replace(" ", "") == expected

    parser.clear()


def test_newtoks(parser):
    text = r"""
    \newtoks\foo
    \foo{hello}

    After toks
    """
    parsed_tokens = parser.parse(text)
    assert parsed_tokens[0]["content"].strip() == "After toks"

    assert "newtoks:foo" in parser.commands
    parser.clear()


def test_command_with_environments(parser):
    text = r"""
        \newcommand{\Fma}{$F=ma$}

        \newcommand{\myenv}[2]{
            \begin {equation*}
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
    commands = parser.commands
    assert "eps" in commands

    # Check expansion
    assert equations[0]["content"] == r"\varepsilon"


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
    assert parsed_tokens[0]["content"].strip() == "{x}+{y}"


# TestParserEnvironments tests:


def test_nested_environments(parser):
    text = r"""
    \begin{lemma}\label{tb} With probability $1-O(\eps)$, one has 
    \begin{equation}\label{t-bound}
    \t = O_{\eps}(X^\delta).
    \end{equation}
    \end  {lemma}
    """
    parsed_tokens = parser.parse(text)

    # Check environments
    assert len(parsed_tokens) == 1

    # Check lemma environment
    lemma = parsed_tokens[0]
    assert lemma["type"] == "math_env"
    assert lemma["name"] == "lemma"
    assert lemma["labels"] == ["tb"]
    assert lemma["numbered"] is True

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
    \pow{777}
    $$
    $\pow{x}$

    \[
    BLOCK ME 
    BRO
    \pow[5]{A}
    \]
    \(XX, \pow[3]{B}\)
    """
    parsed_tokens = parser.parse(text)
    equations = [token for token in parsed_tokens if token["type"] == "equation"]
    assert len(equations) == 4

    block1 = equations[0]["content"]
    block1 = block1.replace(" ", "")
    # block1 contains F=ma, E=mc^2 and 777^{2}
    assert "F=ma" in block1
    assert "E=mc^2" in block1
    assert "{777}^{{2}}" in block1
    assert equations[0]["display"] == "block"

    assert equations[1]["content"].replace(" ", "") == "{x}^{{2}}"
    assert equations[1].get("display") != "block"

    block2 = equations[2]["content"]
    assert "BLOCK ME" in block2
    assert "BRO" in block2
    assert "{A}^{{5}}" in block2.replace(" ", "")
    assert equations[2]["display"] == "block"

    last_eqn = equations[3]["content"].replace(" ", "")
    assert last_eqn == "XX,{B}^{{3}}"


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

    assert "title" not in refs[0]
    assert refs[0]["content"] == "https://www.tesla.com"
    assert refs[1]["content"] == "https://www.google.com"
    assert refs[1]["title"][0]["content"] == "Google"
    assert refs[2]["title"] == "ModalNet"
    assert refs[2]["content"] == "fig:modalnet"
    assert "title" not in refs[3]
    assert refs[3]["content"] == "fig:modalnet"

    text = r"""
    \newcommand{\cmd}{MY URL}
    \href{\cmd}{MY LINK}
    """
    parsed_tokens = parser.parse(text)
    assert len(parsed_tokens) == 1
    assert parsed_tokens[0]["type"] == "url"
    assert parsed_tokens[0]["content"] == "MY URL"


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


def test_item_with_label(parser):
    text = r"""
    \begin{itemize}
    \label{label-top}
    \item[*] First item with custom label
    \item Second item
    \item[+] \label{special-item} Third item with label % \begin{itemize}
    
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


def test_algorithmic(parser):
    text = r"""
\begin{algorithm}[H] 

\caption{Sum of Array Elements \% Here is link \url{https://www.google.com}}
\label{alg:loop}

\begin{algorithmic}[1]
\Require{$A_{1} \dots A_{N}$} 
\Ensure{$Sum$ (sum of values in the array)}
\Statex
\Function{Loop}{$A[\;]$}
  \State {$Sum$ $\gets$ {$0$}}
    \State {$N$ $\gets$ {$length(A)$}}
    \For{$k \gets 1$ to $N$}                    
        \State {$Sum$ $\gets$ {$Sum + A_{k}$}}
    \EndFor
    \State \Return {$Sum$}
\EndFunction
\end{algorithmic}

\end{algorithm}
    """
    parsed_tokens = parser.parse(text)
    algorithm = parsed_tokens[0]
    assert algorithm["type"] == "algorithm"
    assert algorithm["labels"] == ["alg:loop"]
    assert len(algorithm["content"]) == 2

    caption = algorithm["content"][0]
    assert caption["type"] == "caption"
    assert (
        caption["content"][0]["content"].strip()
        == "Sum of Array Elements % Here is link"
    )
    assert caption["content"][1]["type"] == "url"
    assert caption["content"][1]["content"] == "https://www.google.com"

    # algorithmic keep as literal?
    algorithmic = algorithm["content"][1]
    assert algorithmic["type"] == "algorithmic"
    assert r"\Require{$A_{1} \dots A_{N}$}" in algorithmic["content"]
    assert r"\Ensure{$Sum$ (sum of values in the array)}" in algorithmic["content"]
    assert algorithmic["content"].strip().endswith(r"\EndFunction")


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
    assert first_caption["content"][0]["content"] == "First pendulum design"

    # Check second subfigure
    second_subfig = subfigures[1]
    assert second_subfig["labels"] == ["fig:pendulum-b"]

    # Check second subfigure content
    second_graphics = [
        t for t in second_subfig["content"] if t["type"] == "includegraphics"
    ][0]
    second_caption = [t for t in second_subfig["content"] if t["type"] == "caption"][0]
    assert second_graphics["content"] == "example-image-b"
    assert second_caption["content"][0]["content"] == "Second pendulum design"

    # Check main caption
    main_caption = [t for t in figure["content"] if t["type"] == "caption"][0]
    assert main_caption["content"][0]["content"] == "Different pendulum clock designs"


def test_complex_table(parser):
    text = r"""
    \newcommand{\HELLO}[1]{HELLO #1}

    \begin{table}[htbp]
    \centering
    \begin {tabular}{|c|c|c|c|}
        \hline
        \multicolumn{2}{|c|}{\multirow{2}{*}{Region}} & \multicolumn{2}{c|}{Sales} \\
        \cline{3-4}
        \multicolumn{2}{|c|}{} & 2022 & 2023 \\
        \hline
        \multirow{2}{*}{North} & Urban & $x^2 + y^2 = z^2$ & 180 \\
        & Rural & 100 & 120 \\
        \hline
        \multirow{2}{*}{\textbf{South} and \texttt{Texas}} & Urban & 200 & \begin{align} \label{eq:1} E = mc^2 \\ $F = ma$ \end{align} \\
        & & 130 & 160 \\
        Thing with \cite{elon_musk} & SpaceX & Tesla & Neuralink \\
        \H{o} & \HELLO{WORLD} & \textyen\textdollar & \unknown \\
        \hline 
        AA \& BB\newline CC & DD & EE & 
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
    assert table["numbered"] == True

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

    # Check equation cell
    equation_cell = cells[2][2][0]
    assert equation_cell["type"] == "equation"
    assert equation_cell["content"] == "x^2 + y^2 = z^2"
    assert equation_cell.get("display") != "block"

    assert cells[3] == [None, "Rural", "100", "120"]

    assert cells[4][0]["rowspan"] == 2
    cell4_0 = cells[4][0]["content"]
    assert cell4_0[0]["content"] == "South"
    assert cell4_0[0]["styles"] == [FRONTEND_STYLE_MAPPING["textbf"]]
    assert cell4_0[1]["content"].strip() == "and"
    assert cell4_0[2]["content"] == "Texas"
    assert cell4_0[2]["styles"] == [FRONTEND_STYLE_MAPPING["texttt"]]

    # Check align environment cell
    align_cell = cells[4][3][0]
    assert align_cell["type"] == "equation"
    assert align_cell["display"] == "block"
    assert align_cell["labels"] == ["eq:1"]

    assert cells[5] == [None, None, "130", "160"]

    assert cells[6][1:] == ["SpaceX", "Tesla", "Neuralink"]
    assert cells[6][0] == [
        {"type": "text", "content": "Thing with "},
        {"type": "citation", "content": "elon_musk"},
    ]

    assert cells[7] == [
        "ő",
        "HELLO WORLD",
        "¥$",
        [{"type": "command", "command": "\\unknown"}],
    ]

    assert cells[8] == ["AA & BB\n CC", "DD", "EE", None]

    # Check caption
    caption = table["content"][1]
    assert caption["type"] == "caption"
    assert caption["content"][0]["content"] == "Regional Sales Distribution"


def test_tabular_with_escaped_delimiters(parser):
    text = r"""
    \begin{tabular}{cc}
        ssss \& 23333
    \end{tabular}
    """
    parsed_tokens = parser.parse(text)
    assert parsed_tokens[0]["type"] == "tabular"
    assert parsed_tokens[0]["content"] == [[r"ssss & 23333"]]


def test_nested_newcommands(parser):
    text = r"""
    \newcommand{\pow}[2][2]{#2^{#1}}
    \newcommand{\uno}{1}

    $\pow[5]{\uno}$
    """
    parsed_tokens = parser.parse(text)
    assert parsed_tokens[0]["content"] == "1^{5}"

    parser.clear()

    text = r"""
    \newcommand{\imageat}{\tocat}
    \newcommand{\tocat}{~[at]~}

    \imageat{}math.ucla.edu
"""
    tokens = parser.parse(text)
    assert len(tokens) == 1
    assert tokens[0]["content"].strip() == "~[at]~math.ucla.edu"


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
    assert figure["numbered"] == True
    assert len(figure["content"]) == 2

    # Check equation inside figure
    equation = figure["content"][1]
    assert equation["type"] == "equation"
    assert equation["content"].replace(" ", "") == "{3}^{{2}}"


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
        r"$100.00",
        r"25%",
        r"A & B",
        r"x_1",
        r"#5",
        r"{braces}",
        # r"\^{superscript}",
        r"100%",
        r"200$",
        r"#1",
        r"x_2",
        r"{a}",
        # r"\^{2}",
        r"ñ",
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
    \newtheorem{myown}{MARS}
    \newtheorem{mytheorem}{TheoremAA}[section]
    \newtheorem{mylemma}[theorem]{LemmaXX}
    """
    parsed_tokens = parser.parse(text)
    # we ignore newtheorem commands but make sure they are parsed
    assert len(parsed_tokens) == 0

    # then we check that it handles these env
    text = r"""
    \begin{myown}
        Occupy Mars
    \end{myown}

    \begin{mytheorem}
        This is a theorem
    \end{mytheorem}

    \begin{mylemma}
        Lemma Toad
    \end{mylemma}
    """
    parsed_tokens = parser.parse(text)
    assert len(parsed_tokens) == 3
    assert parsed_tokens[0]["type"] == "environment"
    assert parsed_tokens[0]["name"] == "MARS"

    assert parsed_tokens[1]["type"] == "environment"
    assert parsed_tokens[1]["name"] == "TheoremAA"

    assert parsed_tokens[2]["type"] == "environment"
    assert parsed_tokens[2]["name"] == "LemmaXX"


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
        \end {tabular} 
        \end{center}
    }

    \begin{boxed}[BOX]{BOX2}
    This text is inside the environment.
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
    assert arg_text["content"].strip() == "Argument 1 (#1)=BOX"

    # Check tabular
    tabular = center["content"][1]
    assert tabular["type"] == "tabular"
    assert tabular["column_spec"] == "|p{0.9\\textwidth}|"

    # Check tabular content
    assert len(tabular["content"]) == 2

    # First row with argument substitution
    assert tabular["content"][0][0] == "Argument 2 (#2)=BOX2"

    # Second row with text
    row = tabular["content"][1][0]
    assert row.strip() == "This text is inside the environment."


def test_author(parser):
    text = r"""
\author{
  \AND
  Ashish Vaswani\thanks{Equal contribution. Listing order is random. Jakob proposed replacing RNNs with self-attention and started the effort to evaluate this idea.
Ashish, with Illia, designed and implemented the first Transformer models and has been crucially involved in every aspect of this work. Noam proposed scaled dot-product attention, multi-head attention and the parameter-free position representation and became the other person involved in nearly every detail. Niki designed, implemented, tuned and evaluated countless model variants in our original codebase and tensor2tensor. Llion also experimented with novel model variants, was responsible for our initial codebase, and efficient inference and visualizations. Lukasz and Aidan spent countless long days designing various parts of and implementing tensor2tensor, replacing our earlier codebase, greatly improving results and massively accelerating our research.
}\\
  Google Brain\\
  \texttt{avaswani@google.com}\\
  \And
  Noam Shazeer\footnotemark[1]\\
  Google Brain\\
  \texttt{noam@google.com}\\
}
"""
    parsed_tokens = parser.parse(text)
    assert len(parsed_tokens) == 1
    assert parsed_tokens[0]["type"] == "author"

    authors = parsed_tokens[0]["content"]
    assert len(authors) == 2

    first = authors[0]
    assert first[0]["content"] == "Ashish Vaswani"

    thanks_footnote = first[1]
    assert thanks_footnote["type"] == "footnote"  # thanks is footnote
    assert thanks_footnote["content"][0]["content"].startswith("Equal contribution")

    second = authors[1]
    assert second[0]["content"] == "Noam Shazeer"
    assert second[1]["type"] == "footnote"
    assert second[1]["content"][0]["content"].startswith("1")


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

    text = r"""
    \def\arxiv#1{  {\href{http://arxiv.org/abs/#1}
    {{arXiv:#1}}}}

    \arxiv{1234567}
    """
    parsed_tokens = parser.parse(text)
    assert len(parsed_tokens) == 1
    assert parsed_tokens[0]["type"] == "url"
    assert parsed_tokens[0]["title"][0]["content"] == "arXiv:1234567"
    assert parsed_tokens[0]["content"] == "http://arxiv.org/abs/1234567"


def test_if_else_statements(parser):
    text = r"""
    \if{cond1}
        \begin{tabular}{|c|c|}
            \hline
            a & b \\
            \hline
        \end {tabular}
    \elseif{cond2}
        content2
    \else
        content3
    \fi

    More after this
    """
    parsed_tokens = parser.parse(text)

    assert len(parsed_tokens) == 2
    assert parsed_tokens[0]["type"] == "tabular"
    tabular = parsed_tokens[0]
    assert tabular["content"][0][0].strip() == "a"
    assert tabular["content"][0][1].strip() == "b"

    assert parsed_tokens[1]["type"] == "text"
    assert parsed_tokens[1]["content"].strip() == "More after this"

    # with iffalse
    text = r"""
    \iffalse
        false statement
    \else
        true statement
    \fi
    """
    parsed_tokens = parser.parse(text)
    assert len(parsed_tokens) == 1
    assert parsed_tokens[0]["type"] == "text"
    assert parsed_tokens[0]["content"].strip() == "true statement"

    # test unclosed if
    text = r"""
    \ifcond 
    """
    parsed_tokens = parser.parse(text)
    assert len(parsed_tokens) == 1
    assert parsed_tokens[0]["type"] == "command"
    assert parsed_tokens[0]["command"] == r"\ifcond"


def test_nested_items_with_environments(parser):
    text = r"""
    \begin{itemize}
    \item First item with equation:
        \begin{equation}
        E = mc^2
        \end{equation}
    \item Second item with nested list:
        \begin{enumerate}
        \item[a)] Nested item with math $F=ma$
        % ssss a  \item[bbb] SS
        \item[b)] Another nested item with:
            \begin{itemize}
            \item Deep nested item 1
            \item Deep nested item 2 with equation:
                \begin{equation}
                \nabla \cdot \mathbf{E} = \frac{\rho}{\epsilon_0}
                \end{equation}
            % \item xxxx
            \end{itemize}
        \end{enumerate}
    \end{itemize}
    """
    parsed_tokens = parser.parse(text)

    # Check outer itemize
    assert len(parsed_tokens) == 1
    outer_list = parsed_tokens[0]
    assert outer_list["type"] == "list"
    assert outer_list["name"] == "itemize"

    # Check first item with equation
    items = [t for t in outer_list["content"] if t["type"] == "item"]
    assert len(items) == 2

    first_item = items[0]
    assert first_item["type"] == "item"
    equation = [t for t in first_item["content"] if t["type"] == "equation"][0]
    assert equation["content"] == "E = mc^2"
    assert equation["display"] == "block"

    # Check second item with nested enumerate
    second_item = items[1]
    nested_list = [t for t in second_item["content"] if t["type"] == "list"][0]
    assert nested_list["name"] == "enumerate"

    # Check nested items
    nested_items = [t for t in nested_list["content"] if t["type"] == "item"]
    assert len(nested_items) == 2
    assert nested_items[0]["title"] == "a)"

    # Check math in first nested item
    math = [t for t in nested_items[0]["content"] if t["type"] == "equation"][0]
    assert math["content"] == "F=ma"

    # Check deeply nested itemize
    deep_list = [t for t in nested_items[1]["content"] if t["type"] == "list"][0]
    assert deep_list["name"] == "itemize"

    # Check deep nested items
    deep_items = [t for t in deep_list["content"] if t["type"] == "item"]
    assert len(deep_items) == 2

    # Check equation in last deep item
    last_equation = [t for t in deep_items[1]["content"] if t["type"] == "equation"][0]
    assert last_equation["display"] == "block"
    assert "\\nabla" in last_equation["content"]


def test_diacritics(parser):
    text = r"\i"
    parsed_tokens = parser.parse(text)
    assert len(parsed_tokens) == 1
    assert parsed_tokens[0]["content"] == "ı"

    text = r"\H{XXX}"
    parsed_tokens = parser.parse(text)
    assert len(parsed_tokens) == 1
    assert parsed_tokens[0]["content"] == "X̋XX"

    text = r"""\vec333 + \ddot aaaa + \H{XXX}"""
    parsed_tokens = parser.parse(text)
    assert len(parsed_tokens) == 1
    assert parsed_tokens[0]["content"] == "3⃗33 + äaaa + X̋XX"


def test_complex_frac(parser):
    text = r"""
    \newcommand{\test}[1]{TEST #1}

    \frac{
        \test{hi}, \textbf{ASDSD}
    }{
        \begin{tabular}{c}
            cell 1 & cell 2 \\
            \textbf{bold} & \textit{italic}
        \end{tabular}
    }
    """
    parsed_tokens = parser.parse(text)
    assert len(parsed_tokens) == 1

    token = parsed_tokens[0]
    assert token["type"] == "text"
    assert token["content"].strip() == "TEST hi, ASDSD / cell 1 cell 2 bold italic"


def test_legacy_formatting(parser):
    text = r"""
    \tt hello there peopleeee
    \large LARGE
    """
    content = parser.parse(text)

    assert len(content) == 2
    assert content[0]["content"].strip() == "hello there peopleeee"
    assert content[0]["styles"] == [FRONTEND_STYLE_MAPPING["texttt"]]
    assert content[1]["content"].strip() == "LARGE"
    assert content[1]["styles"] == [
        FRONTEND_STYLE_MAPPING["texttt"],
        FRONTEND_STYLE_MAPPING["textlarge"],
    ]

    # test legacy formatting inside tabular
    text = r"""
    \begin{tabular}{c}
        \tt aaa & \large bbb \\ 
        \sc eee & {\em 444}+ 333 \\ 
        \bf\underline{Hello} 55 & 
        % \begin{tabular}{x}
    \end{tabular}
    """
    parsed_tokens = parser.parse(text)
    assert len(parsed_tokens) == 1

    tabular_content = parsed_tokens[0]["content"]
    assert len(tabular_content) == 3
    assert tabular_content[0][0] == [
        {
            "type": "text",
            "content": "aaa",
            "styles": [FRONTEND_STYLE_MAPPING["texttt"]],
        }
    ]
    assert tabular_content[0][1] == [
        {
            "type": "text",
            "content": "bbb",
            "styles": [FRONTEND_STYLE_MAPPING["textlarge"]],
        }
    ]
    assert tabular_content[1][0] == [
        {
            "type": "text",
            "content": "eee",
            "styles": [FRONTEND_STYLE_MAPPING["textsc"]],
        }
    ]
    assert tabular_content[1][1] == [
        {
            "type": "text",
            "content": "444",
            "styles": [FRONTEND_STYLE_MAPPING["emph"]],
        },
        {
            "type": "text",
            "content": "+ 333",
        },
    ]

    cell5_0 = tabular_content[2][0][0]
    assert cell5_0["content"] == "Hello"
    assert cell5_0["styles"] == [
        FRONTEND_STYLE_MAPPING["textbf"],
        FRONTEND_STYLE_MAPPING["underline"],
    ]
    cell5_1 = tabular_content[2][0][1]
    assert cell5_1["content"].strip() == "55"
    assert cell5_1["styles"] == [FRONTEND_STYLE_MAPPING["textbf"]]
    assert tabular_content[2][1] == None


def test_new_if(parser):
    text = r"""
    \def\foo{BAR}
    \newif\ifvar\varfalse

    \vartrue

    Stuff after

    \ifvar\foo haha \else FALSE \fi
    """
    parsed_tokens = parser.parse(text)
    assert len(parsed_tokens) == 1
    assert (
        parsed_tokens[0]["content"].replace(" ", "").replace("\n", "")
        == "StuffafterBARhaha"
    )
    assert "newif:var" in parser.commands


def test_newlength(parser):
    text = r"""\newlength{\lenny}
    
    \lenny

    More text
    """
    parsed_tokens = parser.parse(text)
    assert len(parsed_tokens) == 1
    assert parsed_tokens[0]["content"].strip() == "More text"
    assert "newlength:lenny" in parser.commands


def test_newcounter(parser):
    text = r"""\newcounter{counterX} 
    
    \thecounterX
    aaa"""
    parsed_tokens = parser.parse(text)
    assert len(parsed_tokens) == 1
    assert parsed_tokens[0]["content"].strip() == "aaa"
    assert "newcounter:counterX" in parser.commands


def test_nested_newcommands(parser):
    text = r"""
    \newcommand*\ppp[1]{
        \def\foo#1{FOO}
        \foo#1
    }
    \ppp{bar}
    """
    parsed_tokens = parser.parse(text)
    assert len(parsed_tokens) == 1
    assert parsed_tokens[0]["content"].strip() == "FOO"
    assert "foobar" in parser.commands

    text = r"""
    \def\x{world}
    \def\cmd{hello \x}     % stores "hello \x"
    \edef\cmd#1{hello #1 \x }    % stores "hello world"

    \def\x{different}
    \cmd{333} % hello 333 world
    \x % different
    """
    parsed_tokens = parser.parse(text)
    assert len(parsed_tokens) == 1

    output = parsed_tokens[0]["content"].strip()
    assert output.startswith("hello 333 world")
    assert output.endswith("different")


def test_renew_env(parser):
    text = r"""
    \renewenvironment{XX}%
{%
  \vskip 0.075in%
  \centerline%
  {\large\bf Abstract}%
  \vspace{0.5ex}%
  \begin{quote}%
}
{
  \par%
  \end{quote}%
  \vskip 1ex%
}

\begin{XX}
  Abstract text \textbf{BOLD}
\end{XX}

"""
    parsed_tokens = parser.parse(text)
    assert len(parsed_tokens) == 1
    assert parsed_tokens[0]["type"] == "environment"
    assert parsed_tokens[0]["name"] == "XX"
    contents = parsed_tokens[0]["content"]

    assert contents[0]["type"] == "text"
    assert contents[0]["content"] == "Abstract"
    assert contents[0]["styles"] == [
        FRONTEND_STYLE_MAPPING["textlarge"],
        FRONTEND_STYLE_MAPPING["textbf"],
    ]

    q = contents[-1]
    assert q["type"] == "quote"
    qc = q["content"]
    assert qc[0]["content"].strip() == "Abstract text"
    assert qc[1]["content"] == "BOLD"


def test_weird_setlength_and_defs(parser):
    # real world example from nips_2017.sty
    text = r"""

\setlength{\topsep       }{4\p@ \@plus 1\p@   \@minus 2\p@}
\setlength{\partopsep    }{1\p@ \@plus 0.5\p@ \@minus 0.5\p@}
\setlength{\itemsep      }{2\p@ \@plus 1\p@   \@minus 0.5\p@}
\setlength{\parsep       }{2\p@ \@plus 1\p@   \@minus 0.5\p@}
\setlength{\leftmargin   }{3pc}
\setlength{\leftmargini  }{\leftmargin}
\setlength{\leftmarginii }{2em}
\setlength{\leftmarginiii}{1.5em}
\setlength{\leftmarginiv }{1.0em}
\setlength{\leftmarginv  }{0.5em}
\def\@listi  {\leftmargin\leftmargini}
\def\@listii {\leftmargin\leftmarginii
              \labelwidth\leftmarginii
              \advance\labelwidth-\labelsep
              \topsep  2\p@ \@plus 1\p@    \@minus 0.5\p@
              \parsep  1\p@ \@plus 0.5\p@ \@minus 0.5\p@
              \itemsep \parsep}

\@listii
"""
    # clean sweep
    parsed_tokens = parser.parse(text)
    assert len(parsed_tokens) == 1
    assert parsed_tokens[0]["type"] == "text"
    assert parsed_tokens[0]["content"].strip() == ""

    # all length commands should be ignored
    length_commands = [
        r"\topsep",
        r"\partopsep",
        r"\itemsep",
        r"\parsep",
        r"\leftmarginiv",
    ]
    for cmd in length_commands:
        assert len(parser.parse(cmd)) == 0


def test_csname_and_expandafter_commands(parser):
    text = r"""
    \expandafter\def\expandafter\csname\csname foo2  \expandafter\endcsname boo3! \expandafter\endcsname#1{VALID COMMAND #1}
    \foo2boo3!{MA BOII}
    \csname foo2   boo3! \endcsname{YOLO} \newline
    \csname foo2boo3! \endcsname{NO}  % not valid
    """
    parsed_tokens = parser.parse(text)
    assert len(parsed_tokens) == 1  # all test
    token = parsed_tokens[0]
    assert token["type"] == "text"
    # split all newlines and strip whitespace
    lines = [line.strip() for line in token["content"].strip().split("\n")]
    assert lines[0] == "VALID COMMAND MA BOII"
    assert lines[1] == "VALID COMMAND YOLO"
    assert lines[2] == "NO"

    # TEST FLOATING UNDEFINED CSNAME
    text = r"""
    \csname \csname foo2boo3! \expandafter\endcsname \endcsname
    Post text
    """
    parsed_tokens = parser.parse(text)
    assert len(parsed_tokens) == 1
    assert parsed_tokens[0]["type"] == "text"
    assert parsed_tokens[0]["content"].strip() == "Post text"

    # TEST double csname blocks
    text = r"""
    \def\school{SCHOOL IS COOL}
    \expandafter\let\csname oldschool\expandafter\endcsname\csname school\endcsname
    \oldschool % -> \school -> SCHOOL IS COOL
    """
    parsed_tokens = parser.parse(text)
    assert len(parsed_tokens) == 1
    assert parsed_tokens[0]["type"] == "text"
    assert parsed_tokens[0]["content"].strip() == "SCHOOL IS COOL"


def test_complex_newcommands_with_csname(parser):

    # real world example from nips_2017.sty
    text = r"""
    \newcommand*\patchAmsMathEnvironmentForLineno[1]{%
        \expandafter\let\csname old#1\expandafter\endcsname\csname #1\endcsname
        \expandafter\let\csname oldend#1\expandafter\endcsname\csname end#1\endcsname
        \renewenvironment{#1}%
          {\linenomath\csname old#1\endcsname}%
          {\csname oldend#1\endcsname\endlinenomath}%
      } 

      \def\foo{START FOO}
      \def\endfoo{END FOO}
      \patchAmsMathEnvironmentForLineno{foo}
      \begin{foo}
        INSIDE FOO ENV
      \end{foo}
      """
    parsed_tokens = parser.parse(text)
    assert len(parsed_tokens) == 1
    assert parsed_tokens[0]["type"] == "environment"
    assert parsed_tokens[0]["name"] == "foo"

    foo_content = parsed_tokens[0]["content"]
    assert len(foo_content) == 1
    linenomath = foo_content[0]
    assert linenomath["type"] == "environment"
    assert linenomath["name"] == "linenomath"
    assert len(linenomath["content"]) == 1

    inner = linenomath["content"][0]
    assert inner["type"] == "text"
    assert (
        inner["content"].replace("\n", "").replace(" ", "")
        == "STARTFOOINSIDEFOOENVENDFOO"
    )


def test_complex_commands_with_float(parser):
    # real world example from nips_2017.sty
    text = r"""
    % change this every year for notice string at bottom
    \newcommand{\@nipsordinal}{31st}
    \newcommand{\@nipsyear}{2017}
    \newcommand{\@nipslocation}{Long Beach, CA, USA}

    % handle tweaks for camera-ready copy vs. submission copy
    \if@nipsfinal
    \newcommand{\@noticestring}{%
        \@nipsordinal\/ Conference on Neural Information Processing Systems
        (NIPS \@nipsyear), \@nipslocation.%
    }
    \else
    \fi

    \newcommand{\@notice}{%
    % give a bit of extra room back to authors on first page
    \enlargethispage{2\baselineskip}%
    \@float{noticebox}[b]%
        \footnotesize\@noticestring%
    \end@float%
    }
    \@notice
"""
    parsed_tokens = parser.parse(text)
    assert len(parsed_tokens) == 1
    assert parsed_tokens[0]["type"] == "environment"
    assert parsed_tokens[0]["name"] == "noticebox"
    assert len(parsed_tokens[0]["content"]) == 1
    text_token = parsed_tokens[0]["content"][0]
    assert text_token["type"] == "text"
    assert text_token["styles"] == [FRONTEND_STYLE_MAPPING["textfootnotesize"]]
    t = text_token["content"]
    assert (
        t.find("31st")
        < t.find("Conference on Neural Information Processing Systems")
        < t.find("NIPS 2017")
        < t.find("Long Beach, CA, USA")
    )


def test_for_loops(parser):
    # basically ignore for loops entirely?
    text = r"""
    \foreach \x in {0,...,4}{
    \draw (3*\x,10)--++(0,-0.2);
    \foreach \j in {1,...,4}
        \draw[draw=blue] ({3*(\x+\j/5)},10)--++(0,-0.2);
}

After loops
"""
    parsed_tokens = parser.parse(text)
    assert len(parsed_tokens) == 1
    assert parsed_tokens[0]["type"] == "text"
    assert parsed_tokens[0]["content"].strip() == "After loops"


def test_inputs_with_files(parser):
    import os

    # regular input
    text = r"""
    PRE INPUT

    \input{%s/example.tex}

    POST INPUT
    """ % (
        samples_dir_path
    )
    parsed_tokens = parser.parse(text)
    assert len(parsed_tokens) > 2
    assert parsed_tokens[0]["type"] == "text"
    assert parsed_tokens[0]["content"].strip() == "PRE INPUT"
    assert parsed_tokens[-1]["type"] == "text"
    assert parsed_tokens[-1]["content"].strip() == "POST INPUT"

    # check input middle
    input_tokens = parsed_tokens[1:-1]
    assert len(input_tokens) == 2
    assert input_tokens[0]["type"] == "section"
    assert get_title(input_tokens[0]) == "Example"
    assert input_tokens[1]["type"] == "equation"
    assert input_tokens[1]["content"].strip() == "1+1=2"


def test_bibliography_files(parser):

    # bibliography file
    text = r"""
    PRE BIBLIOGRAPHY

    \bibliography{%s/bib}

    POST BIBLIOGRAPHY
    """ % (
        samples_dir_path
    )
    parsed_tokens = parser.parse(text)
    assert len(parsed_tokens) == 3
    assert parsed_tokens[0]["type"] == "text"
    assert parsed_tokens[0]["content"].strip() == "PRE BIBLIOGRAPHY"
    assert parsed_tokens[-1]["type"] == "text"
    assert parsed_tokens[-1]["content"].strip() == "POST BIBLIOGRAPHY"

    # check bibliography file
    bib_token = parsed_tokens[1]
    assert bib_token["type"] == "bibliography"
    assert len(bib_token["content"]) == 2

    # test multiple bibliography files (and ensure no duplicates)
    text = r"""
    \bibliography{%s/bibtex, %s/bibtex2.bib}
    """ % (
        samples_dir_path,
        samples_dir_path,
    )
    parsed_tokens = parser.parse(text)
    assert len(parsed_tokens) == 1
    assert parsed_tokens[0]["type"] == "bibliography"
    assert len(parsed_tokens[0]["content"]) == 4


def test_cvpr_sty_lastlines(parser):
    text = r"""
    \DeclareRobustCommand\onedot{\futurelet\@let@token\@onedot}
    \def\@onedot{\ifx\@let@token.\else.\null\fi\xspace}

    \def\eg{\emph{e.g}\onedot}

    This is my example \eg Haha
    """
    parsed_tokens = parser.parse(text)
    assert len(parsed_tokens) == 3
    assert parsed_tokens[0]["type"] == "text"
    assert parsed_tokens[0]["content"].strip() == "This is my example"
    assert parsed_tokens[1]["type"] == "text"
    assert parsed_tokens[1]["content"] == "e.g"
    assert parsed_tokens[1]["styles"] == [FRONTEND_STYLE_MAPPING["emph"]]
    assert parsed_tokens[2]["type"] == "text"
    assert parsed_tokens[2]["content"].strip() == "Haha"


def test_floatname(parser):
    text = r"""
    \floatname{algorithm}{Procedure}

    \begin{algorithm}
    This is procedure
    \end{algorithm}
    """
    parsed_tokens = parser.parse(text)
    assert len(parsed_tokens) == 1
    assert parsed_tokens[0]["name"] == "Procedure"


def test_paired_delimiter(parser):
    text = r"""
    \DeclarePairedDelimiter\brc{\{}{\}}% { }
    \begin{equation}
    1+1=\brc{2}
    \end{equation}

    This is \brc{x} equation
    """
    parsed_tokens = parser.parse(text)
    assert len(parsed_tokens) == 2
    assert parsed_tokens[0]["type"] == "equation"
    assert parsed_tokens[0]["content"] == r"1+1=\{{2}\}"
    assert parsed_tokens[1]["type"] == "text"
    assert parsed_tokens[1]["content"].strip() == "This is {x} equation"


def test_textcolor(parser):
    text = r"""
    \definecolor{mycolor}{HTML}{FF0000}
    \color{mycolor} Haha 
    \normalcolor Normal
    \textcolor{mycolor}{Hi there}
    """
    parsed_tokens = parser.parse(text)
    assert len(parsed_tokens) == 3
    assert parsed_tokens[0]["type"] == "text"
    assert parsed_tokens[0]["content"].strip() == "Haha"
    assert parsed_tokens[0]["styles"] == ["color=mycolor"]

    assert parsed_tokens[1]["type"] == "text"
    assert parsed_tokens[1]["content"].strip() == "Normal"
    assert parsed_tokens[1].get("styles", []) == []

    assert parsed_tokens[2]["type"] == "text"
    assert parsed_tokens[2]["content"].strip() == "Hi there"
    assert parsed_tokens[2]["styles"] == ["color=mycolor"]

    color_map = parser.get_colors()
    assert color_map == {"mycolor": {"format": "HTML", "value": "FF0000"}}

    text = r"""
    \color{red}
    \large Provided
    \normalcolor Bruh
    """
    parsed_tokens = parser.parse(text)
    assert len(parsed_tokens) == 2
    assert parsed_tokens[0]["type"] == "text"
    assert parsed_tokens[0]["content"].strip() == "Provided"
    assert parsed_tokens[0]["styles"] == [
        "color=red",
        FRONTEND_STYLE_MAPPING["textlarge"],
    ]

    assert parsed_tokens[1]["type"] == "text"
    assert parsed_tokens[1]["content"].strip() == "Bruh"
    assert parsed_tokens[1].get("styles", []) == []


def test_subfloat(parser):
    text = r"""
    \subfloat[Caption]{Content} POST
    """
    parsed_tokens = parser.parse(text)
    assert len(parsed_tokens) == 2
    assert parsed_tokens[0]["type"] == "group"
    assert parsed_tokens[0]["content"] == [
        {"type": "caption", "content": [{"type": "text", "content": "Caption"}]},
        {"type": "text", "content": "Content"},
    ]

    assert parsed_tokens[1]["content"].strip() == "POST"


def test_delim_braces(parser):
    text = r"""{\color{darkgreen}20}/{\color{darkgray}30}"""

    parsed_tokens = parser.parse(text)
    assert len(parsed_tokens) == 3
    assert parsed_tokens[0]["type"] == "text"
    assert parsed_tokens[0]["content"] == "20"
    assert parsed_tokens[0]["styles"] == ["color=darkgreen"]

    assert parsed_tokens[1]["type"] == "text"
    assert parsed_tokens[1]["content"] == "/"

    assert parsed_tokens[2]["type"] == "text"
    assert parsed_tokens[2]["content"] == "30"
    assert parsed_tokens[2]["styles"] == ["color=darkgray"]

    text = r"""
    \begin{tabular}{cc}
        w {\color{darkgreen}20}/{\color{darkgray}30}
    \end{tabular} 
"""
    parsed_tokens = parser.parse(text)
    assert len(parsed_tokens) == 1
    assert parsed_tokens[0]["type"] == "tabular"
    assert parsed_tokens[0]["content"] == [
        [
            [
                {"type": "text", "content": "w"},
                {"type": "text", "content": "20", "styles": ["color=darkgreen"]},
                {"type": "text", "content": "/"},
                {"type": "text", "content": "30", "styles": ["color=darkgray"]},
            ]
        ]
    ]


def test_sty_usepackage(parser):
    text = r"""
    \usepackage{%s/package2}

    \bar
    """ % (
        samples_dir_path
    )
    parsed_tokens = parser.parse(text, preprocess=True)
    assert len(parsed_tokens) == 1
    assert parsed_tokens[0]["type"] == "text"
    assert parsed_tokens[0]["content"].strip() == "foo"


def test_preprocess_and_def_beginend(parser):
    text = r"""
    \def\bea{\begin{eqnarray}}
    \def\eea{\end{eqnarray}}
    
    \bea
    1+1=2
    \eea
    """
    parsed_tokens = parser.parse(text, preprocess=True)
    assert len(parsed_tokens) == 1
    assert parsed_tokens[0]["type"] == "equation"
    assert parsed_tokens[0]["content"].strip() == r"1+1=2"

    assert "bea" in parser.commands
    assert "eea" in parser.commands


def test_simple_quotes(parser):
    text = r"""
    ``aaa''
    `aaa'
    'aaa'
    "aaa"
    """
    parsed_tokens = parser.parse(text, preprocess=True)
    assert len(parsed_tokens) == 1
    assert parsed_tokens[0]["type"] == "text"
    out = parsed_tokens[0]["content"]
    assert out.strip().split(" ") == ['"aaa"', "'aaa'", "'aaa'", '"aaa"']


def test_newcommand_nested_equations(parser):
    text = r"""
    \newcommand{\app}{\raise.17ex\hbox{$\scriptstyle\sim$}}
    $\app$3
    """
    parsed_tokens = parser.parse(text, preprocess=True)
    assert len(parsed_tokens) == 2
    assert parsed_tokens[0]["type"] == "equation"
    assert parsed_tokens[0]["content"] == r"\hbox{$\scriptstyle\sim$}"
    assert parsed_tokens[1]["type"] == "text"
    assert parsed_tokens[1]["content"] == "3"


def test_math_mode_padding(parser):
    # ensure that math mode padding is properly padded.
    # this is to ensure e.g. \vert#1->\vert{x}instead of error-prone \vert#1 -> \vertx
    text = r"""
    \newcommand{\abs}[1]{\left\vert#1\right\vert}
    $\abs{x}$
    """
    parsed_tokens = parser.parse(text, preprocess=True)
    assert len(parsed_tokens) == 1
    assert parsed_tokens[0]["type"] == "equation"
    assert parsed_tokens[0]["content"] == r"\left\vert{x}\right\vert"


def test_ifstar_definitions(parser):
    text = r"""
    \def\cmd{\@ifstar{star}{nostar}}
    \newcommand{\cmdxx}{\cmd}
    \cmd,\cmd*\cmdxx,\cmdxx***
    """
    parsed_tokens = parser.parse(text, preprocess=True)
    assert len(parsed_tokens) == 1
    assert parsed_tokens[0]["type"] == "text"
    assert parsed_tokens[0]["content"] == "nostar,starnostar,star**"


def test_nested_macro_inner_args_substitution(parser):
    parser.clear()

    text = r"""
    \newcommand{\outermacro}[2]{
        Outer parameters: #1 and #2

        \newcommand{\innermacro}[2]{
            Outer-inner parameters: #1 and #2
            Inner parameters: ##1 and ##2
        }
        \innermacro{inner-first}{inner-second}
    }

    \outermacro{outer-first}{outer-second}
    """

    parsed_tokens = parser.parse(text)
    assert len(parsed_tokens) == 1
    assert parsed_tokens[0]["type"] == "text"
    out = parsed_tokens[0]["content"].strip()
    assert out.startswith("Outer parameters: outer-first and outer-second")
    assert "Outer-inner parameters: outer-first and outer-second" in out
    assert out.endswith("Inner parameters: inner-first and inner-second")

    # now outermacro runs again and changes the definition
    parsed_tokens = parser.parse(r"\outermacro{111}{222}")
    assert len(parsed_tokens) == 1
    assert parsed_tokens[0]["type"] == "text"
    out = parsed_tokens[0]["content"].strip()
    assert out.startswith("Outer parameters: 111 and 222")
    assert "Outer-inner parameters: 111 and 222" in out
    assert out.endswith("Inner parameters: inner-first and inner-second")

    # check that the inner macro is updated and can run standalone
    parsed_tokens = parser.parse(r"\innermacro{3}{4}")
    assert len(parsed_tokens) == 1
    assert parsed_tokens[0]["type"] == "text"
    out = parsed_tokens[0]["content"].strip()
    assert out.startswith("Outer-inner parameters: 111 and 222")
    assert out.endswith("Inner parameters: 3 and 4")


def test_keyval_definitions(parser):
    text = r"""
        \define@key{pubdet}{title}{%
            \renewcommand{\toc@title}{#1}
        }

        \setkeys{pubdet}{title=Hello TITLE}

        \toc@title
    """
    parsed_tokens = parser.parse(text, preprocess=True)
    assert len(parsed_tokens) == 1
    assert parsed_tokens[0]["type"] == "text"
    assert parsed_tokens[0]["content"].strip() == "Hello TITLE"


if __name__ == "__main__":
    pytest.main([__file__])
