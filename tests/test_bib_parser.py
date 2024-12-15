import pytest
from src.bib_parser import BibParser


def test_bib_parser():
    test_bib = """
@article{brown2020-gpt3,
  title={Language models are few-shot learners},
  author={Brown, Tom B and Mann, Benjamin},
  journal={arXiv},
  year={2020}
}

@inproceedings{vaswani2017,
title = {Attention is All you Need},
author = {Vaswani, Ashish and Shazeer, Noam},
booktitle = {NIPS},
year = {2017},
}
"""
    parser = BibParser()
    entries = parser.parse(test_bib)

    assert len(entries) == 2

    # Check first entry
    assert entries[0].entry_type == "article"
    assert entries[0].citation_key == "brown2020-gpt3"
    assert entries[0].fields["title"] == "Language models are few-shot learners"
    assert entries[0].fields["author"] == "Brown, Tom B and Mann, Benjamin"
    assert entries[0].fields["year"] == "2020"

    # Check second entry
    assert entries[1].entry_type == "inproceedings"
    assert entries[1].citation_key == "vaswani2017"
    assert entries[1].fields["title"] == "Attention is All you Need"
    assert entries[1].fields["booktitle"] == "NIPS"


def test_complex_fields():
    test_bib = """
@article{test,
  title={{Complex {Nested} Braces}},
  author={Author, Some and Other, Another},
  journal={Journal with {Special} Characters},
  year={2020}
}
"""
    parser = BibParser()
    entries = parser.parse(test_bib)

    assert len(entries) == 1
    assert entries[0].fields["title"] == "{Complex {Nested} Braces}"
