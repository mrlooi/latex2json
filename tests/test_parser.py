import unittest
from src.patterns import SECTION_LEVELS
from src.tex_parser import LatexParser
from tests.latex_samples_data import TRAINING_SECTION_TEXT

class TestParserText1(unittest.TestCase):
    def setUp(self):
        self.parser = LatexParser()
        self.parsed_tokens = self.parser.parse(TRAINING_SECTION_TEXT)

    def test_parse_sections(self):
        sections = [token for token in self.parsed_tokens if token["type"] == "section"]
        self.assertEqual(len(sections), 7)

        start_level = SECTION_LEVELS['section']
        self.assertEqual(sections[0]['title'], 'Training')
        self.assertEqual(sections[0]['level'], start_level)
        self.assertEqual(sections[1]['title'], 'Training Data and Batching')
        self.assertEqual(sections[1]['level'], start_level + 1)
        self.assertEqual(sections[2]['title'], 'Hardware and Schedule')
        self.assertEqual(sections[2]['level'], start_level + 1)

        regularization_section = None
        for section in sections:
            if section['title'] == 'Regularization':
                regularization_section = section
                break
        self.assertIsNotNone(regularization_section)

        # check its label is there
        self.assertEqual(regularization_section['labels'], ['sec:reg'])
    
    def test_parse_subsections(self):
        text = r"""
        \subsection{Training Data and Batching}
        \subsubsection{Hardware and Schedule}

        \paragraph{Regularization}
        \subparagraph{Sub Regularization}
        """
        parsed_tokens = self.parser.parse(text)
        sections = [token for token in parsed_tokens if token["type"] == "section"]

        self.assertEqual(sections[0]['title'], 'Training Data and Batching')
        self.assertEqual(sections[0]['level'], SECTION_LEVELS['section'] + 1)
        self.assertEqual(sections[1]['title'], 'Hardware and Schedule')
        self.assertEqual(sections[1]['level'], SECTION_LEVELS['section'] + 2)

        self.assertEqual(sections[2]['title'], 'Regularization')
        self.assertEqual(sections[2]['level'], SECTION_LEVELS['paragraph'])
        self.assertEqual(sections[3]['title'], 'Sub Regularization')
        self.assertEqual(sections[3]['level'], SECTION_LEVELS['paragraph'] + 1)

    def test_parse_equations(self):
        equations = [token for token in self.parsed_tokens if token["type"] == "equation"]
        # inline equations = 7
        inline_equations = [token for token in equations if token["display"] == "inline"]
        self.assertEqual(len(inline_equations), 7)
        self.assertEqual(len(equations), 8)

    def test_parse_citations(self):
        # number of citations=5
        citations = [token for token in self.parsed_tokens if token["type"] == "citation"]
        self.assertEqual(len(citations), 5)
        self.assertEqual(citations[0]['content'], 'DBLP:journals/corr/BritzGLL17')
    
    def test_parse_refs(self):
        refs = [token for token in self.parsed_tokens if token["type"] == "ref"]
        self.assertEqual(len(refs), 1)
        self.assertEqual(refs[0]['content'], 'tab:variations')

    def test_parse_labels(self):
        labels = self.parser.labels
        self.assertEqual(len(labels), 1)
        # assert 'sec:reg' in labels
        self.assertIn('sec:reg', labels)

class TestParserNewCommands(unittest.TestCase):
    def setUp(self):
        self.parser = LatexParser()

    def test_command_definitions(self):
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
        parsed_tokens = self.parser.parse(text)
        equations = [token for token in parsed_tokens if token["type"] == "equation"]
        
        commands = self.parser.command_processor.commands
        # Check if commands were stored correctly
        self.assertIn('HH', commands)
        self.assertIn('I', commands)
        self.assertIn('E', commands)
        self.assertIn('P', commands)
        self.assertIn('pow', commands)

        # Check command expansion in equations
        self.assertEqual(equations[0]["content"], "3^{5}")
        self.assertEqual(equations[1]["content"], r"\mathbb{H}")
        self.assertEqual(equations[2]["content"], r"\mathbb{I}")
        self.assertEqual(equations[3]["content"], r"d_{\text{model}}")

        self.assertEqual(parsed_tokens[-2]["content"], "Single line of text")
        last_token = parsed_tokens[-1]["content"]
        split_content = [line.strip() for line in last_token.split("\n") if line.strip()]
        self.assertEqual(len(split_content), 3)
        self.assertEqual(split_content[0], "First paragraph")
        self.assertEqual(split_content[1], "Second paragraph")
        self.assertEqual(split_content[2], "(Edited by me)")


    def test_complex_command_definitions(self):
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
        parsed_tokens = self.parser.parse(text)
        equations = [token for token in parsed_tokens if token["type"] == "equation"]

        # Check command storage
        commands = self.parser.command_processor.commands
        self.assertIn('tensor', commands)
        self.assertIn('norm', commands)
        self.assertIn('integral', commands)
        self.assertIn('tensorNorm', commands)

        # Check expansions
        expected_results = [
            "\\mathbf{T}_{i}^{j}",  # tensor expansion
            "\\|x\\|_{2}^{p}",      # norm with optional arg
            "\\|y\\|_{1}^{2}",      # norm with default optional arg
            "\\int_{0}^{b} f(x) \\, dx",  # integral with defaults
            "\\int_{a}^{b} g(x) \\, dx",  # integral with one optional
            "\\|\\mathbf{T}_{i}^{j}\\|_{\\infty}^{2}"  # nested command
        ]

        for eq, expected in zip(equations, expected_results):
            self.assertEqual(eq["content"], expected)

    def test_command_with_environments(self):
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
        parsed_tokens = self.parser.parse(text)
                # Check that we got one equation token
        self.assertEqual(len(parsed_tokens), 1)
        equation = parsed_tokens[0]
        
        # Verify equation properties
        self.assertEqual(equation["type"], "equation")
        self.assertEqual(equation["display"], "block")
        
        # Verify equation content includes both the substituted parameters 
        # and the expanded \Fma command
        self.assertIn("E = mc^2", equation["content"])
        self.assertIn("F=ma", equation["content"])

    def test_alt_command_definitions(self):
        """Test command definitions without braces"""
        text = r"""
        \newcommand\eps{\varepsilon}

        $\eps$
        """
        parsed_tokens = self.parser.parse(text)
        equations = [token for token in parsed_tokens if token["type"] == "equation"]
        
        # Check command storage
        commands = self.parser.command_processor.commands
        self.assertIn('eps', commands)
        
        # Check expansion
        self.assertEqual(equations[0]["content"], r"\varepsilon")
        self.assertEqual(equations[0]["display"], "inline")

class TestParserEnvironments(unittest.TestCase):
    def setUp(self):
        self.parser = LatexParser()

    def test_nested_environments(self):
        text = r"""
        \begin{lemma}\label{tb} With probability $1-O(\eps)$, one has 
        \begin{equation}\label{t-bound}
        \t = O_{\eps}(X^\delta).
        \end{equation}
        \end{lemma}
        """
        parsed_tokens = self.parser.parse(text)
        
        # Check environments
        environments = [token for token in parsed_tokens if token["type"] == "environment"]
        self.assertEqual(len(environments), 1)
        
        # Check lemma environment
        lemma = environments[0]
        self.assertEqual(lemma["name"], "lemma")
        self.assertEqual(lemma["labels"], ["tb"])
        
        # Check equation environment
        equation = lemma['content'][0]
        for token in lemma['content']:
            if token['type'] == 'equation' and 'labels' in token:
                equation = token
                break
        self.assertEqual(equation["labels"], ["t-bound"])

    def test_multiple_environments(self):
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
        parsed_tokens = self.parser.parse(text)
        theorem = parsed_tokens[0]
        
        self.assertEqual(theorem["name"], "theorem")

        # check proof is nested inside theorem
        proof = theorem['content'][1]
        self.assertEqual(proof["name"], "proof")

        # check subproof is nested inside proof
        self.assertEqual(proof['content'][0]['content'], 'Proof details')
        subproof = proof['content'][1]
        self.assertEqual(subproof["name"], "subproof")

        corollary = parsed_tokens[1]
        self.assertEqual(corollary["name"], "corollary")
        self.assertEqual(corollary["labels"], ["COL"])

        # check equation is nested inside corollary
        equation = corollary['content'][0]
        self.assertEqual(equation["content"], r"\E \left|\sum_{j=1}^n \g(j)\right|^2 \leq C^2")
        self.assertEqual(equation["labels"], ["nax"])


class TestParserEquations(unittest.TestCase):
    def setUp(self):
        self.parser = LatexParser()

    def test_split_equation(self):
        text = r"""
        \begin{equation}\label{jock}
        \begin{split}
        &\frac{1}{H} \sum_{H < H' \leq 2H} \sum_{a \in [1,\q^k], \hbox{ good}} \left|\sum_{m=1}^{H'} \tilde{\boldsymbol{\chi}}(a+m) \sum_{n = a+m \ (\q^k)} \frac{\h(n)}{n^{1+1/\log X}}\right|^2 \\
        &\quad \ll_\eps \frac{\log^2 X}{\q^k} .
        \end{split}
        \end{equation}
        """
        parsed_tokens = self.parser.parse(text)
        equation = parsed_tokens[0]
        self.assertEqual(equation["type"], "equation")
        self.assertEqual(equation["labels"], ["jock"])

        # check begin{split} is nested inside equation
        split = equation['content']
        self.assertEqual(split.startswith(r"\begin{split}"), True)
        self.assertEqual(split.endswith(r"\end{split}"), True)

    def test_parse_equations(self):
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
        parsed_tokens = self.parser.parse(text)
        equations = [token for token in parsed_tokens if token["type"] == "equation"]
        self.assertEqual(len(equations), 4)

        block1 = equations[0]['content']
        # block1 contains F=ma, E=mc^2 and ELON^{2}
        self.assertIn('F=ma', block1)   
        self.assertIn('E=mc^2', block1)
        self.assertIn('ELON^{2}', block1)
        self.assertEqual(equations[0]['display'], 'block')

        self.assertEqual(equations[1]['display'], 'inline')
        self.assertEqual(equations[1]['content'], 'x^{2}')

        block2 = equations[2]['content']
        self.assertIn('BLOCK ME', block2)
        self.assertIn('BRO', block2)
        self.assertIn('A^{5}', block2)
        self.assertEqual(equations[2]['display'], 'block')

        inline2 = equations[3]['content']
        self.assertEqual(inline2, 'INLINE, B^{3}')
        self.assertEqual(equations[3]['display'], 'inline')

    def test_align_block(self):
        text = r"""
        \begin{align*}
        \left(\E \left|\sum_{j=1}^n \g(jd)\right|^2\right)^{1/2} &= \left(\E \left| \sum_{i \geq 0: 3^i \leq n} \boldsymbol{\eps}_{i+l} \sum_{m \leq n/3^i} \chi_3(md') \right|^2\right)^{1/2} \\
        &\leq \left(\sum_{i \geq 0: 3^i \leq n} 1\right)^{1/2}\\
        &\ll \sqrt{\log n},
        \end{align*}
        """
        parsed_tokens = self.parser.parse(text)
        align = parsed_tokens[0]
        self.assertEqual(align['type'], 'equation')
        self.assertEqual(align['display'], 'block')
        content = align['content']
        self.assertEqual(content.startswith(r'\left('), True)
        self.assertEqual(content.endswith(r'\sqrt{\log n},'), True)

class TestParserCitations(unittest.TestCase):
    def setUp(self):
        self.parser = LatexParser()

    def test_parse_citations(self):
        text = r"""
        Regular citation \cite{DBLP:journals/corr/BritzGLL17}
        Citation with title \cite[Theorem 2.1]{smith2023}
        Multiple citations \cite{paper1,paper2}
        """
        parsed_tokens = self.parser.parse(text)
        citations = [token for token in parsed_tokens if token["type"] == "citation"]

        # Test regular citation
        self.assertEqual(citations[0]['content'], 'DBLP:journals/corr/BritzGLL17')
        self.assertNotIn('title', citations[0])

        # Test citation with title
        self.assertEqual(citations[1]['content'], 'smith2023')
        self.assertEqual(citations[1]['title'], 'Theorem 2.1')

        # Test multiple citations
        self.assertEqual(citations[2]['content'], 'paper1,paper2')
        self.assertNotIn('title', citations[2])

class TestParserRefs(unittest.TestCase):
    def setUp(self):
        self.parser = LatexParser()
    
    def test_parse_refs(self):
        text = r"""
        \url{https://www.tesla.com}
        \href{https://www.google.com}{Google}

        \hyperref[fig:modalnet]{ModalNet}
        \ref{fig:modalnet}
        """
        parsed_tokens = self.parser.parse(text)
        refs = [token for token in parsed_tokens]
        self.assertEqual(len(refs), 4)

        self.assertEqual(refs[0]['type'], 'url')
        self.assertEqual(refs[1]['type'], 'url')
        self.assertEqual(refs[2]['type'], 'ref')
        self.assertEqual(refs[3]['type'], 'ref')

        self.assertEqual(refs[0]['content'], 'https://www.tesla.com')
        self.assertEqual(refs[1]['content'], 'https://www.google.com')
        self.assertEqual(refs[2]['title'], 'fig:modalnet')
        self.assertEqual('title' not in refs[0], True)
        self.assertEqual(refs[1]['title'], 'Google')
        self.assertEqual(refs[2]['content'], 'ModalNet')
        self.assertEqual('title' not in refs[3], True)
        self.assertEqual(refs[3]['content'], 'fig:modalnet')

class TestParserItems(unittest.TestCase):
    def setUp(self):
        self.parser = LatexParser()

    def test_nested_items(self):
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
        parsed_tokens = self.parser.parse(text)
        
        # Check the enumerate environment
        self.assertEqual(len(parsed_tokens), 1)
        enum_env = parsed_tokens[0]
        self.assertEqual(enum_env["type"], "list")
        
        # Check items within enumerate
        items = [token for token in enum_env["content"] if token["type"] == "item"]
        self.assertEqual(len(items), 2)
        
        # Check first item's nested content
        first_item = items[0]
        minipages = [token for token in first_item["content"] if token["type"] == "environment" and token["name"] == "minipage"]
        self.assertEqual(len(minipages), 2)
        
        # Check equations in first minipage
        first_minipage = minipages[0]
        equations = [token for token in first_minipage["content"] if token["type"] == "equation"]
        self.assertEqual(len(equations), 2)
        self.assertEqual(equations[0]["content"], "E = mc^2")
        self.assertEqual(equations[1]["content"], "F = ma")
        
        # Check second minipage content
        second_minipage = minipages[1]
        graphics = [token for token in second_minipage["content"] if token["type"] == "includegraphics"]
        self.assertEqual(len(graphics), 1)
        self.assertEqual(graphics[0]["content"], "example-image")
        
        # Check second item's equation
        second_item = items[1]
        equations = [token for token in second_item["content"] if token["type"] == "equation"]
        self.assertEqual(len(equations), 1)
        self.assertEqual(equations[0]["content"], "asdasdsads")
        self.assertEqual(equations[0]["display"], "inline")

    def test_item_with_label(self):
        text = r"""
        \begin{itemize}
        \label{label-top}
        \item[*] First item with custom label
        \item Second item
        \item[+] \label{special-item} Third item with label
        \end{itemize}
        """
        parsed_tokens = self.parser.parse(text)
        
        itemize = parsed_tokens[0]
        self.assertEqual(itemize["type"], "list")
        self.assertEqual(itemize["labels"], ["label-top"])
        
        items = [token for token in itemize["content"] if token["type"] == "item"]
        self.assertEqual(len(items), 3)
        
        # Check custom labels
        # self.assertEqual(items[0]["title"], "*")
        self.assertEqual(items[0]["content"][0]['content'], "First item with custom label")
        self.assertEqual(items[1]["content"][0]['content'], "Second item")
        self.assertEqual(items[2]["content"][0]['content'], "Third item with label")
        # self.assertEqual(items[2]["title"], "+")
        
        # Check item with label
        self.assertEqual(items[2]["labels"], ["special-item"])

class TestParserFigures(unittest.TestCase):
    def setUp(self):
        self.parser = LatexParser()

    def test_nested_figures(self):
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
        parsed_tokens = self.parser.parse(text)
        
        # Check main figure
        self.assertEqual(len(parsed_tokens), 1)
        figure = parsed_tokens[0]
        self.assertEqual(figure["type"], "figure")
        self.assertEqual(figure["labels"], ["fig:pendulum-designs"])
        
        # Check subfigures
        subfigures = [token for token in figure["content"] if token["type"] == "figure"]
        self.assertEqual(len(subfigures), 2)
        
        # Check first subfigure
        first_subfig = subfigures[0]
        self.assertEqual(first_subfig["labels"], ["fig:pendulum-a"])
        
        # Check first subfigure content
        first_graphics = [t for t in first_subfig["content"] if t["type"] == "includegraphics"][0]
        first_caption = [t for t in first_subfig["content"] if t["type"] == "caption"][0]
        self.assertEqual(first_graphics["content"], "image.png")
        self.assertEqual(first_caption["content"], "First pendulum design")
        
        # Check second subfigure
        second_subfig = subfigures[1]
        self.assertEqual(second_subfig["labels"], ["fig:pendulum-b"])
        
        # Check second subfigure content
        second_graphics = [t for t in second_subfig["content"] if t["type"] == "includegraphics"][0]
        second_caption = [t for t in second_subfig["content"] if t["type"] == "caption"][0]
        self.assertEqual(second_graphics["content"], "example-image-b")
        self.assertEqual(second_caption["content"], "Second pendulum design")
        
        # Check main caption
        main_caption = [t for t in figure["content"] if t["type"] == "caption"][0]
        self.assertEqual(main_caption["content"], "Different pendulum clock designs")

        # # check titles
        # self.assertEqual(figure["title"], "htbp")
        # self.assertEqual(first_subfig["title"], "b")
        # self.assertEqual(second_subfig["title"], "b")

class TestParserTables(unittest.TestCase):
    def setUp(self):
        self.parser = LatexParser()

    def test_complex_table(self):
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
            \hline
        \end{tabular}
        \caption{Regional Sales Distribution}
        \label{tab:sales}
        \end{table}
        """
        parsed_tokens = self.parser.parse(text)
        table = parsed_tokens[0]
        
        # Check table properties
        self.assertEqual(table["type"], "table")
        self.assertEqual(table["title"], "htbp")
        self.assertEqual(table["labels"], ["tab:sales"])
        
        # Check tabular content
        tabular = table["content"][0]
        self.assertEqual(tabular["type"], "tabular")
        self.assertEqual(tabular["column_spec"], "|c|c|c|c|")
        
        # Check specific cells
        cells = tabular["content"]
        
        # Check header cell with multicolumn and multirow
        self.assertEqual(cells[0][0]["content"], "Region")
        self.assertEqual(cells[0][0]["rowspan"], 2)
        self.assertEqual(cells[0][0]["colspan"], 2)
        
        # Check equation cell
        equation_cell = cells[2][2]
        self.assertEqual(equation_cell["type"], "equation")
        self.assertEqual(equation_cell["content"], "x^2 + y^2 = z^2")
        self.assertEqual(equation_cell["display"], "inline")
        
        # Check align environment cell
        align_cell = cells[4][3]
        self.assertEqual(align_cell["type"], "equation")
        self.assertEqual(align_cell["display"], "block")
        self.assertEqual(align_cell["labels"], ["eq:1"])
        
        # Check caption
        caption = table["content"][1]
        self.assertEqual(caption["type"], "caption")
        self.assertEqual(caption["content"], "Regional Sales Distribution")

class TestUnknownCommands(unittest.TestCase):
    def setUp(self):
        self.parser = LatexParser()


    def test_unknown_commands_preservation(self):
        """Test that unknown commands are preserved exactly as they appear"""
        test_cases = [
            r'\textbf{bold}',
            r'\textcolor{red}{Colored text}',
            r'\textsc{Small Caps}',
            r'\textbf{\textit{nested}}',
            r'\command{with}{multiple}{args}',
        ]
        
        for cmd in test_cases:
            parsed = self.parser.parse(cmd)
            self.assertEqual(1, len(parsed), f"Expected single token for {cmd}")
            # self.assertEqual("text", parsed[0]["type"])
            self.assertEqual(cmd, parsed[0]["content"], 
                           f"Command not preserved exactly: expected '{cmd}', got '{parsed[0]['content']}'")

    def test_unknown_commands(self):
        text = r"""
        Simple \textbf{bold} and \textit{italic} text.
        
        \begin{itemize}
        \item \textcolor{red}{Colored text} in a list
        \item Nested unknown commands: \textbf{\textit{both}}
        \end{itemize}

        \begin{equation}
        \mathcal{L} = \textbf{x} + y
        \end{equation}

        \begin{figure}
            \centering
            \includegraphics[width=0.8\textwidth]{image.png}
            \captionof{Table}{\textsc{Small Caps} and \textsf{Sans Serif} in caption}
        \end{figure}
        """
        parsed_tokens = self.parser.parse(text)

        # # Check top-level unknown commands
        # text_tokens = [t for t in parsed_tokens if t['type'] == 'text']
        # print(text_tokens)
        # self.assertTrue(any('\\textbf{bold}' in t['content'] for t in text_tokens))
        # self.assertTrue(any('\\textit{italic}' in t['content'] for t in text_tokens))

        # Check unknown commands in list environment
        list_env = [t for t in parsed_tokens if t['type'] == 'list'][0]
        items = [t for t in list_env['content'] if t['type'] == 'item']
        self.assertTrue('\\textcolor{red}{Colored text}' in items[0]['content'][0]['content'])
        # self.assertTrue('\\textbf{\\textit{both}}' in items[1]['content'][0]['content'])

        # Check unknown commands in equation
        equation = [t for t in parsed_tokens if t['type'] == 'equation'][0]
        self.assertTrue('\\textbf{x}' in equation['content'])

        # Check unknown commands in figure caption
        figure = [t for t in parsed_tokens if t['type'] == 'figure'][0]
        caption = [t for t in figure['content'] if t['type'] == 'caption'][0]
        self.assertTrue('\\textsc{Small Caps}' in caption['content'])
        self.assertTrue('\\textsf{Sans Serif}' in caption['content'])

    def test_newcommand_with_unknown_command(self):
        text = r"""
        \newcommand{\pow}[2][2]{#2^{#1}}
        \newcommand{\uno}{1}

        \textbf{$\pow[5]{\uno}$}
        """
        parsed_tokens = self.parser.parse(text)
        self.assertEqual(parsed_tokens[0]['content'], "\\textbf{$1^{5}$}")

class TestMisc(unittest.TestCase):
    def setUp(self):
        self.parser = LatexParser()

    def test_footnote_with_environments(self):
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
        parsed_tokens = self.parser.parse(text)
        self.assertEqual(len(parsed_tokens), 1)
        footnote = parsed_tokens[0]
        self.assertEqual(footnote['type'], 'footnote')
        
        # Check footnote content structure
        content = footnote['content']
        self.assertEqual(len(content), 3)
        
        # Check text component
        self.assertEqual(content[0]['type'], 'text')
        self.assertEqual(content[0]['content'], "Here's a list:")
        
        # Check equation component
        self.assertEqual(content[1]['type'], 'equation')
        self.assertEqual(content[1]['content'], 'F=ma')
        self.assertEqual(content[1]['display'], 'inline')
        
        # Check list component
        list_content = content[2]
        self.assertEqual(list_content['type'], 'list')
        items = list_content['content']
        self.assertEqual(len(items), 2)
        
        # Check first item
        self.assertEqual(items[0]['type'], 'item')
        self.assertEqual(items[0]['content'][0]['type'], 'text')
        self.assertEqual(items[0]['content'][0]['content'], 'First point')
        
        # Check second item
        self.assertEqual(items[1]['type'], 'item')
        self.assertEqual(items[1]['content'][0]['type'], 'text')
        self.assertEqual(items[1]['content'][0]['content'], 'Second point')

if __name__ == '__main__':
    unittest.main()