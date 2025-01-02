from typing import Dict, Optional, Tuple
import unicodedata
import re

from src.parser.handlers.base import TokenHandler
from src.tex_utils import extract_nested_content, substitute_patterns

# Unicode combining characters for various LaTeX accent commands
ACCENT_MAP = {
    # Basic accents
    "'": "\N{COMBINING ACUTE ACCENT}",
    "`": "\N{COMBINING GRAVE ACCENT}",
    '"': "\N{COMBINING DIAERESIS}",
    "^": "\N{COMBINING CIRCUMFLEX ACCENT}",
    "~": "\N{COMBINING TILDE}",
    "=": "\N{COMBINING MACRON}",
    # Special letters
    "c": "\N{COMBINING CEDILLA}",
    "H": "\N{COMBINING DOUBLE ACUTE ACCENT}",
    "k": "\N{COMBINING OGONEK}",
    "b": "\N{COMBINING MACRON BELOW}",
    ".": "\N{COMBINING DOT ABOVE}",
    "d": "\N{COMBINING DOT BELOW}",
    "r": "\N{COMBINING RING ABOVE}",
    "u": "\N{COMBINING BREVE}",
    "v": "\N{COMBINING CARON}",
    # Extended commands
    "vec": "\N{COMBINING RIGHT ARROW ABOVE}",
    "dot": "\N{COMBINING DOT ABOVE}",
    "hat": "\N{COMBINING CIRCUMFLEX ACCENT}",
    "check": "\N{COMBINING CARON}",
    "breve": "\N{COMBINING BREVE}",
    "acute": "\N{COMBINING ACUTE ACCENT}",
    "grave": "\N{COMBINING GRAVE ACCENT}",
    "tilde": "\N{COMBINING TILDE}",
    "bar": "\N{COMBINING OVERLINE}",
    "ddot": "\N{COMBINING DIAERESIS}",
    # Special
    "not": "\N{COMBINING LONG SOLIDUS OVERLAY}",
}


def generate_accent_patterns():
    """
    Generate regex patterns for LaTeX accent commands and special characters.
    Returns a list of (pattern, accent_key) tuples.
    """
    patterns = {}

    for key in ACCENT_MAP:
        if key[0].isalpha():
            patterns[key] = re.compile(
                r"\\" + key + r"((?:\s*\{)|(\s+\S)|(?![a-zA-Z@])\S)"
            )
        else:
            patterns[key] = re.compile(r"\\" + re.escape(key) + r"\s*(\{|\S)")

    return patterns


ACCENT_PATTERNS = generate_accent_patterns()


def apply_accent(base_char: str, accent: str) -> str:
    """
    Apply a LaTeX accent to a base character using Unicode combining characters.
    Only applies to the first character of the input string.

    Args:
        base_char (str): The character(s) to be accented (only first char gets accent)
        accent (str): The LaTeX accent command (without backslash)

    Returns:
        str: The string with first character accented in normalized form
    """
    if not base_char:
        return base_char

    if accent not in ACCENT_MAP:
        return base_char

    # Split into first char and rest
    first_char = base_char[0]
    rest = base_char[1:]

    # Combine only the first character with the accent and normalize
    combined = first_char + ACCENT_MAP[accent]
    return unicodedata.normalize("NFC", combined) + rest


def convert_tex_diacritics(text: str) -> str:
    """
    Convert LaTeX diacritic commands to Unicode characters.
    """
    # Handle regular accents
    return substitute_patterns(text, ACCENT_PATTERNS, parse_diacritic_match)


def parse_diacritic_match(
    text: str, match: re.Match, accent_name: str
) -> Tuple[str, int]:
    """Parse a diacritic match and return the converted text and the end position"""
    matched_str = match.group(0)
    # start_pos = match.start()
    end_pos = match.end()

    last_char = matched_str[-1]
    if last_char == "{":
        out, nested_end_pos = extract_nested_content(text[end_pos - 1 :])
        if out:
            out = out.strip()
            last_char = out
            end_pos += nested_end_pos - 1

    converted = apply_accent(last_char, accent_name)
    return converted, end_pos


class DiacriticsHandler(TokenHandler):
    def can_handle(self, content: str) -> bool:
        """Check if the content contains any diacritic commands"""
        return any(pattern.match(content) for pattern in ACCENT_PATTERNS.values())

    def handle(
        self, content: str, prev_token: Optional[Dict] = None
    ) -> Tuple[Optional[Dict], int]:
        """Handle diacritic commands and return appropriate token"""
        for accent_name, pattern in ACCENT_PATTERNS.items():
            match = pattern.match(content)
            if match:
                converted, end_pos = parse_diacritic_match(content, match, accent_name)
                return {"type": "text", "content": converted}, end_pos

        return None, 0


if __name__ == "__main__":
    # Test cases
    test_strings = [
        r"\'{e} \'{e}",  # with braces
        r"\'e",  # without braces
        r"\c{c}",  # cedilla with braces
        r"\c c",  # cedilla with space
        r"\vec{x}",  # vector with braces
        r"\vec x",  # vector with space
        r"\'{e}llo",  # in word
        r"\grave{a}",  # with braces
        r"\grave a",  # without braces
        r"\.DOT",
        r"\.  {sss}",
        r"\vec  a \vec333",
        r"\vec{x}",
        r"\vec x",
        r"\vec3",
        # Test multiple vector accents in one string
        r"\vec{x}\vec y\vec3",
        # Test with numbers and other characters
        r"\vec333",
        r"\vec{333}",
        # Test other diacritical marks
        r"\dot{x}",
        r"\ddot{x}",
        r"\hat{x}",
        r"\bar{x}",
        r"\not{=}",
        r"\H{x}",
    ]

    patterns = generate_accent_patterns()
    for test in test_strings:
        converted = convert_tex_diacritics(test)
        print(test, "->", converted)
