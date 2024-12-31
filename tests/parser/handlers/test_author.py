import pytest
from src.parser.handlers.author import AuthorHandler


def test_author_handler():
    item = AuthorHandler()

    text = r"""
\author{
  \AND
  Ashish Vaswani\thanks{Equal contribution.} \\
  Google Brain\\
  \texttt{avaswani@google.com}\\
  \And
  Noam Shazeer\footnotemark[1]\\
  Google Brain\\
  noam@google.com\\
}

after authors
    """.strip()

    authors, end_pos = item.handle(text)

    assert authors["type"] == "author"
    authors_list = authors["content"]
    assert len(authors_list) == 2
    assert authors_list[0].startswith("Ashish Vaswani")
    assert "{avaswani@google.com}" in authors_list[0]
    assert authors_list[1].startswith("Noam Shazeer")
    assert "noam@google.com" in authors_list[1]

    assert text[end_pos:].strip() == "after authors"
