import re
from collections import OrderedDict


BRACE_CONTENT_PATTERN = r"\{([^}]+)\}"
OPTIONAL_BRACE_PATTERN = r"(?:\[[^\]]*\])?"

NUMBER_PATTERN = r"[-+]?\d*\.?\d+"

# Command pattern matches:
# 1. Standard commands: letters and @ (e.g., \foo, \@foo)
# 2. Non-letter commands (e.g., \<, \>, \=, \,, \., \;, \!, \|, \$, \%, \&, \#, \_, \{, \}, \<<, \>>)
# 3. Active character ~ which can behave like a command
command_pattern = r"\\([a-zA-Z@]+|[<>=,\.;!|$%&#_{}()\[\]~]+|\d)"
command_with_opt_brace_pattern = r"(?:%s|%s)" % (BRACE_CONTENT_PATTERN, command_pattern)

number_points_suffix = (
    NUMBER_PATTERN + r"\s*(?:pt|mm|cm|in|em|ex|sp|bp|dd|cc|nd|nc)?(?=[^a-zA-Z]|$)"
)
command_or_dim = rf"(?:[-+]?\s*{command_with_opt_brace_pattern}|{number_points_suffix}|{NUMBER_PATTERN}\s*[-+]?\s*{command_with_opt_brace_pattern}|{NUMBER_PATTERN})"
# Add these compiled patterns at module level
# match $ or % or { or } only if not preceded by \
# Update DELIM_PATTERN to also match double backslashes and opening braces {
DELIM_PATTERN = re.compile(
    r"(?<!\\)(?:\\\\|\$|%|(?:^|[ \t])\{|\s{|{}|\\\^|\\(?![$%&_#{}^~\\]))"
)

DOCUMENTCLASS_PATTERN = re.compile(
    r"\\documentclass\s*%s\s*%s" % (OPTIONAL_BRACE_PATTERN, BRACE_CONTENT_PATTERN),
    re.DOTALL,
)
USEPACKAGE_PATTERN = re.compile(
    r"\\(?:usepackage|RequirePackage)\s*%s\s*%s"
    % (OPTIONAL_BRACE_PATTERN, BRACE_CONTENT_PATTERN),
    re.DOTALL,
)
LOADCLASS_PATTERN = re.compile(
    r"\\LoadClass\s*%s\s*%s" % (OPTIONAL_BRACE_PATTERN, BRACE_CONTENT_PATTERN),
    re.DOTALL,
)

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
    "newline",
    "maketitle",
    "title",
    "author",
    "and",
    "thanks",
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
    "appendix",
    "appendices",
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
