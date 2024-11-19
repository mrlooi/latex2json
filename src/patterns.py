import re
from collections import OrderedDict


# NOTE: THESE patterns are primarily for content inside document environments already. i.e. no bibliography, etc
# NOTE: Don't handle text related commands e.g. \text, \textbf, \textit, \mathbb etc. We will process them on render
# NOTE: We also ignore itemlist containers e.g. \enumerate, \itemize, \description since we parse them as regular env and label as lists via env_name check

# ASSUMES ORDERD DICT (PYTHON 3.7+)
RAW_PATTERNS = OrderedDict([
    ('label', r'\\label\s*{'),

    # Comments
    ('comment', r'%([^\n]*)'),

    # Itemize, enumerate, description
    ('item', r'\\item(?:\[(.*?)\])?\s*([\s\S]*?)(?=\\item|$)'),

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
    # Line breaks
    ('newline', r'\\(?:newline|linebreak)\b'),
    # Line break with optional spacing specification
    ('break_spacing', r'\\\\(?:\s*\[([^]]*)\])?'),  # Added \s* to handle optional whitespace

    # Generic env pattern
    ('environment', r'\\begin\{([^}]*)\}(.*?)\\end\{([^}]*)\}')
])

# needed for re.DOTALL flag (also written as re.S) makes the dot (.) special character match any character including newlines
MULTILINE_PATTERNS = {
    'environment', 'item',
    # 'itemize', 'enumerate', 'description', 
}

# Then compile them into a new dictionary
PATTERNS = OrderedDict(
    (key, re.compile(pattern, re.DOTALL if key in MULTILINE_PATTERNS else 0))
    for key, pattern in RAW_PATTERNS.items()
)

LABEL_PATTERN = PATTERNS['label']
NEWLINE_PATTERN = PATTERNS['newline']

LIST_ENVIRONMENTS = ['itemize', 'enumerate', 'description']

# Map environment names to their types
ENV_TYPES = {
    "table": "table",
    "subtable": "table",
    "subsubtable": "table",
    "figure": "figure",
    "subfigure": "figure",
    "subfloat": "figure",  # another common figure subdivision
    **{env: "list" for env in LIST_ENVIRONMENTS}
}

SECTION_LEVELS = {
    'part': 0,
    'chapter': 1,
    'section': 1,
    'subsection': 2,
    'subsubsection': 3,
    'paragraph': 4,
    'subparagraph': 5
}


TEXT_PATTERNS = OrderedDict([
    ('text_commands', r'\\(?:text|textbf|textit|textrm|texttt|textsc|textsf|textmd|textup|textsl|textnormal)\s*{([^}]*)}'),
    ('math_text', r'\\(?:mathbb|mathbf|mathit|mathrm|mathsf|mathtt|mathcal|mathscr|mathfrak)\s*{([^}]*)}'),
    ('font_commands', r'\\(?:em|bf|it|rm|sf|tt|sc|sl|normalfont)\b'),
])
