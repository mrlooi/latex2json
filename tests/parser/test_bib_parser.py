import pytest
from latex2json.parser.bib_parser import BibParser
import os

dir_path = os.path.dirname(os.path.abspath(__file__))


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


def test_bibitem_parsing():
    test_bib = r"""
\begin{thebibliography}{1}
\bibitem[Smith et al.]{smith2020}
Smith, John and Jones, Bob.
\newblock Some interesting paper.
\newblock Journal of Testing, 2020.

\bibitem{brown2021}
Brown, Alice.
\newblock Another paper title.
\end{thebibliography}
"""
    parser = BibParser()
    entries = parser.parse(test_bib)

    assert len(entries) == 2
    assert entries[0].citation_key == "smith2020"
    assert entries[0].title == "Smith et al."
    assert "Some interesting paper" in entries[0].content
    assert entries[0].entry_type == "bibitem"

    assert entries[1].citation_key == "brown2021"
    assert entries[1].title is None
    assert "Another paper title" in entries[1].content


def test_standalone_bibitem():
    test_bib = r"""
\bibitem{key1} First reference
\bibitem[Title]{key2} Second reference
"""
    parser = BibParser()
    entries = parser.parse(test_bib)

    assert len(entries) == 2
    assert entries[0].citation_key == "key1"
    assert entries[0].title is None
    assert entries[0].content == "First reference"

    assert entries[1].citation_key == "key2"
    assert entries[1].title == "Title"
    assert entries[1].content == "Second reference"


def test_mixed_content():
    test_bib = """
@article{ref1,
    title={Article Title},
    author={Author, Some},
    year={2020}
}

\\bibitem{ref2} Some reference
"""
    parser = BibParser()
    entries = parser.parse(test_bib)

    assert len(entries) == 1  # Should only parse BibTeX since it starts with @
    assert entries[0].entry_type == "article"
    assert entries[0].citation_key == "ref1"


def test_empty_input():
    parser = BibParser()
    entries = parser.parse("")
    assert len(entries) == 0

    entries = parser.parse("   \n   ")
    assert len(entries) == 0


def test_invalid_bibtex():
    test_bib = """
@article{incomplete
    title={Test}
"""
    parser = BibParser()
    entries = parser.parse(test_bib)
    assert len(entries) == 0


def test_bibtex_with_quotes():
    test_bib = """
@article{test,
    title="Quoted Title",
    author={Author Name},
    year="2020"
}
"""
    parser = BibParser()
    entries = parser.parse(test_bib)

    assert len(entries) == 1
    assert entries[0].fields["title"] == "Quoted Title"
    assert entries[0].fields["year"] == "2020"


def test_bibitem_with_multiple_newblocks():
    test_bib = r"""
\bibitem{key}
First block
\newblock Second block
\newblock Third block
"""
    parser = BibParser()
    entries = parser.parse(test_bib)

    assert len(entries) == 1
    c = entries[0].content
    assert "First block" in c
    assert "Second block" in c
    assert "Third block" in c


def test_parse_file_bibtex():
    parser = BibParser()
    entries = parser.parse_file(os.path.join(dir_path, "samples/bibtex.bib"))

    assert len(entries) == 2

    # Check first entry
    assert entries[0].entry_type == "incollection"
    assert entries[0].citation_key == "Bengio+chapter2007"
    assert entries[0].fields["title"] == "Scaling Learning Algorithms Towards {AI}"
    assert entries[0].fields["author"] == "Bengio, Yoshua and LeCun, Yann"
    assert entries[0].fields["year"] == "2007"
    assert entries[0].fields["booktitle"] == "Large Scale Kernel Machines"

    # Check second entry
    assert entries[1].entry_type == "article"
    assert entries[1].citation_key == "Hinton06"
    assert (
        entries[1].fields["title"] == "A Fast Learning Algorithm for Deep Belief Nets"
    )
    assert entries[1].fields["journal"] == "Neural Computation"
    assert entries[1].fields["volume"] == "18"
    assert entries[1].fields["year"] == "2006"


def test_parse_file_bbl():
    parser = BibParser()
    entries = parser.parse_file(os.path.join(dir_path, "samples/bib.bbl"))

    assert len(entries) == 2

    # Check first entry
    assert entries[0].entry_type == "bibitem"
    assert entries[0].citation_key == "chess365"
    assert "Online chess games database" in entries[0].content
    assert "365chess" in entries[0].content

    # Check second entry
    assert entries[1].entry_type == "bibitem"
    assert entries[1].citation_key == "ssss"
    assert "SSSS" in entries[1].content
