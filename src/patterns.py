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

    'equation_inline': r'\$([^$]*)\$',
    'citation': r'\\(?:cite|citep)(?:\[[^\]]*\])?{([^}]*)}',  # Updated to handle optional arguments
    'ref': r'\\ref{([^}]*)}',
    'eqref': r'\\eqref{([^}]*)}',
    'comment': r'%([^\n]*)',
    'label': r'\\label{([^}]*)}',
    'newcommand': r'\\(?:new|renew)command{\\([^}]+)}\{([^}]*)\}',  # Handles both new and renew
    'newcommand_args': r'\\(?:new|renew)command\*?(?:{\\([^}]+)}|\\([^[\s{]+))(?:\s*\[(\d+)\])?((?:\s*\[[^]]*\])*)\s*{((?:[^{}]|{(?:[^{}]|{[^{}]*})*})*)}',
}

LABEL_PATTERN = PATTERNS['label']
CAPTION_PATTERN = r'\\caption{([^}]*)}'
TABULAR_PATTERN = r'\\begin\{tabular\}(?:\[[^\]]*\])?\{([^}]*)\}(.*?)\\end\{tabular\}'
CITATION_PATTERN = PATTERNS['citation']

def extract_citations(text):
    """
    Extract citations from text, ignoring any optional arguments in square brackets
    """
    citations = []
    matches = re.finditer(CITATION_PATTERN, text)
    for match in matches:
        citations.extend(match.group(1).split(','))
    return [c.strip() for c in citations] if citations else None