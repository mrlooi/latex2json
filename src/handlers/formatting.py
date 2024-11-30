import re
from collections import OrderedDict
from typing import Callable, Dict, Optional, Tuple
from src.handlers.base import TokenHandler
from src.tex_utils import extract_nested_content


DEFINE_COLOR_PATTERN = re.compile(
    r"""
    \\definecolor\*?        # \definecolor command
    {[^}]*}                # color name in braces
    {[^}]*}  # color model eg RGB, rgb, HTML, gray, cmyk
    {[^}]*}                # color values
    """,
    re.VERBOSE,
)
COLOR_COMMANDS_PATTERN = re.compile(
    r"""
    \\(?:
        color\*?{[^}]*}                      # \color{..}
        |(?:row|column|cell)color\*?{[^}]*}   # \rowcolor, \columncolor, \cellcolor
        |pagecolor\*?{[^}]*}                  # \pagecolor{..}
        |normalcolor                          # \normalcolor
        |color\s*{[^}]*![^}]*}                  # color mixing like \color{red!50!blue}
    )
    """,
    re.VERBOSE,
)

BOX_PATTERN = re.compile(
    r"""
    \\(?:
        parbox(?:\s*\[[^\]]*\])*\s*{[^}]*}\s*{| # \parbox[pos][height][inner-pos]{width}{text}
        makebox(?:\s*\[[^\]]*\])*\s*{| # \makebox[width][pos]
        framebox(?:\s*\[[^\]]*\])*\s*{| # \framebox[width][pos]
        raisebox\s*{[^}]+}(?:\s*\[[^\]]*\])*\s*{| # \raisebox{raise}[height][depth]
        fbox\s*{| # \fbox{text}
        colorbox\s*{[^}]*}\s*{|           # \colorbox{color}{text}
        fcolorbox\s*{[^}]*}\s*{[^}]*}\s*{   # \fcolorbox{border}{bg}{text}
    )
    """,
    re.VERBOSE | re.DOTALL,
)

RAW_PATTERNS = OrderedDict(
    [
        # Comments
        ("comment", r"%([^\n]*)"),
        # pdf options
        ("pdf", r"\\(?:pdfoutput|pdfsuppresswarningpagegroup)\s*=\s*\d+"),
        ("itemsep", r"\\itemsep\s*=\s*-?\d*\.?\d+\w+?\b"),
        # top level commands
        ("documentclass", r"\\documentclass(?:\s*\[([^\]]*)\])?\s*\{([^}]+)\}"),
        (
            "usepackage",
            r"\\(usepackage|RequirePackage)(?:\s*\[([^\]]*)\])?\s*\{([^}]+)\}",
        ),
        # Formatting commands
        ("setup", r"\\hypersetup\s*{"),
        ("make", r"\\(?:maketitle|makeatletter|makeatother)\b"),
        (
            "page",
            r"\\(?:centering|raggedright|raggedleft|allowdisplaybreaks|samepage|FirstPageHeading|LastPageEnding|noindent|par|clearpage|cleardoublepage|newpage|filbreak|linebreak|nopagebreak|pagebreak|hfill|vfill|break|scriptsize|sloppy|flushbottom)\b",
        ),
        (
            "skip",
            r"\\(?:bigskip|medskip|smallskip|abovedisplayskip|belowdisplayskip|abovedisplayshortskip|belowdisplayshortskip)\b",
        ),
        (
            "style",
            r"\\(?:pagestyle|urlstyle|thispagestyle|theoremstyle|bibliographystyle)\s*\{[^}]*\}",
        ),
        ("newstyle", r"\\(?:newpagestyle|renewpagestyle)\s*\{[^}]*\}\s*{"),
        # ("font", r"\\(?:mdseries|bfseries|itshape|slshape|normalfont|ttfamily)\b"),
        # setters
        ("lstset", r"\\lstset\s*{"),
        (
            "newsetlength",
            r"\\(?:newlength\s*\{[^}]*\})|\\setlength\s*(?:\{([^}]+)\}|\\[a-zA-Z]+)\s*\{([^}]+)\}",
        ),
        ("counter", r"\\(?:setcounter\s*\{([^}]+)\}\{([^}]+)\}|value\s*\{([^}]+)\})"),
        # New margin and size commands allowing any characters after the number
        (
            "margins",
            r"\\(?:topmargin|oddsidemargin|evensidemargin|textwidth|linewidth|textheight|footskip|headheight|headsep|marginparsep|marginparwidth|parindent|parskip|vfuzz|hfuzz)\b",
        ),
        # spacing
        (
            "spacing",
            r"\\(?:"
            r"quad|qquad|,|;|"  # \quad, \qquad, \, \;
            r"hspace\*?\s*{([^}]+)}|"  # \hspace{length}
            r"hskip\s*\d*\.?\d+(?:pt|mm|cm|in|em|ex|sp|bp|dd|cc|nd|nc)\b"  # \hskip 10pt
            r")",
        ),
        # number
        ("number", r"\\(?:numberwithin)\s*\{[^}]*\}\s*\{[^}]*\}"),
        # table
        ("newcolumntype", r"\\(?:newcolumntype|renewcolumntype)\s*\{[^}]*\}\s*{"),
        (
            "separators",
            r"\\(?:"
            r"hline|"  # no args
            r"vspace\s*{([^}]+)}|"
            r"cline\s*{([^}]+)}|"  # {n-m}
            r"(?:midrule|toprule|bottomrule)(?:\[\d*[\w-]*\])?|"  # optional [trim]
            r"cmidrule(?:\[([^\]]*)\])?\s*{([^}]+)}|"  # optional [trim] and {n-m}
            r"hdashline(?:\[[\d,\s]*\])?|"  # optional [length,space]
            r"cdashline\s*{([^}]+)}|"  # {n-m}
            r"specialrule\s*{([^}]*)}\s*{([^}]*)}\s*{([^}]*)}|"  # {height}{above}{below}
            r"addlinespace(?:\[([^\]]*)\])?|"  # optional [length]
            r"rule\s*{[^}]*}\s*{[^}]*}|"  # \rule{width}{height}
            r"morecmidrules|"  # no args
            r"fboxsep\s*{([^}]+)}"  # {length}
            r")",
        ),
        ("protect", r"\\protect(?=[\\{]|\s|[^a-zA-Z])"),
        ("addtocontents", r"\\addtocontents\s*\{[^}]*\s*\}\s*\{[^}]*\}"),
        ("backslash", r"\\(?:backslash|textbackslash)\b"),
        ("ensuremath", r"\\ensuremath\s*{"),
    ]
)

# Then compile them into a new dictionary
PATTERNS = OrderedDict(
    (key, re.compile(pattern)) for key, pattern in RAW_PATTERNS.items()
)
PATTERNS["color"] = COLOR_COMMANDS_PATTERN
PATTERNS["definecolor"] = DEFINE_COLOR_PATTERN
PATTERNS["box"] = BOX_PATTERN
# PATTERNS['and'] = re.compile(r'\\and\b', re.IGNORECASE)


class FormattingHandler(TokenHandler):
    def can_handle(self, content: str) -> bool:
        return any(pattern.match(content) for pattern in PATTERNS.values())

    def handle(self, content: str) -> Tuple[Optional[Dict], int]:
        # Try each pattern until we find a match
        for pattern_name, pattern in PATTERNS.items():
            match = pattern.match(content)
            if match:
                if pattern_name == "backslash":
                    return {"type": "text", "content": r"\\"}, match.end()
                elif pattern_name == "spacing":
                    return {"type": "text", "content": " "}, match.end()
                elif pattern_name in ["newcolumntype", "newstyle", "setup", "lstset"]:
                    # extracted nested
                    start_pos = match.end() - 1
                    extracted_content, end_pos = extract_nested_content(
                        content[start_pos:]
                    )
                    return None, start_pos + end_pos
                elif pattern_name == "ensuremath":
                    start_pos = match.end() - 1
                    extracted_content, end_pos = extract_nested_content(
                        content[start_pos:]
                    )
                    return {
                        "type": "equation",
                        "content": extracted_content,
                        "display": "inline",
                    }, start_pos + end_pos
                elif pattern_name == "box":
                    start_pos = match.end() - 1
                    extracted_content, end_pos = extract_nested_content(
                        content[start_pos:]
                    )
                    return {
                        "type": "box",
                        "content": extracted_content
                        + "\n",  # add newline to end of box?
                    }, start_pos + end_pos
                return None, match.end()

        return None, 0


if __name__ == "__main__":
    handler = FormattingHandler()
    print(handler.handle(r"\textbackslash"))
    print(handler.handle(r"\maketitle"))
