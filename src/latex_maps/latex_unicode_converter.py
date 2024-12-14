import re
from typing import Dict

from src.latex_maps._latex2unicode_map import latex2unicode


class LatexUnicodeConverter:
    def __init__(self):
        # create copy of latex2unicode
        self.latex2str = self._init_latex2unicode()
        self.patterns = self._create_categorized_regex_patterns()

    def _init_latex2unicode(self):
        _latex2str: Dict[str, str] = {}
        for key, value in latex2unicode.items():
            _latex2str[key] = value if isinstance(value, str) else chr(value)
        return _latex2str

    def _create_categorized_regex_patterns(self):
        patterns = {"ensuremath": [], "text": [], "math": [], "font": [], "other": []}

        # Categorize each command
        for cmd in self.latex2str.keys():
            if not cmd.startswith("\\") and not cmd.startswith("{"):
                continue

            # Add word boundary after the command to prevent partial matches
            escaped = re.escape(cmd)
            if escaped[-1].isalpha():
                escaped += r"(?![a-zA-Z])"
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

    def convert(self, text: str) -> str:
        result = text

        # Process in specific order: longer commands first
        for pattern in self.patterns.values():
            result = pattern.sub(lambda m: self.latex2str[m.group(0)], result)

        return result


# Example usage
if __name__ == "__main__":
    converter = LatexUnicodeConverter()

    test_strings = [
        r"This is a test \textbackslash with Erd\H{o}s some commands",
        r"Multiple \textdollar \textyen symbols",
        r"\ensuremath{\succnsim}\oe\# ` \'{}A",
        "\\mathtt{0}\\mathbb{E}f",
        "{\\fontencoding{LELA}\\selectfont\\char40}",
        r"\v{l} \l \ij \o \O \L \Lerer",
        r"\H{o}",
    ]

    print()
    for text in test_strings:
        result = converter.convert(text)
        print(f"Original: {text}")
        print(f"Converted: {result}\n")
