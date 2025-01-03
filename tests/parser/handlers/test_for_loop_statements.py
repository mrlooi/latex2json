import pytest
from latex_parser.parser.handlers.for_loop_statements import ForLoopHandler


@pytest.fixture
def handler():
    return ForLoopHandler()


def test_foreach(handler):
    content = r"""\foreach \x in {0,...,4}{
    \draw (3*\x,10)--++(0,-0.2);
    \foreach \j in {1,...,4}
        \draw[draw=blue] ({3*(\x+\j/5)},10)--++(0,-0.2);
    }

    POST FOREACH
""".strip()
    token, pos = handler.handle(content)
    assert content[pos:].strip() == "POST FOREACH"

    content = r"""
    \foreach \x [count = \xi] in {a,...,c,f,...,z}
{\node at (\xi,0) {$\x$};}

POST FOREACH
""".strip()
    token, pos = handler.handle(content)
    assert content[pos:].strip() == "POST FOREACH"


def test_forloop(handler):
    content = r"""
\forloop{i}{1}{5}{
    content with \thei
}
POST FORLOOP
""".strip()
    token, pos = handler.handle(content)
    assert content[pos:].strip() == "POST FORLOOP"


if __name__ == "__main__":
    pytest.main([__file__])
