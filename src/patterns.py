import re
from collections import OrderedDict


# NOTE: THESE patterns are primarily for content inside document environments already. i.e. no bibliography, etc
# NOTE: Don't handle text related commands e.g. \text, \textbf, \textit, \mathbb etc. We will process them on render
# NOTE: We also ignore itemlist containers e.g. \enumerate, \itemize, \description since we parse them as regular env and label as lists via env_name check

# ASSUMES ORDERD DICT (PYTHON 3.7+)
RAW_PATTERNS = OrderedDict([
    ('label', r'\\label\s*{'),

    # Line breaks
    ('newline', r'\\(?:newline|linebreak)(?![a-zA-Z])'),
    # Line break with optional spacing specification
    ('break_spacing', r'\\\\(?:\s*\[([^]]*)\])?'),  # Added \s* to handle optional whitespace
])

# needed for re.DOTALL flag (also written as re.S) makes the dot (.) special character match any character including newlines
MULTILINE_PATTERNS = {
    # 'itemize', 'enumerate', 'description', 
}

# Then compile them into a new dictionary
PATTERNS = OrderedDict(
    (key, re.compile(pattern, re.DOTALL if key in MULTILINE_PATTERNS else 0))
    for key, pattern in RAW_PATTERNS.items()
)

LABEL_PATTERN = PATTERNS['label']
NEWLINE_PATTERN = PATTERNS['newline']

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
