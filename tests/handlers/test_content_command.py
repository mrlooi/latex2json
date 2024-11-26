import pytest
from src.handlers.content_command import ContentCommandHandler
from src.patterns import SECTION_LEVELS

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
        "level": SECTION_LEVELS['section'],
        "numbered": True
    }
    
    # Test subsection
    token, pos = handler.handle(r"\subsection*{Methods}")
    assert token == {
        "type": "section",
        "title": "Methods",
        "level": SECTION_LEVELS['subsection'],
        "numbered": False
    }
    
    # Test subsubsection
    token, pos = handler.handle(r"\subsubsection{Results}")
    assert token == {
        "type": "section",
        "title": "Results",
        "level": SECTION_LEVELS['subsubsection'],
        "numbered": True
    }

def test_handle_captions(handler):
    # Test basic caption
    token, pos = handler.handle(r"\caption{A simple caption}")
    assert token == {
        "type": "caption",
        "content": "A simple caption"
    }
    
    # Test captionof
    token, pos = handler.handle(r"\captionof{figure}{A figure caption}")
    assert token == {
        "type": "caption",
        "title": "figure",
        "content": "A figure caption"
    }

def test_handle_footnotes(handler):
    token, pos = handler.handle(r"\footnote{A footnote text}")
    assert token == {
        "type": "footnote",
        "content": "A footnote text"
    }

def test_handle_references(handler):
    # Test basic ref
    token, pos = handler.handle(r"\ref{sec:intro}")
    assert token == {
        "type": "ref",
        "content": "sec:intro"
    }

    token, pos = handler.handle(r"\cref{sec:intro, fig:fig1}")
    assert token == {
        "type": "ref",
        "content": "sec:intro, fig:fig1"
    }

    token, pos = handler.handle(r"\autoref{sec:intro}")
    assert token == {
        "type": "ref",
        "content": "sec:intro"
    }
    
    token, pos = handler.handle(r"\Autoref{sec:intro}")
    assert token is None
    
    # Test hyperref
    token, pos = handler.handle(r"\hyperref[sec:methods]{Methods section}")
    assert token == {
        "type": "ref",
        "title": "sec:methods",
        "content": "Methods section"
    }
    
    # Test href
    token, pos = handler.handle(r"\href{http://example.com}{Link text}")
    assert token == {
        "type": "url",
        "content": "http://example.com",
        "title": "Link text"
    }

def test_handle_citations(handler):
    # Test basic citation
    token, pos = handler.handle(r"\cite{smith2023}")
    assert token == {
        "type": "citation",
        "content": "smith2023"
    }
    
    # Test citation with optional text
    token, pos = handler.handle(r"\cite[p. 42]{smith2023}")
    assert token == {
        "type": "citation",
        "content": "smith2023",
        "title": "p. 42"
    }

def test_handle_graphics(handler):
    token, pos = handler.handle(r"\includegraphics{image.png}")
    assert token == {
        "type": "includegraphics",
        "content": "image.png"
    }

def test_handle_urls(handler):
    token, pos = handler.handle(r"\url{http://example.com}")
    assert token == {
        "type": "url",
        "content": "http://example.com"
    }

def test_handle_with_expand_fn():
    def mock_expand(content: str) -> str:
        return content.replace('old', 'new')
    
    handler = ContentCommandHandler(process_content_fn=mock_expand)
    token, pos = handler.handle(r"\paragraph*{old title}")
    assert token == {
        "type": "section",
        "title": "new title",
        "level": SECTION_LEVELS['paragraph'],
        "numbered": False
    }

def test_handle_nested_content():
    content = r"\section{Title with \textbf{bold} {hello} text}"
    def mock_expand(content: str) -> str:
        return content.replace(r'\textbf{bold}', 'bold')
    
    handler = ContentCommandHandler(process_content_fn=mock_expand)
    token, pos = handler.handle(content)
    assert token == {
        "type": "section",
        "title": "Title with bold {hello} text",
        "level": SECTION_LEVELS['section'],
        "numbered": True
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
        "level": SECTION_LEVELS['section'],
        "numbered": False
    }

if __name__ == "__main__":
    pytest.main([__file__])
