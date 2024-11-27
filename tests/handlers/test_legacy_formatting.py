import pytest
from src.handlers.legacy_formatting import LegacyFormattingHandler

@pytest.fixture
def handler():
    return LegacyFormattingHandler()

def test_can_handle_valid_commands(handler):
    assert handler.can_handle(r"{\bf text}")
    assert handler.can_handle(r"{\it text}")
    assert handler.can_handle(r"{\large text}")

def test_can_handle_invalid_commands(handler):
    assert not handler.can_handle(r"{\unknown text}")
    assert not handler.can_handle(r"{text}")

def test_handle_valid_commands(handler):
    output, _ = handler.handle(r"{\bf text}")
    assert output['type'] == 'command'
    assert output['content'] == r'\textbf{text}'

    output, _ = handler.handle(r"{\it text}")
    assert output['type'] == 'command'
    assert output['content'] == r'\textit{text}'

def test_handle_nested_commands(handler):
    output, _ = handler.handle(r"{\tt text with \pow{3}}")
    assert output['type'] == 'command'
    assert 'texttt' in output['content']  # Check if the command is converted

# def test_handle_invalid_commands(handler):
#     output, _ = handler.handle(r"{\unknown text}")
#     assert output['type'] == 'text'
#     assert 'unknown' in output['content']  # Check if it returns the original text
