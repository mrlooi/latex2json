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

    def test_parse_equations(self):
        equations = [token for token in self.parsed_tokens if token["type"] == "equation"]
        self.assertEqual(len(equations), 8)
        # inline equations = 7
        inline_equations = [token for token in equations if token["display"] == "inline"]
        self.assertEqual(len(inline_equations), 7)

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
        labels = [token for token in self.parsed_tokens if token["type"] == "label"]
        self.assertEqual(len(labels), 1)
        self.assertEqual(labels[0]['content'], 'sec:reg')

if __name__ == '__main__':
    unittest.main()