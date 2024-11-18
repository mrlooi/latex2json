import re
from collections import OrderedDict

EQUATION_PATTERNS = {
    'equation',    # basic numbered equation
    'align',       # aligned equations
    'gather',      # centered equations
    'multline',    # long equation split across lines
    'eqnarray',    # old style align (deprecated but used)
    'flalign',     # flush aligned equations
    'alignat'      # aligned with custom spacing
}

# NOTE: THESE patterns are primarily for content inside document environments already. i.e. no bibliography, etc
# NOTE: Don't handle text related commands e.g. \text, \textbf, \textit, \mathbb etc. We will process them on render
# NOTE: We also ignore itemlist containers e.g. \enumerate, \itemize, \description since we parse them as regular env and label as lists via env_name check

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

    # Env patterns that we want to handle (non-equation, non-generic)
    ('tabular', r'\\begin\{tabular\}(?:\[[^\]]*\])?\{([^}]*)\}(.*?)\\end\{tabular\}'),
    ('verbatim_env', r'\\begin\{verbatim\}(.*?)\\end\{verbatim\}'),
    ('lstlisting', r'\\begin\{lstlisting\}(?:\[([^\]]*)\])?(.*?)\\end\{lstlisting\}'),  # Updated pattern
 
    ('verb_command', r'\\verb\*?([^a-zA-Z])(.*?)\1'),  # \verb|code| or \verb*|code| where | can be any non-letter delimiter

    # Math delimiters
    ('equation_display_$$', r'\$\$([\s\S]*?)\$\$'),
    ('equation_inline_$', r'\$([^$]*)\$'),
    ('equation_display_brackets', r'\\\[(.*?)\\\]'),
    ('equation_inline_brackets', r'\\\((.*?)\\\)'),

    # Simple commands
    ('ref', r'\\ref\s*{'),
    ('eqref', r'\\eqref\s*{'),
    ('label', r'\\label\s*{'),
    ('url', r'\\url\s*{'),
    ('includegraphics', r'\\includegraphics\s*(?:\[([^\]]*)\])?\s*{'),
    
    # Citations
    ('citation', r'\\(?:cite|citep)(?:\[([^\]]*)\])?\s*{'),
    
    # Comments
    ('comment', r'%([^\n]*)'),

    # Matches newcommand/renewcommand up to the opening definition brace, capturing the command name, 
    # number of arguments, and optional default values. Supports both {\commandname} and \commandname syntax.    
    ('newcommand', r'\\(?:new|renew)command\*?(?:{\\([^}]+)}|\\([^\s{[]+))(?:\s*\[(\d+)\])?((?:\s*\[[^]]*\])*)\s*{'),

    # Matches newenvironment up to \newenvironment{name} only. parse optional args later
    ('newenvironment', r'\\(?:new|renew)environment\*?\s*{([^}]+)}'),


    # Itemize, enumerate, description
    ('item', r'\\item(?:\[(.*?)\])?\s*([\s\S]*?)(?=\\item|$)'),

    # newtheorem
    ('newtheorem', r'\\newtheorem{([^}]*)}(?:\[([^]]*)\])?{([^}]*)}(?:\[([^]]*)\])?'),

    # Put these all at the end

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
])

# Add equation patterns dynamically
equation_pattern_dict = {
    name: rf'\\begin\{{{name}\*?\}}(.*?)\\end\{{{name}(?:\*)?\}}'
    for name in EQUATION_PATTERNS
}
RAW_PATTERNS.update(equation_pattern_dict)
# ADD generic env pattern at the end (SO THAT HANDLED AFTER EQUATIONS etc)
RAW_PATTERNS['environment'] = r'\\begin\{([^}]*)\}(.*?)\\end\{([^}]*)\}'


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
    'ref',        # Added
    'eqref',      # Added
    # 'label',      # Added
    'url',        # Added
    'includegraphics',  # Added (second argument)
    'citation',   # Added
}

# needed for re.DOTALL flag (also written as re.S) makes the dot (.) special character match any character including newlines
MULTILINE_PATTERNS = EQUATION_PATTERNS | {
    'equation_display_$$', 'equation_display_brackets',
    'table', 'tabular', 'figure', 'environment', 'item',
    'verbatim_env', 'lstlisting',
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
