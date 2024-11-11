PATTERNS = {
    'section': r'\\section{([^}]*)}',
    'subsection': r'\\subsection{([^}]*)}',
    'paragraph': r'\\paragraph{([^}]*)}',
    # Handle specific environments first (python 3.7+ is ordered dict)
    'equation': r'\\begin\{equation\*?\}(.*?)\\end\{equation(?:\*)?\}',
    'align': r'\\begin\{align\*?\}(.*?)\\end\{align(?:\*)?\}',
    'table': r'\\begin\{table\*?\}(.*?)\\end\{table(?:\*)?\}',  # Add table pattern
    # Generic environment pattern comes last
    # 'environment': r'\\begin\{([^}]*)\}(.*?)\\end\{([^}]*)\}',

    'equation_inline': r'\$([^$]*)\$',
    'citation': r'\\(?:cite|citep){([^}]*)}',
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