import pytest
from src.handlers.content_command import (
    ContentCommandHandler,
    SECTION_LEVELS,
    PARAGRAPH_LEVELS,
)


@pytest.fixture
def handler():
    return ContentCommandHandler()


def test_can_handle_sections(handler):
    assert handler.can_handle(r"\section{Title}")
    assert handler.can_handle(r"\subsection{Title}")
    assert handler.can_handle(r"\chapter{Title}")
    assert not handler.can_handle("regular text")
    # assert not handler.can_handle(r"\section{") # incomplete command


def test_can_handle_other_commands(handler):
    assert handler.can_handle(r"\caption{A caption}")
    assert handler.can_handle(r"\footnote{A footnote}")
    assert handler.can_handle(r"\href{url}{text}")
    assert handler.can_handle(r"\url{http://example.com}")


def test_handle_sections(handler):
    # Test basic section
    token, pos = handler.handle(r"\section{Introduction}")
    assert token == {
        "type": "section",
        "title": "Introduction",
        "level": SECTION_LEVELS["section"],
        "numbered": True,
    }

    # Test subsection
    token, pos = handler.handle(r"\subsection*{Methods}")
    assert token == {
        "type": "section",
        "title": "Methods",
        "level": SECTION_LEVELS["subsection"],
        "numbered": False,
    }

    # Test subsubsection
    token, pos = handler.handle(r"\subsubsection{Results}")
    assert token == {
        "type": "section",
        "title": "Results",
        "level": SECTION_LEVELS["subsubsection"],
        "numbered": True,
    }


def test_handle_captions(handler):
    # Test basic caption
    token, pos = handler.handle(r"\caption{A simple caption}")
    assert token == {"type": "caption", "content": "A simple caption"}

    # Test captionof
    token, pos = handler.handle(r"\captionof{figure}{A figure caption}")
    assert token == {
        "type": "caption",
        "title": "figure",
        "content": "A figure caption",
    }


def test_handle_footnotes(handler):
    token, pos = handler.handle(r"\footnote{A footnote text}")
    assert token == {"type": "footnote", "content": "A footnote text"}

    token, pos = handler.handle(r"\footnotemark")
    assert token == {"type": "footnote", "content": "*"}

    content = r"\footnotemark[1] aaa"
    token, pos = handler.handle(content)
    assert token == {"type": "footnote", "content": "1"}
    assert content[pos:] == " aaa"

    content = r"\footnotetext{A footnote text}"
    token, pos = handler.handle(content)
    assert token == {"type": "footnote", "content": "A footnote text"}
    assert content[pos:] == ""

    content = r"\footnotetext[1]{A footnote text} Post"
    token, pos = handler.handle(content)
    assert token == {"type": "footnote", "content": "A footnote text"}
    assert content[pos:] == " Post"


def test_handle_references(handler):
    # Test basic ref
    token, pos = handler.handle(r"\ref{sec:intro}")
    assert token == {"type": "ref", "content": "sec:intro"}

    token, pos = handler.handle(r"\cref{sec:intro, fig:fig1}")
    assert token == {"type": "ref", "content": "sec:intro, fig:fig1"}

    token, pos = handler.handle(r"\autoref{sec:intro}")
    assert token == {"type": "ref", "content": "sec:intro"}

    token, pos = handler.handle(r"\eqref{EQ1}")
    assert token == {"type": "ref", "content": "EQ1"}

    token, pos = handler.handle(r"\pageref*{EQ1}")
    assert token == {"type": "ref", "content": "EQ1"}

    token, pos = handler.handle(r"\autorefe{sec:intro}")
    assert token is None

    # Test hyperref
    token, pos = handler.handle(r"\hyperref[sec:methods]{Methods section}")
    assert token == {
        "type": "ref",
        "title": "sec:methods",
        "content": "Methods section",
    }

    # Test href
    token, pos = handler.handle(r"\href{http://example.com}{Link text}")
    assert token == {
        "type": "url",
        "content": "http://example.com",
        "title": "Link text",
    }


def test_handle_citations(handler):
    # Test basic citation
    token, pos = handler.handle(r"\cite{smith2023}")
    assert token == {"type": "citation", "content": "smith2023"}

    # Test citation with optional text
    token, pos = handler.handle(r"\cite[p. 42]{smith2023}")
    assert token == {"type": "citation", "content": "smith2023", "title": "p. 42"}


def test_handle_graphics(handler):
    token, pos = handler.handle(r"\includegraphics{image.png}")
    assert token == {"type": "includegraphics", "content": "image.png"}

    # with page number
    token, pos = handler.handle(r"\includegraphics[page=2]{mypdf.pdf}")
    assert token == {"type": "includegraphics", "content": "mypdf.pdf", "page": 2}


def test_handle_includepdf(handler):
    token, pos = handler.handle(r"\includepdf[pages={1-3}]{mypdf.pdf}")
    assert token == {"type": "includepdf", "content": "mypdf.pdf", "pages": "1-3"}

    token, pos = handler.handle(r"\includepdf[pages=2]{mypdf.pdf}")
    assert token == {"type": "includepdf", "content": "mypdf.pdf", "pages": "2"}

    token, pos = handler.handle(r"\includepdf[pages={1,3,5-7}]{mypdf.pdf}")
    assert token == {"type": "includepdf", "content": "mypdf.pdf", "pages": "1,3,5-7"}

    token, pos = handler.handle(r"\includepdf{mypdf.pdf}")
    assert token == {"type": "includepdf", "content": "mypdf.pdf"}


def test_handle_urls(handler):
    token, pos = handler.handle(r"\url{http://example.com}")
    assert token == {"type": "url", "content": "http://example.com"}


def test_handle_with_expand_fn():
    def mock_expand(content: str) -> str:
        return content.replace("old", "new")

    handler = ContentCommandHandler(process_content_fn=mock_expand)
    token, pos = handler.handle(r"\paragraph{old title}")
    assert token == {
        "type": "paragraph",
        "title": "new title",
        "level": PARAGRAPH_LEVELS["paragraph"],
    }

    token, pos = handler.handle(r"\subparagraph{old title}")
    assert token == {
        "type": "paragraph",
        "title": "new title",
        "level": PARAGRAPH_LEVELS["subparagraph"],
    }


def test_handle_nested_content():
    content = r"\section{Title with \textbf{bold} {hello} text}"

    def mock_expand(content: str) -> str:
        return content.replace(r"\textbf{bold}", "bold")

    handler = ContentCommandHandler(process_content_fn=mock_expand)
    token, pos = handler.handle(content)
    assert token == {
        "type": "section",
        "title": "Title with bold {hello} text",
        "level": SECTION_LEVELS["section"],
        "numbered": True,
    }


def test_handle_invalid_input(handler):
    # Test with non-command content
    token, pos = handler.handle("regular text")
    assert token is None
    assert pos == 0

    # Test with malformed command
    token, pos = handler.handle(r"\section{Incomplete")
    assert token is None
    assert pos > 0  # Should return position after \section


def test_handle_empty_content(handler):
    # Test empty section
    token, pos = handler.handle(r"\section*{}")
    assert token == {
        "type": "section",
        "title": "",
        "level": SECTION_LEVELS["section"],
        "numbered": False,
    }


def test_other(handler):
    text = r"\abstract{ THIS IS MY ABSTRACT } After Intro"
    token, pos = handler.handle(text)
    assert token == {"type": "abstract", "content": "THIS IS MY ABSTRACT"}
    assert text[pos:] == " After Intro"

    text = r"\pdfbookmark[1]{My bookmark}{my:bookmark} POST BOOKMARK"
    token, pos = handler.handle(text)
    assert token == {
        "type": "ref",
        "title": "My bookmark",
        "content": "my:bookmark",
    }
    assert text[pos:] == " POST BOOKMARK"

    text = r"\bookmark[1]{My bookmark} post"
    token, pos = handler.handle(text)
    assert token == {
        "type": "ref",
        "content": "My bookmark",
    }
    assert text[pos:] == " post"

    # appendix
    text = r"\appendix POST APPENDIX"
    token, pos = handler.handle(text)
    assert token == {"type": "appendix"}
    assert text[pos:] == " POST APPENDIX"

    # include/input
    text = r"\input{file.tex} POST INPUT"
    token, pos = handler.handle(text)
    assert token == {"type": "input_file", "content": "file.tex"}
    assert text[pos:] == " POST INPUT"

    text = text.replace(r"\input", r"\include")
    token, pos = handler.handle(text)
    assert token == {"type": "input_file", "content": "file.tex"}
    assert text[pos:] == " POST INPUT"

    # bibliography file
    text = r"\bibliography{file.bib} POST BIBLIOGRAPHY"
    token, pos = handler.handle(text)
    assert token == {"type": "bibliography_file", "content": "file.bib"}
    assert text[pos:] == " POST BIBLIOGRAPHY"


if __name__ == "__main__":
    pytest.main([__file__])
