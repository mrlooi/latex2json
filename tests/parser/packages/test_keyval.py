import pytest
from latex2json.parser.packages.keyval import KeyValHandler


def test_keyval_handler_can_handle():
    handler = KeyValHandler()

    # Should handle keyval commands
    assert handler.can_handle(r"\define@key")
    assert handler.can_handle(r"\setkeys")

    # Should not handle other commands
    assert not handler.can_handle(r"\begin{figure}")
    assert not handler.can_handle(r"\includegraphics")


def test_keyval_handler_handle_define_key():
    handler = KeyValHandler()

    # Test define_key command
    text = r"\define@key{family}{key}[default]{handler} POST"
    token, end_pos = handler.handle(text)

    assert token is None  # Since handle() is set to ignore tokens
    assert text[end_pos:] == " POST"

    # without [default]
    text = r"\define@key{family}{key}{handler} POST"
    token, end_pos = handler.handle(text)

    assert token is None  # Since handle() is set to ignore tokens
    assert text[end_pos:] == " POST"


def test_keyval_handler_handle_setkeys():
    handler = KeyValHandler()

    # Test setkeys command
    text = r"\setkeys{family}{key1=value1,key2=value2} POST"
    token, end_pos = handler.handle(text)

    assert token is None  # Since handle() is set to ignore tokens
    assert text[end_pos:] == " POST"
