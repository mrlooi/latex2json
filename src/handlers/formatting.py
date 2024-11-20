import re
from collections import OrderedDict
from typing import Callable, Dict, Optional, Tuple
from src.handlers.base import TokenHandler

RAW_PATTERNS = OrderedDict([
    # Comments
    ('comment', r'%([^\n]*)'),

    # Formatting commands
    ('formatting', r'\\(usepackage|centering|raggedright|raggedleft|noindent|clearpage|cleardoublepage|newpage|linebreak|pagebreak|bigskip|medskip|smallskip|hfill|vfill|break)\b'),

    ('separators', r'\\(?:'
        r'hline|'  # no args
        r'cline\s*{([^}]+)}|'  # {n-m}
        r'(?:midrule|toprule|bottomrule)(?:\[\d*[\w-]*\])?|'  # optional [trim]
        r'cmidrule(?:\[([^\]]*)\])?\s*{([^}]+)}|'  # optional [trim] and {n-m}
        r'hdashline(?:\[[\d,\s]*\])?|'  # optional [length,space]
        r'cdashline\s*{([^}]+)}|'  # {n-m}
        r'specialrule\s*{([^}]*)}\s*{([^}]*)}\s*{([^}]*)}|'  # {height}{above}{below}
        r'addlinespace(?:\[([^\]]*)\])?|'  # optional [length]
        r'morecmidrules'  # no args
        r')'),
])

# Then compile them into a new dictionary
PATTERNS = OrderedDict(
    (key, re.compile(pattern))
    for key, pattern in RAW_PATTERNS.items()
)

class FormattingHandler(TokenHandler):
    def can_handle(self, content: str) -> bool:
        return any(pattern.match(content) for pattern in PATTERNS.values())
    
    def handle(self, content: str) -> Tuple[Optional[Dict], int]:
        # Try each pattern until we find a match
        for pattern_name, pattern in PATTERNS.items():
            match = pattern.match(content)
            if match:
                # ignore formatting commands
                return None, match.end()
        
        return None, 0
    
if __name__ == "__main__":
    handler = FormattingHandler()
    print(handler.can_handle(r"\hline"))