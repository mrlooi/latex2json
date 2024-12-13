import re
from collections import OrderedDict


BRACE_CONTENT_PATTERN = r"\{([^}]+)\}"
NUMBER_PATTERN = r"[-+]?\d*\.?\d+"

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

WHITELISTED_COMMANDS = [
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
]
