import re

PATTERNS = {
    'section': r'\\(?:(?:sub)*section){([^}]*)}',
    'paragraph': r'\\(?:(?:sub)*paragraph){([^}]*)}',

    # Handle specific begin environments first (python 3.7+ is ordered dict)
    'equation': r'\\begin\{equation\*?\}(.*?)\\end\{equation(?:\*)?\}',
    'align': r'\\begin\{align\*?\}(.*?)\\end\{align(?:\*)?\}',
    'equation_display_$$': r'\$\$([\s\S]*?)\$\$',  # Double dollar block equations with multiline support (make sure this is above equation_inline_$)
    'equation_inline_$': r'\$([^$]*)\$', # we want to parse inline equations in order to roll out any potential newcommand definitions
    'equation_display_brackets': r'\\\[(.*?)\\\]',  # Display math with \[...\]
    'equation_inline_brackets': r'\\\((.*?)\\\)',  # Inline math with \(...\)

    # Tables and figures
    'table': r'\\begin\{table\*?\}(.*?)\\end\{table(?:\*)?\}',  # Add table pattern
    'tabular': r'\\begin\{tabular\}(?:\[[^\]]*\])?\{([^}]*)\}(.*?)\\end\{tabular\}',
    'figure': r'\\begin\{figure\*?\}(.*?)\\end\{figure(?:\*)?\}',  # Add figure pattern

    # List environments - put before generic environment pattern
    'itemize': r'\\begin\{itemize\}(.*?)\\end\{itemize\}',
    'enumerate': r'\\begin\{enumerate\}(?:\[(.*?)\])?(.*?)\\end\{enumerate\}',
    'description': r'\\begin\{description\}(.*?)\\end\{description\}',

    # Generic begin environment pattern comes last
    'environment': r'\\begin\{([^}]*)\}(.*?)\\end\{([^}]*)\}',

    # REF patterns and label
    'ref': r'\\ref{([^}]*)}',
    'eqref': r'\\eqref{([^}]*)}',
    'hyperref': r'\\hyperref\[([^]]*)\]{([^}]*)}', # captures label and text
    'label': r'\\label{([^}]*)}',

    # Newcommand patterns
    'newcommand': r'\\(?:new|renew)command{\\([^}]+)}\{([^}]*)\}',  # Handles both new and renew
    'newcommand_args': r'\\(?:new|renew)command\*?(?:{\\([^}]+)}|\\([^[\s{]+))(?:\s*\[(\d+)\])?((?:\s*\[[^]]*\])*)\s*{((?:[^{}]|{(?:[^{}]|{[^{}]*})*})*)}',

    # URL patterns
    'url': r'\\url{([^}]*)}',                    # captures URL
    'href': r'\\href{([^}]*)}{([^}]*)}',         # captures URL and text

    'citation': r'\\(?:cite|citep)(?:\[([^\]]*)\])?{([^}]*)}',  # Updated to handle optional arguments
    'comment': r'%([^\n]*)',
    'footnote': r'\\footnote{([^}]*)}',
    'includegraphics': r'\\includegraphics\[([^\]]*)\]{([^}]*)}',
}

LABEL_PATTERN = PATTERNS['label']
CAPTION_PATTERN = r'\\caption{([^}]*)}'
TABULAR_PATTERN = PATTERNS['tabular']
GRAPHICS_PATTERN = PATTERNS['includegraphics']
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