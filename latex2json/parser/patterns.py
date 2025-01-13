import re
from collections import OrderedDict


BRACE_CONTENT_PATTERN = r"\{([^}]+)\}"
NUMBER_PATTERN = r"[-+]?\d*\.?\d+"

# Add these compiled patterns at module level
# match $ or % or { or } only if not preceded by \
# Update DELIM_PATTERN to also match double backslashes and opening braces {
DELIM_PATTERN = re.compile(
    r"(?<!\\)(?:\\\\|\$|%|(?:^|[ \t])\{|\s{|\\\^|\\(?![$%&_#{}^~\\]))"
)

USEPACKAGE_PATTERN = re.compile(
    r"\\(?:usepackage|RequirePackage)(?:\s*\[[^\]]*\])?\s*\{([^}]+)\}",
    re.DOTALL,
)  # capture group 1

# ASSUMES ORDERD DICT (PYTHON 3.7+)
RAW_PATTERNS = OrderedDict(
    [
        ("label", r"\\label\s*{"),
        # Line breaks
        ("newline", r"\\(?:newline|linebreak)(?![a-zA-Z])"),
        # Line break with optional spacing specification
        (
            "break_spacing",
            r"\\\\(?:\s*\[([^]]*)\])?",
        ),  # Added \s* to handle optional whitespace
        (
            "line_continuation",
            r"\\(?:\s|$)",
        ),  # Single backslash followed by whitespace or end of string
    ]
)

# Then compile them into a new dictionary
PATTERNS = OrderedDict(
    (key, re.compile(pattern)) for key, pattern in RAW_PATTERNS.items()
)

LABEL_PATTERN = PATTERNS["label"]
NEWLINE_PATTERN = PATTERNS["newline"]

# These commands should not be overrwritten by newcommand/newenvironment
WHITELISTED_COMMANDS = [
    "newcommand",
    "begin",
    "end",
    "section",
    "subsection",
    "subsubsection",
    "paragraph",
    "subparagraph",
    "maketitle",
    "title",
    "author",
    "date",
    "part",
    "chapter",
    "abstract",
    "table",
    "figure",
    "cite",
    "citep",
    "citet",
    "caption",
    "captionof",
    "bibitem",
    "url",
    "ref",
    "\\",
    "\\\\",
    # text font
    "textbf",
    "textit",
    "textsl",
    "textsc",
    "textsf",
    "texttt",
    "textrm",
    "textup",
    "emph",
    # text size
    "texttiny",
    "textscriptsize",
    "textfootnotesize",
    "textsmall",
    "textnormal",
    "textlarge",
    "texthuge",
    "text",
    # legacy font
    # Basic text style commands
    "tt",
    "bf",
    "it",
    "sl",
    "sc",
    "sf",
    "rm",
    "em",
    "bold",
    # Font family declarations
    "rmfamily",
    "sffamily",
    "ttfamily",
    # Font shape declarations
    "itshape",
    "scshape",
    "upshape",
    "slshape",
    # Font series declarations
    "bfseries",
    "mdseries",
    # Font combinations and resets
    "normalfont",
    # Additional text mode variants
    "textup",
    "textnormal",
    "textmd",
    # math stuff (often used directly before math mode)
    "unboldmath",
    "boldmath",
    "mathversion{bold}",
    "mathversion{normal}",
    # Basic size commands
    "tiny",
    "scriptsize",
    "footnotesize",
    "small",
    "normalsize",
    "large",
    "Large",
    "LARGE",
    "huge",
    "Huge",
    # Additional size declarations
    "smaller",
    "larger",
]
