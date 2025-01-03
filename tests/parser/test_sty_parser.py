import pytest
from latex_parser.parser.sty_parser import LatexStyParser
import os


def test_sty_parser():
    parser = LatexStyParser()

    # parse file way
    dir_path = os.path.dirname(os.path.abspath(__file__))
    tokens = parser.parse_file(os.path.join(dir_path, "samples/package1.sty"))
    assert len(tokens) == 1

    assert tokens[0]["type"] == "newcommand"
    assert tokens[0]["name"] == "foo"

    parser.clear()

    # regular parse way
    with open(os.path.join(dir_path, "samples/package1.sty"), "r") as f:
        content = f.read()
    tokens = parser.parse(content)
    assert len(tokens) == 1

    assert tokens[0]["type"] == "newcommand"
    assert tokens[0]["name"] == "foo"

    parser.clear()

    # package2
    def check_tokens(tokens):
        assert len(tokens) == 2
        assert tokens[0]["type"] == "newcommand"
        assert tokens[0]["name"] == "bar"

        assert tokens[1]["type"] == "newcommand"
        assert tokens[1]["name"] == "foo"

    tokens = parser.parse_file(os.path.join(dir_path, "samples/package2.sty"))
    check_tokens(tokens)

    parser.clear()

    # abs paths
    text = r"""
    \usepackage{%s, %s}
""" % (
        os.path.join(dir_path, "samples/package2.sty"),
        os.path.join(dir_path, "samples/package1.sty"),
    )
    tokens = parser.parse(text)
    check_tokens(tokens)

    parser.clear()
