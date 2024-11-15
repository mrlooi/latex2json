import re
from collections import OrderedDict

# NOTE: THESE patterns are primarily for content inside document environments already. i.e. no bibliography, etc
# NOTE: Don't handle text related commands e.g. \text, \textbf, \textit, \mathbb etc. We will process them on render
# NOTE: We also ignore itemlist containers e.g. \enumerate, \itemize, \description since we treat them as lists internally

# ASSUMES ORDERD DICT (PYTHON 3.7+)
RAW_PATTERNS = OrderedDict([
    # 1. Commands that need nested brace handling (simplified patterns)
    ('section', r'\\(?:(?:sub)*section)\s*{'),
    ('paragraph', r'\\(?:(?:sub)*paragraph)\s*{'),
    ('part', r'\\part\s*{'),
    ('chapter', r'\\chapter\s*{'),
    ('footnote', r'\\footnote\s*{'),
    ('caption', r'\\caption\s*{'),
    ('captionof', r'\\captionof\s*{([^}]*?)}\s*{'),
    ('hyperref', r'\\hyperref\s*\[([^]]*)\]\s*{'),
    ('href', r'\\href\s*{([^}]*)}\s*{'),

    # Environment patterns
    ('equation', r'\\begin\{equation\*?\}(.*?)\\end\{equation(?:\*)?\}'),
    ('align', r'\\begin\{align\*?\}(.*?)\\end\{align(?:\*)?\}'),
    ('gather', r'\\begin\{gather\*?\}(.*?)\\end\{gather(?:\*)?\}'),
    ('tabular', r'\\begin\{tabular\}(?:\[[^\]]*\])?\{([^}]*)\}(.*?)\\end\{tabular\}'),
    ('environment', r'\\begin\{([^}]*)\}(.*?)\\end\{([^}]*)\}'),

    # Math delimiters
    ('equation_display_$$', r'\$\$([\s\S]*?)\$\$'),
    ('equation_inline_$', r'\$([^$]*)\$'),
    ('equation_display_brackets', r'\\\[(.*?)\\\]'),
    ('equation_inline_brackets', r'\\\((.*?)\\\)'),

    # Simple commands
    ('ref', r'\\ref\s*{([^}]*)}'),
    ('eqref', r'\\eqref\s*{([^}]*)}'),
    ('label', r'\\label\s*{([^}]*)}'),
    ('url', r'\\url\s*{([^}]*)}'),
    ('includegraphics', r'\\includegraphics\s*\[([^\]]*)\]\s*{([^}]*)}'),
    
    # Citations
    ('citation', r'\\(?:cite|citep)(?:\[([^\]]*)\])?\s*{([^}]*)}'),
    
    # Comments
    ('comment', r'%([^\n]*)'),
    
    # Formatting commands
    ('formatting', r'\\(usepackage|centering|raggedright|raggedleft|noindent|clearpage|cleardoublepage|newpage|linebreak|pagebreak|bigskip|medskip|smallskip|hfill|vfill|break)\b'),

    # Special handling for newcommand
    ('newcommand', r'\\(?:new|renew)command\*?(?:{\\([^}]+)}|\\([^[\s{]+))(?:\s*\[(\d+)\])?((?:\s*\[[^]]*\])*)\s*{'),

    ('item', r'\\item(?:\[(.*?)\])?\s*([\s\S]*?)(?=\\item|$)'),

    # Line breaks
    ('newline', r'\\(?:newline|linebreak)\b'),
])

# Update NESTED_BRACE_COMMANDS to reflect all commands needing special handling
NESTED_BRACE_COMMANDS = {
    # Section-like commands
    'section',
    'paragraph',
    'part',
    'chapter',
    
    # Other commands with potentially nested content
    'caption',
    'captionof',  # Second argument only
    'footnote',
    'hyperref',
    'href',       # Second argument only
    # 'newcommand', # handled separately
}

# needed for re.DOTALL flag (also written as re.S) makes the dot (.) special character match any character including newlines
EQUATION_PATTERNS = {'equation', 'align', 'gather'}
MULTILINE_PATTERNS = EQUATION_PATTERNS | {
    'equation_display_$$', 'equation_display_brackets',
    'table', 'tabular', 'figure', 'environment', 'item'
    # 'itemize', 'enumerate', 'description', 
}

# Then compile them into a new dictionary
PATTERNS = OrderedDict(
    (key, re.compile(pattern, re.DOTALL if key in MULTILINE_PATTERNS else 0))
    for key, pattern in RAW_PATTERNS.items()
)

LABEL_PATTERN = PATTERNS['label']
TABULAR_PATTERN = PATTERNS['tabular']
CITATION_PATTERN = PATTERNS['citation']
NEWLINE_PATTERN = PATTERNS['newline']

def extract_citations(text):
    """
    Extract citations from text, including optional title arguments in square brackets
    Returns a list of tuples: (citation, title) where title may be None
    """
    citations = []
    matches = re.finditer(CITATION_PATTERN, text)
    for match in matches:
        # Get the full match to extract the optional title
        full_match = match.group(0)
        # Look for optional title argument
        title_match = re.search(r'\[(.*?)\]', full_match)
        title = title_match.group(1) if title_match else None
        
        # Split citations if there are multiple
        for citation in match.group(1).split(','):
            citations.append((citation.strip(), title))
            
    return citations if citations else None

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

SEPARATORS = [
    '\\hline',      # Basic horizontal line
    '\\cline',      # From booktabs - partial horizontal line
    '\\midrule',    # From booktabs - middle rule
    '\\toprule',    # From booktabs - top rule
    '\\bottomrule', # From booktabs - bottom rule
    '\\cmidrule',   # From booktabs - partial rule
    '\\hdashline',  # From arydshln - dashed line
    '\\cdashline',  # From arydshln - partial dashed line
    '\\specialrule', # From booktabs - custom thickness rule
    '\\addlinespace',  # From booktabs - adds vertical space
    '\\morecmidrules', # From booktabs - allows multiple cmidrules
]

SECTION_LEVELS = {
    'part': 0,
    'chapter': 1,
    'section': 1,
    'subsection': 2,
    'subsubsection': 3,
    'paragraph': 4,
    'subparagraph': 5
}