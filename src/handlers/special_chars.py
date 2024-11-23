from collections import OrderedDict
from typing import Callable, Dict, Optional, Tuple

import re

from src.handlers.base import TokenHandler



# Regex pattern for legacy format special characters
LEGACY_PATTERNS = re.compile(r'(\s*)(\\[\'^_]){\s*([^}]+)\s*}', re.DOTALL)

# Regex pattern for special symbols without braces
SYMBOL_PATTERNS = re.compile(r'(\s*)(\\[oOlL])\b')

# Mapping from legacy to modern LaTeX commands
LEGACY_FORMAT_MAPPING = OrderedDict([
    (r'\^', 'textsuperscript'),    # superscript
    (r'\_', 'textsubscript'),      # subscript
    (r"\'", 'acute'),        # acute accent
])

# Mapping for special symbols
SYMBOL_MAPPING = OrderedDict([
    (r'\o', 'o'),           # slashed o
    (r'\O', 'O'),           # slashed O
    (r'\l', 'l'),           # slashed l
    (r'\L', 'L'),           # slashed L
])

# Add new mapping for diacritical marks
DIACRITIC_MAPPING = OrderedDict([
    (r'\`', '\u0300'),  # grave accent
    (r"\'", '\u0301'),  # acute accent
    (r'\^', '\u0302'),  # circumflex
    (r'\"', '\u0308'),  # umlaut/dieresis
    (r'\~', '\u0303'),  # tilde
    (r'\=', '\u0304'),  # macron
    (r'\.', '\u0307'),  # dot above
    (r'\u', '\u0306'),  # breve
    (r'\v', '\u030C'),  # caron/háček
    (r'\H', '\u030B'),  # double acute
    (r'\d', '\u0323'),  # dot below
    (r'\b', '\u0331'),  # bar under
    (r'\c', '\u0327'),  # cedilla
    (r'\k', '\u0328'),  # ogonek
    (r'\r', '\u030A'),  # ring above
    (r'\t', '\u0361'),  # tie
])

# Add new regex pattern for diacritics
DIACRITIC_PATTERN = re.compile(r'(\s*)(\\[`\'^\"\~=\.uvHdbckrt]){\s*([^}]+)\s*}', re.DOTALL)

class SpecialCharHandler(TokenHandler):
    def can_handle(self, content: str) -> bool:
        """
        Check if the content contains any special character patterns.
        """
        return (LEGACY_PATTERNS.match(content) is not None or 
                SYMBOL_PATTERNS.match(content) is not None or
                DIACRITIC_PATTERN.match(content) is not None)
    
    def handle(self, content: str) -> Tuple[Optional[Dict], int]:
        """
        Handle special character formatting in LaTeX.
        
        Args:
            content: The input string to process
            
        Returns:
            Tuple containing:
            - Dictionary with processed content and type, or None if no match
            - Ending position of the match
        """
        # # Try legacy patterns first
        # match = LEGACY_PATTERNS.match(content)
        # if match:
        #     whitespace = match.group(1)
        #     command = match.group(2).strip()
        #     text = match.group(3).strip()
            
        #     modern_command = LEGACY_FORMAT_MAPPING.get(command)
        #     if modern_command:
        #         output = {
        #             'type': 'command',
        #             'content': whitespace + r'\\' + modern_command + '{' + text + '}'
        #         }
        #     else:
        #         output = {
        #             'type': 'text',
        #             'content': match.group(0)
        #         }
        #     return output, match.end()
        
        # Try symbol patterns
        match = SYMBOL_PATTERNS.match(content)
        if match:
            whitespace = match.group(1)
            command = match.group(2)
            
            symbol = SYMBOL_MAPPING.get(command)
            if symbol:
                output = {
                    'type': 'text',
                    'content': match.group(0)
                }
            else:
                output = {
                    'type': 'text',
                    'content': match.group(0)
                }
            return output, match.end()
        
        # Try diacritic patterns
        match = DIACRITIC_PATTERN.match(content)
        if match:
            whitespace = match.group(1)
            command = match.group(2)
            base_char = match.group(3).strip()
            
            combining_char = DIACRITIC_MAPPING.get(command)
            if combining_char:
                # Combine the base character with the diacritic
                combined = base_char + combining_char
                output = {
                    'type': 'text',
                    'content': whitespace + combined
                }
                return output, match.end()
        
        return None, 0


if __name__ == "__main__":
    handler = SpecialCharHandler()

    # Test cases
    test_cases = [
        r"\^{superscript}",
        r"\_{subscript}",
        r"\'{e}",
        r"\o",
        r"\O",
        r"\l",
        r"\L",
        r" { \tt text} YOLO",  # Should not match
    ]

    # Update test cases
    additional_tests = [
        r"\`{e}",      # è
        r"\'{e}",      # é
        r'\^{e}',      # ê
        r'\"{e}',      # ë
        r'\~{n}',      # ñ
        r'\={a}',      # ā
        r'\.{z}',      # ż
        r'\H{o}'
    ]
    test_cases.extend(additional_tests)

    for test in test_cases:
        result, end_pos = handler.handle(test)
        print(f"\nInput: {test}")
        print(f"Output: {result}")
        print(f"Remaining: {test[end_pos:] if end_pos < len(test) else 'None'}")
