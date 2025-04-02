import datetime
import re
from collections import OrderedDict
from typing import Callable, Dict, List, Optional, Tuple
from latex2json.parser.handlers.base import TokenHandler
from latex2json.parser.patterns import (
    NUMBER_PATTERN,
    OPTIONAL_BRACE_PATTERN,
    BRACE_CONTENT_PATTERN,
    number_points_suffix,
)
from latex2json.utils.tex_utils import (
    extract_nested_content,
    extract_nested_content_sequence_blocks,
)
import decimal

COLOR_CELLS_PATTERN = re.compile(
    r"""
    \\(?:
        (?:row|column|cell)color\*?\s*%s\s*{[^}]*}   # \rowcolor, \columncolor, \cellcolor
    )
    """
    % OPTIONAL_BRACE_PATTERN,
    re.VERBOSE,
)

number_regex = NUMBER_PATTERN

declare_pattern_N_blocks = {
    "DeclareFontFamily": 3,
    "DeclareFontShape": 6,
    "DeclareMathAlphabet": 5,
    "DeclareOption": 2,
    "SetMathAlphabet": 6,
    "DeclareSymbolFontAlphabet": 2,
}


RAW_PATTERNS = OrderedDict(
    [
        # Comments
        ("comment", r"(?<!\\)%([^\n]*)"),
        # Class and package setup commands
        (
            "class_setup",
            re.compile(
                r"\\(?:NeedsTeXFormat\s*\{([^}]+)\}|(?:ProvidesClass|ProvidesPackage)\s*%s\s*\[)"
                % BRACE_CONTENT_PATTERN,
                re.DOTALL,
            ),
        ),
        # pdf options
        ("pdf", r"\\(?:pdfoutput|pdfsuppresswarningpagegroup)\s*=\s*\d+"),
        ("pdfinfo", r"\\pdfinfo\s*{"),
        # date
        ("date", r"\\date\s*\{"),
        ("today", r"\\today\b"),
        ("subjclass", r"\\subjclass\s*%s\s*\{[^}]+\}" % OPTIONAL_BRACE_PATTERN),
        # Formatting commands
        ("setup", r"\\(?:hypersetup|captionsetup)%s\s*{" % OPTIONAL_BRACE_PATTERN),
        (
            "make_or_contents",
            r"\\(?:(?:[a-zA-Z@]+)?maketitle|makeatletter|makeatother|tableofcontents|@title)\b",
        ),
        ("addcontentsline", r"\\addcontentsline\s*\{[^}]*\}\s*\{[^}]*\}\s*\{[^}]*\}"),
        ("titlecontents", r"\\titlecontents\s*{"),
        ("contents", r"\\contentspage\b"),
        (
            "page",
            r"\\enlargethispage\s*\{[^}]*\}|\\pagecolor\*?{[^}]*}|\\(?:centering|raggedright|raggedleft|allowdisplaybreaks|samepage|thepage|noindent|par|clearpage|cleardoublepage|nopagebreak|hss|hfill|hfil|vfill|vfil|break|sloppy|flushbottom|flushleft|flushright|flushtop)\b",
        ),
        (
            "pagebreak",
            r"\\(?:pagebreak|filbreak|newpage|allowbreak|goodbreak|medbreak|break)\b|\\linebreak(?:\[\d+\])?",
        ),
        (
            "vskip",
            r"\\vskip\s*(?:" + number_regex + r"\w+\b|-?\\[@a-zA-Z]+|\b)",
        ),
        (
            "penalty",
            r"\\(?:penalty\s*|interfootnotelinepenalty\s*=?\s*)" + number_regex + r"\b",
        ),
        (
            "skip",
            r"\\(?:bigskip|medskip|smallskip|lastskip|unskip|(above|below)(display|caption)(short)?skip)\b",
        ),
        (
            "style",
            r"\\(?:pagestyle|urlstyle|thispagestyle|theoremstyle|bibliographystyle|documentstyle|setcitestyle)\s*\{[^}]*\}",
        ),
        ("print", r"\\printbibliography\b"),
        ("newstyle", r"\\(?:newpagestyle|renewpagestyle)\s*\{[^}]*\}\s*{"),
        # ("font", r"\\(?:mdseries|bfseries|itshape|slshape|normalfont|ttfamily)\b"),
        # setters
        ("lstset", r"\\lstset\s*{"),
        (
            "setlist",
            r"\\setlist\s*%s\s*{" % OPTIONAL_BRACE_PATTERN,
        ),  # Added setlist pattern
        (
            "value",
            r"\\value\s*\{([^}]+)\}",
        ),
        # New margin and size commands allowing any characters after the number
        (
            "margins",
            r"\\(?:rightmargin|leftmargin)\b|"
            + r"\\(?:topmargin|oddsidemargin|evensidemargin|textwidth|textheight|skip|footskip|headheight|headsep|footnotesep|marginparsep|marginparwidth|parindent|parskip|vfuzz|hfuzz|hoffset|voffset)"
            + r"\s*(\=?\s*(?:%s))?" % (number_points_suffix),
        ),
        (
            "lineskip",
            r"\\lineskip\s*%s" % (number_points_suffix)
            + r"|(%s)?\\baselineskip(?:\s*%s)?" % (number_regex, number_points_suffix),
        ),
        # width
        ("width", r"\\(?:linewidth|columnwidth|textwidth|hsize|labelwidth|wd)\b"),
        # spacing
        (
            "spacing",
            r"\\(?:"
            r"quad|qquad|xspace|,|;|:|\!|"  # \quad, \qquad, \, \; \:
            r"hspace\*?\s*{([^}]+)}|"  # \hspace{length}
            r"hskip\s*%s" % (number_points_suffix)  # \hskip 10pt
            + r"|linespread\s*\{[^}]*\}"  # Added \linespread{...}
            r")",
        ),
        (
            "toolset",
            r"\\mathtoolsset\s*%s" % (BRACE_CONTENT_PATTERN),
        ),
        # \kern, which is technically spacing but more like a length between characters. so ignore
        ("kern", r"\\kern\s*%s" % (number_points_suffix)),
        # options
        (
            "options",
            re.compile(
                r"\\(?:ProcessOptions\b|(PassOptionsToPackage|PassOptionsToClass)\s*\{[^}]*\}\s*\{[^}]*\})",
                re.DOTALL,
            ),
        ),
        (
            "declare",
            re.compile(
                r"\\(DeclareFontShape|DeclareSymbolFontAlphabet|DeclareFontFamily|DeclareMathAlphabet|DeclareOption|SetMathAlphabet|DeclareGraphicsExtensions)\*?\s*\{",
                re.DOTALL,
            ),
        ),
        # number
        ("number", r"\\num(?:\[([^\]]*)\])?\s*{([^}]*)}"),
        (
            "linenumbers",
            re.compile(
                r"\\(?:linenumbers\b|linesnumbered\b|numberwithin\s*\{[^}]*\}\s*\{[^}]*\})",
                re.DOTALL | re.IGNORECASE,
            ),
        ),
        (
            "numbering_style",
            re.compile(
                r"(?:\\(?:arabic|roman|alph|fnsymbol)(?:\s*\{[^}]*\}|\b))|\\pagenumbering\s*\{[^}]*\}",
                re.DOTALL,
            ),
        ),
        # separators
        ("itemsep", r"\\itemsep\s*(=\s*)?-?\d*\.?\d+\w+?\b"),
        (
            "table_separators",
            r"\\(?:"
            r"hline\b|"  # no args
            r"center\b|"  # no args
            r"centerline\b|"  # no args
            r"cline\s*{([^}]+)}|"  # {n-m}
            r"topsep\b|parsep\b|partopsep\b|"
            r"labelsep\s*\{?([^\}]*)\}?|"
            + r"(?:midrule|toprule|bottomrule)%s|"
            % (OPTIONAL_BRACE_PATTERN)  # optional [trim]
            + r"cmidrule\s*(?:\(([^)]+)\)\s*)?(?:\[([^\]]*)\]\s*)?{([^}]+)}|"  # optional (lr)[trim] and {n-m}
            r"hdashline(?:\[[\d,\s]*\])?|"  # optional [length,space]
            r"cdashline\s*{([^}]+)}|"  # {n-m}
            r"specialrule\s*{([^}]*)}\s*{([^}]*)}\s*{([^}]*)}|"  # {height}{above}{below}
            r"addlinespace(?:\[([^\]]*)\])?|"  # optional [length]
            r"rule\s*{[^}]*}\s*{[^}]*}|"  # \rule{width}{height}
            r"hrule\b|"
            r"morecmidrules\b|"  # no args
            r"fboxsep\s*{([^}]+)}|"  # {length}
            r"Xhline\s*{([^}]+)}|"  # {length}
            r"tabcolsep\b|"
            r"colrule\b|"
            r"noalign\b|"
            r"endfirsthead\b"
            r")",
        ),
        (
            "rulewidth",
            r"\\(?:arrayrulewidth|heavyrulewidth|overfullrule)(?:\s*=?\s*%s(?:\w+)?)?"
            % number_regex,
        ),
        ("paper", r"\\(?:paperwidth|paperheight)\s*=\s*%s(?:\w+)?" % number_regex),
        ("protect", r"\\protect\\[a-zA-Z]+(?:\s*(?:\[[^\]]*\]|\{[^}]*\})*)?"),
        ("addtocontents", r"\\(?:addtocontents|addtocounter)\s*\{[^}]*\s*\}\s*{"),
        (
            "counters",
            r"\\c@page\b|\\counterwithin\s*\{[^}]*}\s*\{[^}]*\}|\\refstepcounter{[^}]+}|\\@addtoreset\s*\{[^}]*\}\s*\{[^}]*\}",
        ),
        ("add_enumerate_counter", r"\\AddEnumerateCounter\s*\{"),
        ("backslash", r"\\(?:backslash|textbackslash|arraybackslash)\b"),
        ("geometry", r"\\geometry\s*\{"),
        ("ensuremath", r"\\ensuremath\s*{"),
        ("hyphenation", r"\\hyphenation\s*{"),
        # Handle vspace separately
        ("vspace", r"\\vspace\*?\s*{[^}]*}"),
        ("phantom", r"\\(?:hphantom|vphantom|phantom)\s*{"),
        (
            "raise",
            r"\\(?:raise|lower|raisebox)\s*(?:"
            + number_regex
            + r"\w+\b|\{[^}]*\})(?:\s*\{[^}]*\})*",
        ),
        (
            "other",
            re.compile(
                r"\\(?:ignorespaces|relax|repeat|\@tempboxa|box|global|@plus|@minus|null|FloatBarrier|footins|phantomsection)\b",
            ),
        ),
        ("newmdenv", re.compile(r"\\newmdenv\s*(?:\[(.*?)\])?\s*\{(.*?)\}", re.DOTALL)),
        ("pz@", r"(?:%s)?\\[pz]@(?![a-zA-Z@])" % number_regex),
        ("slash", r"\\/"),  # \/ (in latex, this is like an empty space)
        ("@empty", r"\\@empty(?![a-zA-Z@])"),
        (
            "advance",
            r"\\(?:advance|divide|multiply)(?:\\[a-zA-Z@*\d]+)?(?:\s+by)?(?:\s*-)?(?:\s*(?:\\)?[a-zA-Z@*\d]+)?",
        ),
        ("typeout", r"\\typeout\s*{"),
        # other...
        ("physics", r"\\pacs\s*\{(.*?)\}"),
        ("Hy@", r"\\Hy@[a-zA-Z]+\s*{"),
        ("unvbox", r"\\unvbox\s*(?:%s|\\[a-zA-Z@]+\b)" % (number_regex)),
    ]
)

# Then compile them into a new dictionary
PATTERNS = OrderedDict(
    (key, pattern if isinstance(pattern, re.Pattern) else re.compile(pattern))
    for key, pattern in RAW_PATTERNS.items()
)
PATTERNS["color_cells"] = COLOR_CELLS_PATTERN

number_regex_compiled = re.compile(number_regex)


def strip_trailing_number_from_token(token: Dict) -> Dict:
    if not token or not isinstance(token, dict) or token.get("type") != "text":
        return token

    text = token["content"]
    if not text:
        return token

    # If the entire string is a number, clear the content
    if re.match(f"^{number_regex}$", text):
        token["content"] = ""
        return token

    # Find the last non-numeric character
    for i in range(len(text) - 1, -1, -1):
        if not number_regex_compiled.match(text[i:]):
            token["content"] = text[: i + 1]
            break

    return token


class FormattingHandler(TokenHandler):
    @staticmethod
    def format_number(number: str, options: Optional[str] = None) -> str:
        """Format a number according to siunitx-style options.

        Args:
            number: The number to format as a string
            options: Optional string containing formatting options like 'round-precision=1'

        Returns:
            Formatted number as a string
        """
        try:
            if not options:
                return number

            # Parse options
            if "round-precision" in options:
                precision_match = re.search(r"round-precision=(\d+)", options)
                if precision_match:
                    precision = int(precision_match.group(1))
                    decimal_num = decimal.Decimal(number)
                    quantizer = decimal.Decimal("0." + "0" * precision)
                    rounded = decimal_num.quantize(
                        quantizer, rounding=decimal.ROUND_HALF_UP
                    )
                    return str(rounded)

            return number

        except (ValueError, decimal.InvalidOperation, AttributeError) as e:
            return number

    def can_handle(self, content: str) -> bool:
        return any(pattern.match(content) for pattern in PATTERNS.values())

    def handle(
        self,
        content: str,
        prev_token: Optional[Dict] = None,
        exclude_patterns: Optional[List[str]] = None,
    ) -> Tuple[Optional[Dict], int]:
        # Try each pattern until we find a match
        for pattern_name, pattern in PATTERNS.items():
            if exclude_patterns and pattern_name in exclude_patterns:
                continue
            match = pattern.match(content)
            if match:
                if pattern_name == "comment":
                    return None, match.end()
                elif pattern_name == "number":
                    options = match.group(1)
                    number = match.group(2)

                    formatted_number = self.format_number(number, options)
                    return {"type": "text", "content": formatted_number}, match.end()
                elif pattern_name == "pz@" or match.group(0).startswith(
                    r"\baselineskip"
                ):
                    if prev_token:
                        # check for number\pz@ e.g. 2\pz@ in previous token
                        # since \pz@ could be parsed after the prior number was extracted in previous parsing loop
                        # then strip out the trailing number if it exists
                        strip_trailing_number_from_token(prev_token)
                    return None, match.end()
                elif pattern_name == "backslash":
                    return {"type": "text", "content": r"\\"}, match.end()
                elif pattern_name == "spacing":
                    if match.group(0) == r"\!":
                        return None, match.end()
                    return {"type": "text", "content": " "}, match.end()
                elif pattern_name == "add_enumerate_counter":
                    start_pos = match.end() - 1
                    extracted_content, end_pos = extract_nested_content_sequence_blocks(
                        content[start_pos:], max_blocks=3
                    )
                    return None, start_pos + end_pos
                elif pattern_name in [
                    "newcolumntype",
                    "newstyle",
                    "setup",
                    "lstset",
                    "setlist",
                    "addtocontents",
                    "geometry",
                    "hyphenation",
                    "typeout",
                    "pdfinfo",
                    "Hy@",
                ]:
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
                elif pattern_name == "date":
                    start_pos = match.end() - 1
                    extracted_content, end_pos = extract_nested_content(
                        content[start_pos:]
                    )
                    return {
                        "type": "date",
                        "content": extracted_content,
                    }, start_pos + end_pos
                elif pattern_name == "today":
                    return {
                        "type": "date",
                        "content": datetime.datetime.now().strftime("%Y-%m-%d"),
                    }, match.end()
                elif pattern_name == "titlecontents":
                    return self._handle_titlecontents(content, match)
                elif pattern_name in ["vspace", "pagebreak"]:
                    return {"type": "text", "content": "\n"}, match.end()
                elif pattern_name == "options":
                    return self._handle_options(content, match)
                elif pattern_name == "declare":
                    return self._handle_declare(content, match)
                elif pattern_name == "class_setup":
                    if match.group(0).endswith("["):
                        start_pos = match.end() - 1
                        extracted_content, end_pos = extract_nested_content(
                            content[start_pos:], "[", "]"
                        )
                        return None, start_pos + end_pos
                    return None, match.end()
                elif pattern_name == "phantom":
                    start_pos = match.end() - 1
                    extracted_content, end_pos = extract_nested_content(
                        content[start_pos:]
                    )
                    # Check if it's hphantom or vphantom
                    if match.group(0).startswith("\\hphantom"):
                        # Horizontal phantom - create spaces matching content width
                        return {
                            "type": "text",
                            "content": " " * len(extracted_content),
                        }, start_pos + end_pos
                    else:  # vphantom
                        # Vertical phantom - create line break without horizontal space
                        return {
                            "type": "text",
                            "content": "\n",
                        }, start_pos + end_pos
                return None, match.end()

        return None, 0

    def _handle_titlecontents(
        self, content: str, match: re.Match
    ) -> Tuple[Optional[Dict], int]:
        start_pos = match.end() - 1
        _, end_pos = extract_nested_content_sequence_blocks(
            content[start_pos:], "{", "}", max_blocks=1
        )
        start_pos += end_pos
        _, end_pos = extract_nested_content_sequence_blocks(
            content[start_pos:], "[", "]", max_blocks=1
        )
        start_pos += end_pos
        _, end_pos = extract_nested_content_sequence_blocks(
            content[start_pos:], "{", "}", max_blocks=4
        )
        # final optional [] block
        start_pos += end_pos
        _, end_pos = extract_nested_content_sequence_blocks(
            content[start_pos:], "[", "]", max_blocks=1
        )
        start_pos += end_pos
        return None, start_pos

    def _handle_declare(
        self, content: str, match: re.Match
    ) -> Tuple[Optional[Dict], int]:
        cmd = match.group(1)
        start_pos = match.end() - 1
        N_blocks = declare_pattern_N_blocks.get(cmd, 1)
        blocks, end_pos = extract_nested_content_sequence_blocks(
            content[start_pos:], "{", "}", max_blocks=N_blocks
        )
        return None, start_pos + end_pos

    def _handle_options(
        self, content: str, match: re.Match
    ) -> Tuple[Optional[Dict], int]:
        out = match.group(0)
        if out.endswith("{"):
            start_pos = match.end() - 1
            _, end_pos = extract_nested_content(content[start_pos:])

            end_pos += start_pos
            return None, end_pos
        return None, match.end()


if __name__ == "__main__":
    handler = FormattingHandler()
    # print(handler.handle(r"\textbackslash"))
    # print(handler.handle(r"\maketitle"))

    print(
        strip_trailing_number_from_token(
            {"type": "text", "content": "1234567890abC F33"}
        )
    )
