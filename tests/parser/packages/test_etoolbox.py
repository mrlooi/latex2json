import pytest
from latex2json.parser.packages.etoolbox import EtoolboxHandler


def test_etoolbox_handler_can_handle():
    handler = EtoolboxHandler()

    # Should handle etoolbox boolean commands
    assert handler.can_handle(r"\ifbool{somebool}")
    assert handler.can_handle(r"\notbool{somebool}")
    assert handler.can_handle(r"\providebool{somebool}")
    assert handler.can_handle(r"\setbool{somebool}")
    assert handler.can_handle(r"\booltrue{somebool}")
    assert handler.can_handle(r"\boolfalse{somebool}")
    assert handler.can_handle(r"\newbool{somebool}")

    # Should not handle other commands
    assert not handler.can_handle(r"\begin{figure}")
    assert not handler.can_handle(r"\includegraphics")


def test_etoolbox_handler_handle_ifbool():
    handler = EtoolboxHandler()

    # Test \ifbool command
    text = r"\ifbool{mybool}{true content}{false content} POST"
    token, end_pos = handler.handle(text)

    assert token is not None
    assert token["type"] == "bool_conditional"
    assert token["name"] == "mybool"
    assert token["true_code"] == "true content"
    assert token["false_code"] == "false content"
    assert not token["is_not"]
    assert text[end_pos:].strip() == "POST"

    # Test \notbool command (inverted version)
    text = r"\notbool{mybool}{false content}{true content} POST"
    token, end_pos = handler.handle(text)

    assert token is not None
    assert token["type"] == "bool_conditional"
    assert token["name"] == "mybool"
    assert token["true_code"] == "true content"
    assert token["false_code"] == "false content"
    assert token["is_not"]
    assert text[end_pos:].strip() == "POST"


def test_etoolbox_handler_handle_providebool():
    handler = EtoolboxHandler()

    # Test \providebool command
    text = r"\providebool{newbool} POST"
    token, end_pos = handler.handle(text)

    assert token is not None
    assert token["type"] == "bool_definition"
    assert token["name"] == "newbool"
    assert text[end_pos:].strip() == "POST"

    # Verify bool was added to handler's definitions
    assert "newbool" in handler.bool_definitions
    assert handler.bool_definitions["newbool"] is False


def test_etoolbox_handler_handle_setbool():
    handler = EtoolboxHandler()

    # First define the boolean
    handler.handle(r"\providebool{mybool}")

    # Test \setbool command with true
    text = r"\setbool{mybool}{true} POST"
    token, end_pos = handler.handle(text)

    assert token is not None
    assert token["type"] == "bool_set"
    assert token["name"] == "mybool"
    assert token["value"] is True
    assert text[end_pos:].strip() == "POST"

    # Verify bool value was updated
    assert handler.bool_definitions["mybool"] is True

    # Test with false
    text = r"\setbool{mybool}{false} POST"
    token, end_pos = handler.handle(text)

    assert token is not None
    assert token["type"] == "bool_set"
    assert token["name"] == "mybool"
    assert token["value"] is False
    assert text[end_pos:].strip() == "POST"


def test_etoolbox_handler_handle_bool_true_false():
    handler = EtoolboxHandler()

    # First define the boolean
    handler.handle(r"\providebool{mybool}")

    # Test \booltrue command
    text = r"\booltrue{mybool} POST"
    token, end_pos = handler.handle(text)

    assert token is not None
    assert token["type"] == "bool_set"
    assert token["name"] == "mybool"
    assert token["value"] is True
    assert text[end_pos:].strip() == "POST"

    # Verify bool value was updated
    assert handler.bool_definitions["mybool"] is True

    # Test \boolfalse command
    text = r"\boolfalse{mybool} POST"
    token, end_pos = handler.handle(text)

    assert token is not None
    assert token["type"] == "bool_set"
    assert token["name"] == "mybool"
    assert token["value"] is False
    assert text[end_pos:].strip() == "POST"

    # Verify bool value was updated
    assert handler.bool_definitions["mybool"] is False


def test_etoolbox_handler_handle_newbool():
    handler = EtoolboxHandler()

    # Test \newbool command
    text = r"\newbool{newbool} POST"
    token, end_pos = handler.handle(text)

    assert token is not None
    assert token["type"] == "bool_definition"
    assert token["name"] == "newbool"
    assert token["definition_type"] == "newbool"
    assert text[end_pos:].strip() == "POST"

    # Verify bool was added to handler's definitions
    assert "newbool" in handler.bool_definitions
    assert handler.bool_definitions["newbool"] is False

    # Test redefining existing bool with newbool (should work)
    text = r"\newbool{newbool} POST"
    token, end_pos = handler.handle(text)
    assert token is not None
    assert token["type"] == "bool_definition"
    assert token["definition_type"] == "newbool"


def test_etoolbox_handler_handle_providebool_vs_newbool():
    handler = EtoolboxHandler()

    # First define with newbool
    handler.handle(r"\newbool{mybool}")

    # Try to provide existing bool
    text = r"\providebool{mybool} POST"
    token, end_pos = handler.handle(text)

    assert token is not None
    assert token["type"] == "bool_definition"
    assert token["name"] == "mybool"
    assert token["definition_type"] == "providebool"
    # Verify bool wasn't redefined since it already exists
    assert "mybool" in handler.bool_definitions
