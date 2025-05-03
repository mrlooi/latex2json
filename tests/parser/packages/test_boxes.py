import pytest
from latex2json.parser.packages.boxes import BoxHandler


@pytest.fixture
def handler():
    return BoxHandler()


def test_can_handle_valid(handler):
    assert handler.can_handle(r"\makebox{text}")
    assert handler.can_handle(r"\fbox{text}")
    assert handler.can_handle(r"\parbox{5cm}{text}")
    assert handler.can_handle(r"\hbox to 3in{text}")
    assert not handler.can_handle(r"\unknown{text}")
    assert not handler.can_handle(r"\textbf{text}")


def test_box_commands(handler):
    # Test that box commands only return their text content
    test_cases = [
        (r"\makebox{Simple text}", "Simple text"),
        (r"\framebox{Simple text}", "Simple text"),
        (r"\raisebox{2pt}{Raised text}", "Raised text"),
        (r"\raisebox{2pt}[1pt][2pt]{Raised text}", "Raised text"),
        (r"\makebox[3cm]{Fixed width}", "Fixed width"),
        (r"\framebox[3cm][l]{Left in frame}", "Left in frame"),
        (r"\parbox{5cm}{Simple parbox text}", "Simple parbox text"),
        (r"\parbox[t][3cm][s]{5cm}{Stretched vertically}", "Stretched vertically"),
        (r"\fbox{Framed text}", "Framed text"),
        (r"\colorbox{yellow}{Colored box}", "Colored box"),
        (
            r"\parbox[c][3cm]{5cm}{Center aligned with fixed height}",
            "Center aligned with fixed height",
        ),
        (
            r"""\mbox{
            All
            One line ajajaja
            }""",
            "All One line ajajaja",
        ),
        (r"\hbox to 3in{Some text}", "Some text"),
        (r"\pbox{3cm}{Some text}", "Some text"),
        (r"\adjustbox{max width=\textwidth}{Some text}", "Some text"),
        (r"\rotatebox{90}{Some text}", "Some text"),
    ]

    for command, expected_text in test_cases:
        token, pos = handler.handle(command)
        assert token and token["content"].strip() == expected_text
        assert pos > 0  # Should advance past the command


def test_box_with_surrounding_text(handler):
    text = r"""
    \parbox[c][3cm]{5cm}{Center aligned with fixed height} STUFF AFTER
    """.strip()
    token, pos = handler.handle(text)
    assert token and token["content"].strip() == "Center aligned with fixed height"
    assert text[pos:] == " STUFF AFTER"


def test_fancyhead(handler):
    test_cases = [
        (r"\fancyhead[R]{Simple text}", "Simple text"),
        (r"\fancyheadoffset{Simple text}", "Simple text"),
        (r"\rhead{Simple text}", "Simple text"),
        (r"\lhead{Raised text}", "Raised text"),
    ]

    for command, expected_text in test_cases:
        token, pos = handler.handle(command)
        assert token and token["content"].strip() == expected_text
        assert pos > 0  # Should advance past the command


# SAVEBOX/USEBOX STUFF
def test_newsavebox_and_usebox(handler):
    # Test newsavebox registration
    command1 = r"\newsavebox{\mybox} POST"
    result1, pos1 = handler.handle(command1)
    assert command1[pos1:] == " POST"
    assert result1 is None  # newsavebox just registers, returns nothing
    assert "mybox" in handler.saved_boxes
    assert handler.saved_boxes["mybox"] is None

    # Test sbox storing content
    command2 = r"\sbox\mybox{Stored content} POST"
    result2, pos2 = handler.handle(command2)
    assert command2[pos2:] == " POST"
    assert result2 is None  # sbox stores but returns nothing
    assert handler.saved_boxes["mybox"] is not None
    assert handler.saved_boxes["mybox"]["content"] == "Stored content"

    # Test usebox retrieving content
    command3 = r"\usebox\mybox POST"
    result3, pos3 = handler.handle(command3)
    assert command3[pos3:] == " POST"
    assert result3 is not None
    assert result3["content"] == "Stored content"


def test_savebox_variations(handler):
    handler.clear()
    # Test savebox (alternative to sbox)
    command1 = r"\savebox\mybox{Alternative storage} POST"
    result1, pos1 = handler.handle(command1)
    assert command1[pos1:] == " POST"
    assert result1 is None
    assert handler.saved_boxes["mybox"] is not None
    assert handler.saved_boxes["mybox"]["content"] == "Alternative storage"

    # Test using undefined box
    command2 = r"\usebox\undefinedbox POST"
    result2, pos2 = handler.handle(command2)
    assert command2[pos2:] == " POST"
    assert result2 is None  # Should return None for undefined boxes


def test_box_content_processing(handler):
    handler.clear()

    # Test that content processing is applied to saved box content
    def mock_processor(content):
        return {"type": "text", "content": f"PROCESSED_{content}"}

    handler.process_content_fn = mock_processor

    # Store content with processing
    command1 = r"\sbox\processedbox{Test content} POST"
    result1, pos1 = handler.handle(command1)
    assert command1[pos1:] == " POST"
    assert result1 is None

    # Verify processed content is stored and retrieved
    command2 = r"\usebox\processedbox POST"
    result2, pos2 = handler.handle(command2)
    assert command2[pos2:] == " POST"
    assert result2 is not None
    assert result2["content"] == "PROCESSED_Test content"


def test_setbox(handler):
    command = r"\setbox0=\hbox{Hello} POST"
    result, pos = handler.handle(command)
    assert command[pos:] == " POST"
    assert result is None
    assert handler.numbered_boxes[0]["content"] == "Hello"

    command = r"\setbox1=\makebox[3cm]{World} POST"
    result, pos = handler.handle(command)
    assert command[pos:] == " POST"
    assert result is None
    assert handler.numbered_boxes[1]["content"] == "World"
