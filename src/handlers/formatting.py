import re
from collections import OrderedDict
from typing import Callable, Dict, Optional, Tuple
from src.handlers.base import TokenHandler
from src.tex_utils import extract_nested_content


DEFINE_COLOR_PATTERN = re.compile(
    r'''
    \\definecolor\*?        # \definecolor command
    {[^}]*}                # color name in braces
    {[^}]*}  # color model eg RGB, rgb, HTML, gray, cmyk
    {[^}]*}                # color values
    ''',
    re.VERBOSE
)
COLOR_COMMANDS_PATTERN = re.compile(
    r'''
    \\(?:
        color\*?{[^}]*}                      # \color{..}
        # |textcolor\*?{[^}]*}{[^}]*}          # \textcolor{color}{text}
        |colorbox\*?{[^}]*}{[^}]*}           # \colorbox{color}{text}
        |fcolorbox\*?{[^}]*}{[^}]*}{[^}]*}   # \fcolorbox{border}{bg}{text}
        |(?:row|column|cell)color\*?{[^}]*}   # \rowcolor, \columncolor, \cellcolor
        |pagecolor\*?{[^}]*}                  # \pagecolor{..}
        |normalcolor                          # \normalcolor
        |color{[^}]*![^}]*}                  # color mixing like \color{red!50!blue}
    )
    ''',
    re.VERBOSE
)

RAW_PATTERNS = OrderedDict([
    # Comments
    ('comment', r'%([^\n]*)'),

    # top level commands
    ('documentclass', r'\\documentclass(?:\s*\[([^\]]*)\])?\s*\{([^}]+)\}'),
    ('usepackage', r'\\usepackage(?:\s*\[([^\]]*)\])?\s*\{([^}]+)\}'),

    # Formatting commands
    ('setup', r'\\hypersetup\s*{'),
    ('make', r'\\(?:maketitle|makeatletter|makeatother)\b'),
    ('page', r'\\(?:centering|raggedright|raggedleft|noindent|par|clearpage|cleardoublepage|newpage|linebreak|nopagebreak|pagebreak|bigskip|medskip|smallskip|hfill|vfill|break|scriptsize)\b'),
    ('style', r'\\(?:pagestyle|thispagestyle|theoremstyle)\s*\{[^}]*\}'),
    ('newstyle', r'\\(?:newpagestyle|renewpagestyle)\s*\{[^}]*\}\s*{'),
    ('font', r'\\(?:mdseries|bfseries|itshape|slshape|normalfont|ttfamily)\b'),
 
    # setters
    ('newsetlength', r'\\(?:newlength\s*\{[^}]*\})|\\setlength\s*\{([^}]+)\}\{([^}]+)\}'),
    ('setcounter', r'\\setcounter\s*\{([^}]+)\}\{([^}]+)\}'),

    # New margin and size commands allowing any characters after the number
    ('margins', r'\\(?:topmargin|oddsidemargin|evensidemargin|textwidth|textheight|footskip|headheight|headsep|marginparsep|marginparwidth|parindent|parskip|vfuzz|hfuzz)\s*([-+]?\d*\.?\d+.*)\b'),

    # spacing 
    ('spacing', r'\\(?:'
        r'quad|qquad|,|;|'  # \quad, \qquad, \, \;
        r'hspace\*?\s*{([^}]+)}|'  # \hspace{length}
        r'hskip\s*\d*\.?\d+(?:pt|mm|cm|in|em|ex|sp|bp|dd|cc|nd|nc)\b'  # \hskip 10pt
        r')'),
    
    # number
    ('number', r'\\(?:numberwithin)\s*\{[^}]*\}\s*\{[^}]*\}'),

    # table
    ('newcolumntype', r'\\(?:newcolumntype|renewcolumntype)\s*\{[^}]*\}\s*{'),
    ('separators', r'\\(?:'
        r'hline|'  # no args
        r'vspace\s*{([^}]+)}|'
        r'cline\s*{([^}]+)}|'  # {n-m}
        r'(?:midrule|toprule|bottomrule)(?:\[\d*[\w-]*\])?|'  # optional [trim]
        r'cmidrule(?:\[([^\]]*)\])?\s*{([^}]+)}|'  # optional [trim] and {n-m}
        r'hdashline(?:\[[\d,\s]*\])?|'  # optional [length,space]
        r'cdashline\s*{([^}]+)}|'  # {n-m}
        r'specialrule\s*{([^}]*)}\s*{([^}]*)}\s*{([^}]*)}|'  # {height}{above}{below}
        r'addlinespace(?:\[([^\]]*)\])?|'  # optional [length]
        r'rule\s*{[^}]*}\s*{[^}]*}|'  # \rule{width}{height}
        r'morecmidrules'  # no args
        r')'),
    
    ('backslash', r'\\(?:backslash|textbackslash)\b'),

    ('ensuremath', r'\\ensuremath\s*{'),

    ('niceties', r'\\(?:normalsize)\s*{')
])

# Then compile them into a new dictionary
PATTERNS = OrderedDict(
    (key, re.compile(pattern))
    for key, pattern in RAW_PATTERNS.items()
)
PATTERNS['color'] = COLOR_COMMANDS_PATTERN
PATTERNS['definecolor'] = DEFINE_COLOR_PATTERN


class FormattingHandler(TokenHandler):
    def can_handle(self, content: str) -> bool:
        return any(pattern.match(content) for pattern in PATTERNS.values())
    
    def handle(self, content: str) -> Tuple[Optional[Dict], int]:
        # Try each pattern until we find a match
        for pattern_name, pattern in PATTERNS.items():
            match = pattern.match(content)
            if match:
                if pattern_name == 'backslash':
                    return {
                        'type': 'text',
                        'content': r'\\'
                    }, match.end()
                elif pattern_name == 'spacing':
                    return {'type': 'text', 'content': ' '}, match.end()
                elif pattern_name in ['newcolumntype', 'newstyle', 'setup']:
                    # extracted nested
                    start_pos = match.end() - 1
                    extracted_content, end_pos = extract_nested_content(content[start_pos:])
                    return None, start_pos + end_pos
                elif pattern_name == 'ensuremath':
                    start_pos = match.end() - 1
                    extracted_content, end_pos = extract_nested_content(content[start_pos:])
                    return {'type': 'equation', 'content': extracted_content, 'display': 'inline'}, start_pos + end_pos
                elif pattern_name == 'niceties':
                    start_pos = match.end() - 1
                    extracted_content, end_pos = extract_nested_content(content[start_pos:])
                    return {'type': 'text', 'content': extracted_content}, start_pos + end_pos
                # ignore formatting commands
                return None, match.end()
        
        return None, 0
    
if __name__ == "__main__":
    handler = FormattingHandler()
    print(handler.handle(r"\textbackslash"))
    print(handler.handle(r"\maketitle"))