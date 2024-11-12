import re

PATTERNS = {
    'section': r'\\section{([^}]*)}',
    'subsection': r'\\subsection{([^}]*)}',
    'paragraph': r'\\paragraph{([^}]*)}',
    # Handle specific environments first (python 3.7+ is ordered dict)
    'equation': r'\\begin\{equation\*?\}(.*?)\\end\{equation(?:\*)?\}',
    'align': r'\\begin\{align\*?\}(.*?)\\end\{align(?:\*)?\}',
    'table': r'\\begin\{table\*?\}(.*?)\\end\{table(?:\*)?\}',  # Add table pattern
    # Generic environment pattern comes last
    'environment': r'\\begin\{([^}]*)\}(.*?)\\end\{([^}]*)\}',

    'equation_inline': r'\$([^$]*)\$', # we want to parse inline equations in order to roll out any potential newcommand definitions
    'citation': r'\\(?:cite|citep)(?:\[([^\]]*)\])?{([^}]*)}',  # Updated to handle optional arguments
    'ref': r'\\ref{([^}]*)}',
    'eqref': r'\\eqref{([^}]*)}',
    'comment': r'%([^\n]*)',
    'label': r'\\label{([^}]*)}',
    'newcommand': r'\\(?:new|renew)command{\\([^}]+)}\{([^}]*)\}',  # Handles both new and renew
    'newcommand_args': r'\\(?:new|renew)command\*?(?:{\\([^}]+)}|\\([^[\s{]+))(?:\s*\[(\d+)\])?((?:\s*\[[^]]*\])*)\s*{((?:[^{}]|{(?:[^{}]|{[^{}]*})*})*)}',

    'footnote': r'\\footnote{([^}]*)}',
}

LABEL_PATTERN = PATTERNS['label']
CAPTION_PATTERN = r'\\caption{([^}]*)}'
TABULAR_PATTERN = r'\\begin\{tabular\}(?:\[[^\]]*\])?\{([^}]*)\}(.*?)\\end\{tabular\}'
CITATION_PATTERN = PATTERNS['citation']

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


SEPARATORS = [
    '\\hline',      # Basic horizontal line
    '\\midrule',    # From booktabs - middle rule
    '\\toprule',    # From booktabs - top rule
    '\\bottomrule', # From booktabs - bottom rule
    '\\cmidrule',   # From booktabs - partial rule
    '\\hdashline',  # From arydshln - dashed line
    '\\cdashline',  # From arydshln - partial dashed line
    '\\specialrule' # From booktabs - custom thickness rule
]