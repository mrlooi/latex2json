import unittest
from src.tex_parser import LatexParser
from tests.latex_samples_data import TRAINING_SECTION_TEXT

class TestParserText1(unittest.TestCase):
    def setUp(self):
        self.parser = LatexParser()
        self.parsed_tokens = self.parser.parse(TRAINING_SECTION_TEXT)

    def test_parse_sections(self):
        sections = [token for token in self.parsed_tokens if token["type"] == "section"]
        self.assertEqual(len(sections), 7)
        self.assertEqual(sections[0]['title'], 'Training')
        self.assertEqual(sections[0]['level'], 1)
        self.assertEqual(sections[1]['title'], 'Training Data and Batching')
        self.assertEqual(sections[1]['level'], 2)
        self.assertEqual(sections[2]['title'], 'Hardware and Schedule')
        self.assertEqual(sections[2]['level'], 2)

        regularization_section = None
        for section in sections:
            if section['title'] == 'Regularization':
                regularization_section = section
                break
        self.assertIsNotNone(regularization_section)

        # check its label is there
        self.assertEqual(regularization_section['label'], 'sec:reg')

    # def test_parse_equations(self):
    #     equations = [token for token in self.parsed_tokens if token["type"] == "equation"]
    #     # inline equations = 7
    #     inline_equations = [token for token in equations if token["display"] == "inline"]
    #     self.assertEqual(len(inline_equations), 7)
    #     self.assertEqual(len(equations), 8)

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


# class TestParserTable(unittest.TestCase):
#     def setUp(self):
#         self.parser = LatexParser()

#     def test_nested_environments(self):
#         text = r"""
#         \begin{lemma}\label{tb} With probability $1-O(\eps)$, one has 
# \begin{equation}\label{t-bound}
# \t = O_{\eps}(X^\delta).
# \end{equation}
# \end{lemma}
# """
#         parsed_tokens = self.parser.parse(text)
#         print(parsed_tokens)


class TestParserCommands(unittest.TestCase):
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
        self.assertEqual(lemma["label"], "tb")
        
        # # Check equation environment (inside lemma['content'])
        equation = lemma['content'][0]
        for token in lemma['content']:
            if token['type'] == 'equation' and 'label' in token:
                equation = token
                break
        self.assertEqual(equation["label"], "t-bound")

    def test_multiple_environments(self):
        text = r"""
        \begin{theorem}
            Statement
            \begin{proof}
                Proof details
                \begin{enumerate}
                    \item First point
                    \item Second point
                \end{enumerate}
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

        # check enumerate is nested inside proof
        self.assertEqual(proof['content'][0]['content'], 'Proof details')
        enumerate = proof['content'][1]
        self.assertEqual(enumerate["name"], "enumerate")

        corollary = parsed_tokens[1]
        self.assertEqual(corollary["name"], "corollary")
        self.assertEqual(corollary["label"], "COL")

        # check equation is nested inside corollary
        equation = corollary['content'][0]
        self.assertEqual(equation["content"], r"\E \left|\sum_{j=1}^n \g(j)\right|^2 \leq C^2")
        self.assertEqual(equation["label"], "nax")

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
        self.assertEqual(equation["label"], "jock")

        # check begin{split} is nested inside equation
        split = equation['content']
        self.assertEqual(split.startswith(r"\begin{split}"), True)
        self.assertEqual(split.endswith(r"\end{split}"), True)

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

if __name__ == '__main__':
    unittest.main()