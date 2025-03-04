import re
from typing import Dict

from latex2json.latex_maps._latex2unicode_map import latex2unicode

UNICODE_PATTERN = r"\\u([0-9a-fA-F]{4,6})"


class LatexUnicodeConverter:
    # Class-level storage
    _latex2str: Dict[str, str] = None
    _patterns = None

    @classmethod
    def _ensure_initialized(cls):
        if cls._latex2str is None:
            cls._latex2str = cls._init_latex2unicode()
            cls._patterns = cls._create_categorized_regex_patterns()

    @classmethod
    def _init_latex2unicode(cls):
        _latex2str: Dict[str, str] = {}
        for key, value in latex2unicode.items():
            _latex2str[key] = value if isinstance(value, str) else chr(value)
        return _latex2str

    @classmethod
    def _create_categorized_regex_patterns(cls):
        patterns = {
            "unicode": [UNICODE_PATTERN],  # add unicode at top to check it first
            "ensuremath": [],
            "text": [],
            "math": [],
            "font": [],
            "other": [],
        }

        # Categorize each command
        for cmd in cls._latex2str.keys():
            if not cmd.startswith("\\") and not cmd.startswith("{"):
                continue

            # Add word boundary after the command to prevent partial matches
            escaped = re.escape(cmd)
            if escaped[-1].isalpha() or escaped[-1] == "@":
                escaped = r"(?:%s\{\}|%s(?![a-zA-Z]))" % (escaped, escaped)
            if cmd.startswith("\\ensuremath"):
                patterns["ensuremath"].append(escaped)
            elif cmd.startswith("\\text"):
                patterns["text"].append(escaped)
            elif cmd.startswith("\\math"):
                patterns["math"].append(escaped)
            elif "font" in cmd:
                patterns["font"].append(escaped)
            else:
                patterns["other"].append(escaped)

        # Compile patterns for each category
        compiled_patterns = {}
        for category, pattern_list in patterns.items():
            if pattern_list:  # Only compile if we have patterns
                compiled_patterns[category] = re.compile("|".join(pattern_list))

        return compiled_patterns

    def __init__(self):
        self.__class__._ensure_initialized()
        # Use direct reference to class variables
        self.latex2str = self.__class__._latex2str
        self.patterns = self.__class__._patterns

    def convert(self, text: str) -> str:
        result = text

        def handle_match(match, pattern_type):
            c = match.group(0).strip()
            # Handle Unicode escape sequences
            if pattern_type == "unicode":
                try:
                    return chr(int(match.group(1), 16))
                except (ValueError, IndexError):
                    return c
            # Handle regular LaTeX commands
            if c.endswith("{}"):
                c = c[:-2].strip()
            return self.latex2str.get(c, c)

        # Process in specific order: longer commands first
        for pattern_type, pattern in self.patterns.items():
            result = pattern.sub(lambda m: handle_match(m, pattern_type), result)

        return result


# Example usage
if __name__ == "__main__":
    converter = LatexUnicodeConverter()

    test_strings = [
        # r"This is a test \textbackslash with Erd\H{o}s some commands",
        # r"Multiple \textdollar \textyen symbols",
        # r"\ensuremath{\succnsim}\oe\# ` \'{}A",
        # "\\mathtt{0}\\mathbb{E}f",
        # "{\\fontencoding{LELA}\\selectfont\\char40}",
        # r"\v{l} \l \ij \o \O \L \Lerer",
        # r"\H{o}",
        r"\u00a7",
    ]

    for text in test_strings:
        result = converter.convert(text)
        print(f"Original: {text}")
        print(f"Converted: {result}\n")
