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


if __name__ == '__main__':
    unittest.main()