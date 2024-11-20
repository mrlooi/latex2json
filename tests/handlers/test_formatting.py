import pytest
from src.handlers.formatting import FormattingHandler

@pytest.fixture
def handler():
    return FormattingHandler()

def test_can_handle_formatting(handler):
    # Test formatting commands
    assert handler.can_handle(r"\usepackage{amsmath}")
    assert handler.can_handle(r"\centering")
    assert handler.can_handle(r"\raggedright")
    assert handler.can_handle(r"\noindent")
    assert handler.can_handle(r"\clearpage")
    assert handler.can_handle(r"\linebreak")
    assert handler.can_handle(r"\bigskip")
    assert not handler.can_handle("regular text")

def test_can_handle_comments(handler):
    assert handler.can_handle("% This is a comment")
    assert handler.can_handle("%Another comment")
    assert not handler.can_handle("Not a % comment")

def test_can_handle_separators(handler):
    # Test various separator commands
    assert handler.can_handle(r"\hline")
    assert handler.can_handle(r"\cline{2-4}")
    assert handler.can_handle(r"\midrule")
    assert handler.can_handle(r"\toprule")
    assert handler.can_handle(r"\bottomrule")
    assert handler.can_handle(r"\cmidrule{1-2}")
    assert handler.can_handle(r"\cmidrule[2pt]{1-2}")
    assert handler.can_handle(r"\hdashline")
    assert handler.can_handle(r"\cdashline{2-4}")
    assert handler.can_handle(r"\specialrule{.2em}{.1em}{.1em}")
    assert handler.can_handle(r"\addlinespace")
    assert handler.can_handle(r"\addlinespace[5pt]")
    assert handler.can_handle(r"\morecmidrules")

def test_handle_formatting_commands(handler):
    # Test handling of formatting commands
    token, pos = handler.handle(r"\centering Some text")
    # assert token is None
    assert pos == len(r"\centering")  # Length of "\centering"

    token, pos = handler.handle(r"\noindent Text")
    # assert token is None
    assert pos == len(r"\noindent")  # Length of "\noindent"

def test_handle_comments(handler):
    # Test handling of comments
    comment = "% This is a comment\nNext line"
    token, pos = handler.handle(comment)
    # assert token is None
    assert pos == len(comment.split('\n')[0])  # Length of comment up to \n

def test_handle_separators(handler):
    # Test handling of separator commands
    token, pos = handler.handle(r"\hline some text")
    # assert token is None
    assert pos == len(r"\hline") 

    token, pos = handler.handle(r"\cline{2-4} text")
    # assert token is None
    assert pos == len(r"\cline{2-4}")

    token, pos = handler.handle(r"\midrule[2pt] text")
    # assert token is None
    assert pos == len(r"\midrule[2pt]")

def test_handle_invalid_input(handler):
    # Test with non-command content
    token, pos = handler.handle("regular text")
    # assert token is None
    assert pos == 0

if __name__ == "__main__":
    pytest.main([__file__]) 