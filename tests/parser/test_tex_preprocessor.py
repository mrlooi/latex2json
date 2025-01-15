import pytest
import os
from latex2json.parser.tex_preprocessor import LatexPreprocessor


@pytest.fixture
def preprocessor():
    return LatexPreprocessor()


dir_path = os.path.dirname(os.path.abspath(__file__))
sample_path = os.path.join(dir_path, "samples")


def test_newcommand_processing(preprocessor):
    text = r"""
    \newcommand{\test}{TEST}
    \test
    """
    processed, tokens = preprocessor.preprocess(text)
    assert "TEST" in processed
    assert len(tokens) == 1
    assert tokens[0]["type"] == "newcommand"
    assert tokens[0]["name"] == "test"


def test_def_processing(preprocessor):
    text = r"""
    \def\bea{\begin{eqnarray}}
    \bea
    """
    processed, tokens = preprocessor.preprocess(text)
    assert r"\begin{eqnarray}" in processed
    assert len(tokens) == 1
    assert tokens[0]["type"] == "def"
    assert tokens[0]["name"] == "bea"


def test_newif_processing(preprocessor):
    text = r"""
    \newif\iftest
    \iftest
        This should appear
    \else
        This should not appear
    \fi
    """
    processed, tokens = preprocessor.preprocess(text)
    assert "This should appear" in processed
    assert "This should not appear" not in processed
    assert len(tokens) == 1
    assert tokens[0]["type"] == "newif"
    assert tokens[0]["name"] == "test"


def test_usepackage_processing(preprocessor):
    # Create a test directory path
    text = r"\usepackage{package1}"
    processed, tokens = preprocessor.preprocess(text, file_dir=sample_path)
    assert processed.strip() == ""
    assert len(tokens) == 1
    assert tokens[0]["type"] == "newcommand"
    assert tokens[0]["name"] == "foo"


def test_documentclass_processing(preprocessor):
    text = r"""
    \documentclass{basecls}
    \somecmd
    """
    processed, tokens = preprocessor.preprocess(text, file_dir=sample_path)
    assert processed.strip() == "Some command"
    assert len(tokens) == 1

    assert tokens[0]["type"] == "newcommand"
    assert tokens[0]["name"] == "somecmd"


def test_recursive_command_warning(preprocessor, caplog):
    text = r"""
    \newcommand{\recursive}{\recursive}
    """
    processed, tokens = preprocessor.preprocess(text)
    assert "Potential recursion detected" in caplog.text


def test_multiple_commands(preprocessor):
    text = r"""
    \newcommand{\first}{FIRST}
    \newcommand{\second}{SECOND}
    \first \second
    """
    processed, tokens = preprocessor.preprocess(text)
    assert "FIRST SECOND" in processed
    assert len(tokens) == 2


def test_command_with_arguments(preprocessor):
    text = r"""
    \newcommand{\greet}[1]{Hello #1}
    \greet{World}
    """
    processed, tokens = preprocessor.preprocess(text)
    assert "Hello World" in processed
    assert len(tokens) == 1


def test_clear_preprocessor(preprocessor):
    text = r"\newcommand{\test}{TEST}"
    preprocessor.preprocess(text)

    # Clear the preprocessor
    preprocessor.clear()

    # Check if the command is cleared
    text2 = r"\test"
    processed, tokens = preprocessor.preprocess(text2)
    assert r"\test" in processed  # Command should not be expanded after clear


def test_nested_commands(preprocessor):
    text = r"""
    \newcommand{\inner}{INNER}
    \newcommand{\outer}{\inner TEST}
    \outer
    """
    processed, tokens = preprocessor.preprocess(text)
    assert "INNER TEST" in processed
    assert len(tokens) == 2
