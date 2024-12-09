from src.handlers.diacritics import DiacriticsHandler, convert_tex_diacritics


def test_diacritics():
    # Test vector accent with different formats
    assert convert_tex_diacritics(r"\vec {x}") == "x⃗"
    assert convert_tex_diacritics(r"\vec x") == "x⃗"
    assert convert_tex_diacritics(r"\vec3") == "3⃗"

    # Test multiple vector accents in one string
    assert convert_tex_diacritics(r"\vec{x}\vec y\vec3") == "x⃗y⃗3⃗"

    # Test with numbers and other characters
    assert convert_tex_diacritics(r"\vec333") == "3⃗33"
    assert convert_tex_diacritics(r"\vec{333}") == "3⃗33"

    # Test with ^~=`'"
    assert convert_tex_diacritics(r"\^{abb}") == "âbb"
    assert convert_tex_diacritics(r"\~a") == "ã"
    assert convert_tex_diacritics(r"\=a") == "ā"
    assert convert_tex_diacritics(r"\'a") == "á"
    assert convert_tex_diacritics(r"\`{abb}") == "àbb"
    assert convert_tex_diacritics(r"\"a") == "ä"

    # Test basic accents
    assert convert_tex_diacritics(r"\'a") == "á"
    assert convert_tex_diacritics(r"\`a") == "à"
    assert convert_tex_diacritics(r"\"a") == "ä"
    assert convert_tex_diacritics(r"\^a") == "â"
    assert convert_tex_diacritics(r"\~a") == "ã"
    assert convert_tex_diacritics(r"\=a") == "ā"

    # Test special letters
    assert convert_tex_diacritics(r"\c{c}") == "ç"
    assert convert_tex_diacritics(r"\v{s}") == "š"
    assert convert_tex_diacritics(r"\H{o}") == "ő"
    assert convert_tex_diacritics(r"\k{a}") == "ą"
    assert convert_tex_diacritics(r"\b{a}") == "a̱"
    assert convert_tex_diacritics(r"\.{a}") == "ȧ"
    assert convert_tex_diacritics(r"\d{a}") == "ạ"
    assert convert_tex_diacritics(r"\r{a}") == "å"
    assert convert_tex_diacritics(r"\u{a}") == "ă"

    # Test extended commands
    assert convert_tex_diacritics(r"\dot{x}") == "ẋ"
    assert convert_tex_diacritics(r"\hat{x}") == "x̂"
    assert convert_tex_diacritics(r"\check{xeee}") == "x̌eee"
    assert convert_tex_diacritics(r"\breve{x}") == "x̆"
    assert convert_tex_diacritics(r"\acute{x}fff") == "x́fff"
    assert convert_tex_diacritics(r"\grave{x}") == "x̀"
    assert convert_tex_diacritics(r"\tilde{x}") == "x̃"
    assert convert_tex_diacritics(r"\bar{x}") == "x̅"
    assert convert_tex_diacritics(r"\ddot{x}") == "ẍ"

    # Test special
    assert convert_tex_diacritics(r"\not{=}") == "≠"

    # Test combinations and spacing variants
    assert convert_tex_diacritics(r"\.{i}") == "i̇"
    assert convert_tex_diacritics(r"\. i") == "i̇"

    # # Test with \i and \j
    # assert convert_tex_diacritics(r"\'\i3") == "í3"
    # assert convert_tex_diacritics(r"\'\j{SSS}") == "j́{SSS}"


def test_diacritics_handler():
    handler = DiacriticsHandler()

    text = r"\'a posttext"
    assert handler.can_handle(text)
    token, pos = handler.handle(text)
    assert token["content"] == "á"
    assert text[pos:] == " posttext"

    # Test with braces
    text = r"\vec{xyz} posttext"
    assert handler.can_handle(text)
    token, pos = handler.handle(text)
    assert token["content"] == "x⃗yz"
    assert text[pos:] == " posttext"

    # Test with multiple diacritics in sequence
    text = r"\vec{x}\acute{y}\hat{z} posttext"
    assert handler.can_handle(text)
    token, pos = handler.handle(text)
    assert token["content"] == "x⃗"
    assert text[pos:] == r"\acute{y}\hat{z} posttext"

    # Test with special characters
    text = r"\c{c}\k{a}\H{o} posttext"
    assert handler.can_handle(text)
    token, pos = handler.handle(text)
    assert token["content"] == "ç"
    assert text[pos:] == r"\k{a}\H{o} posttext"

    # # standalone i j
    # text = r"\'\i xxx"
    # assert handler.can_handle(text)
    # token, pos = handler.handle(text)
    # assert token["content"] == "í"
    # assert text[pos:] == " xxx"

    # Test invalid input
    text = r"\invalid{x} posttext"
    assert not handler.can_handle(text)
