import re
from typing import Callable, Dict, Optional, Tuple
from src.handlers.base import TokenHandler
from src.patterns import BRACE_CONTENT_PATTERN
from src.tex_utils import extract_nested_content, extract_nested_content_pattern

POST_NEW_COMMAND_PATTERN_STR = (
    r"\*?\s*(?:{\\([^}]+)}|\\([^\s{[]+))(?:\s*\[(\d+)\])?((?:\s*\[[^]]*\])*)\s*{"
)

DEF_COMMAND_PREFIX = r"(?:\\long)?\\(?:e|g)?def\s*\\"
LET_COMMAND_PREFIX = r"\\(?:future)?let\s*\\"

DEF_COMMAND_PATTERN = re.compile(
    r"%s([^\s{#]+)(((?:#\d+|[^{])*)\s*{)" % (DEF_COMMAND_PREFIX), re.DOTALL
)
LET_COMMAND_PATTERN = re.compile(
    r"%s([^\s{\\]+)\s*(=.*|\\[^\s{]+)" % (LET_COMMAND_PREFIX), re.DOTALL
)

EXPAND_PATTERN = re.compile(r"\\(?:expandafter|noexpand)(?![a-zA-Z])")
START_CSNAME_PATTERN = re.compile(r"\\csname(?![a-zA-Z])")
END_CSNAME_PATTERN = re.compile(r"\\endcsname(?![a-zA-Z])")

# Compile patterns for definition commands
PATTERNS = {
    # Matches newcommand/renewcommand, supports both {\commandname} and \commandname syntax
    "newcommand": re.compile(
        r"\\(?:new|renew|provide)command" + POST_NEW_COMMAND_PATTERN_STR, re.DOTALL
    ),
    "let": re.compile(LET_COMMAND_PREFIX),
    "declaremathoperator": re.compile(
        r"\\DeclareMathOperator" + POST_NEW_COMMAND_PATTERN_STR, re.DOTALL
    ),  # for math mode
    "declarerobustcommand": re.compile(
        r"\\DeclareRobustCommand" + POST_NEW_COMMAND_PATTERN_STR, re.DOTALL
    ),
    # Matches \def commands - always with backslash before command name
    "def": re.compile(DEF_COMMAND_PREFIX),
    # Matches newtheorem with all its optional arguments
    "newtheorem": re.compile(
        r"\\newtheorem{([^}]*)}(?:\[([^]]*)\])?{([^}]*)}(?:\[([^]]*)\])?", re.DOTALL
    ),
    "crefname": re.compile(r"\\crefname{([^}]*)}{([^}]*)}{([^}]*)}", re.DOTALL),
    "newif": re.compile(r"\\(?:re)?newif\s*\\if([^\s{\\]+)", re.DOTALL),
    "newlength": re.compile(
        r"\\(?:re)?newlength\s*" + BRACE_CONTENT_PATTERN, re.DOTALL
    ),
    "setlength": re.compile(
        r"\\setlength\s*%s\s*%s" % (BRACE_CONTENT_PATTERN, BRACE_CONTENT_PATTERN),
        re.DOTALL,
    ),
    "newcounter": re.compile(
        r"\\(?:re)?newcounter\s*" + BRACE_CONTENT_PATTERN, re.DOTALL
    ),
    "newother": re.compile(
        r"\\(?:re)?new(?:count|box|dimen|skip|muskip)\s*\\([^\s{[]+)"
    ),
    "setcounter": re.compile(
        r"\\setcounter\s*%s\s*%s" % (BRACE_CONTENT_PATTERN, BRACE_CONTENT_PATTERN),
        re.DOTALL,
    ),
    "expandafter": EXPAND_PATTERN,
}


def extract_and_concat_nested_csname(content: str) -> Tuple[str, int]:
    match = START_CSNAME_PATTERN.match(content)
    if match:
        _, next_end_pos, inner = extract_nested_content_pattern(
            content, START_CSNAME_PATTERN, END_CSNAME_PATTERN
        )
        if next_end_pos == -1:
            return "", -1

        # Remove the start and end patterns
        inner = START_CSNAME_PATTERN.sub("", inner)
        inner = END_CSNAME_PATTERN.sub("", inner)
        inner = EXPAND_PATTERN.sub("", inner)

        return inner, next_end_pos
    return "", -1


class NewDefinitionHandler(TokenHandler):

    def can_handle(self, content: str) -> bool:
        """Check if the content contains any definition commands"""
        return any(pattern.match(content) for pattern in PATTERNS.values())

    def handle(
        self, content: str, prev_token: Optional[Dict] = None
    ) -> Tuple[Optional[Dict], int]:
        """Handle definition commands and return appropriate token with definition details"""
        for pattern_name, pattern in PATTERNS.items():
            match = pattern.match(content)
            if match:
                # declaremathoperator is for math mde
                if pattern_name == "newcommand" or pattern_name.startswith("declare"):
                    return self._handle_newcommand(content, match)
                elif pattern_name == "let":
                    return self._handle_def_prefix(
                        content,
                        match,
                        LET_COMMAND_PATTERN,
                        self._handle_let,
                        False,
                        max_csname_blocks=2,
                    )
                elif pattern_name == "def":
                    return self._handle_def_prefix(
                        content,
                        match,
                        DEF_COMMAND_PATTERN,
                        self._handle_def,
                        max_csname_blocks=1,
                    )
                elif pattern_name == "newtheorem":
                    return self._handle_newtheorem(match)
                elif pattern_name == "crefname":
                    return self._handle_crefname(match)
                elif pattern_name == "newif":
                    return self._handle_newif(match)
                elif pattern_name == "newlength" or pattern_name == "setlength":
                    return self._handle_newlength(match)
                elif pattern_name == "newcounter" or pattern_name == "setcounter":
                    return self._handle_newcounter(match)
                elif pattern_name == "newother":
                    return self._handle_newother(match)
                elif pattern_name == "expandafter":
                    next_pos = match.end()
                    token, end_pos = self.handle(content[next_pos:])
                    return token, next_pos + end_pos
                else:
                    return None, match.end()

        return None, 0

    def _handle_newother(self, match) -> Tuple[Optional[Dict], int]:
        r"""Handle \newother definitions"""
        var_name = match.group(1).strip()
        token = {"type": "newother", "name": var_name}
        return token, match.end()

    def _handle_newif(self, match) -> Tuple[Optional[Dict], int]:
        r"""Handle \newif definitions"""
        var_name = match.group(1)
        token = {"type": "newif", "name": var_name}
        return token, match.end()

    def _handle_newlength(self, match) -> Tuple[Optional[Dict], int]:
        r"""Handle \newlength definitions"""
        var_name = match.group(1).strip()
        var_name = var_name.replace("\\", "")
        token = {"type": "newlength", "name": var_name}
        return token, match.end()

    def _handle_newcounter(self, match) -> Tuple[Optional[Dict], int]:
        r"""Handle \newcounter definitions"""
        var_name = match.group(1).strip()
        token = {"type": "newcounter", "name": var_name}
        return token, match.end()

    def _handle_crefname(self, match) -> Tuple[Optional[Dict], int]:
        r"""Handle \crefname definitions"""
        token = {
            "type": "crefname",
            "name": match.group(1),
            "singular": match.group(2),
            "plural": match.group(3),
        }
        return token, match.end()

    def _handle_let(self, content: str, match) -> Tuple[Optional[Dict], int]:
        name = match.group(1).strip()
        content = match.group(2).strip()
        # Remove optional equals sign if present
        if content.startswith("="):
            content = content[1:]
        elif name.endswith("="):
            name = name[:-1]
        token = {
            "type": "newcommand",
            "name": name,
            "content": content,
            "num_args": 0,
            "defaults": [],
            "usage_pattern": r"\\" + name + r"(?![a-zA-Z@])",
        }
        return token, match.end()

    def _handle_newcommand(self, content: str, match) -> Tuple[Optional[Dict], int]:
        """Handle \newcommand and \renewcommand definitions"""
        start_pos = match.end()
        definition, end_pos = extract_nested_content(
            content[start_pos - 1 :]
        )  # -1 to go back {
        if definition is None:
            return None, start_pos

        # Get command name from either group 1 (with braces) or group 2 (without braces)
        cmd_name = match.group(1) or match.group(2)
        if cmd_name.startswith(
            "\\"
        ):  # Handle case where command name starts with backslash
            cmd_name = cmd_name[1:]

        # Add number of arguments if specified
        num_args = 0
        if match.group(3):
            num_args = int(match.group(3))

        # Add default values if present
        defaults = []
        if match.group(4):
            for default in re.finditer(r"\[(.*?)\]", match.group(4)):
                defaults.append(default.group(1))

        pattern = r"\\" + re.escape(cmd_name) + r"(?![a-zA-Z])"

        token = {
            "type": "newcommand",
            "name": cmd_name,
            "content": definition,
            "num_args": num_args,
            "defaults": defaults,
            "usage_pattern": pattern,
        }

        return token, start_pos + end_pos - 1

    def _handle_newtheorem(self, match) -> Tuple[Optional[Dict], int]:
        """Handle \newtheorem definitions"""
        token = {"type": "newtheorem", "name": match.group(1), "title": match.group(3)}

        # Handle optional counter specification
        if match.group(2):
            token["counter"] = match.group(2)

        # Handle optional numbering within
        if match.group(4):
            token["within"] = match.group(4)

        return token, match.end()

    def _handle_def_prefix(
        self,
        content: str,
        match: re.Match,
        full_pattern: re.Pattern,
        handler: Callable[[str, re.Match], Tuple[Optional[Dict], int]],
        add_usage_suffix=True,
        max_csname_blocks=1,
    ) -> Tuple[Optional[Dict], int]:
        prefix = match.group(0)
        if prefix:
            # remove last backslash
            prefix = prefix[:-1]
            start_pos = match.end() - 1

            expand_after_pattern = re.compile(r"\s*" + EXPAND_PATTERN.pattern)

            inner_csnames = []
            while start_pos < len(content):

                # extract inner inside \csname <INNER> \endcsname
                if len(inner_csnames) < max_csname_blocks:
                    # strip out all expandafter patterns
                    _match = expand_after_pattern.match(content[start_pos:])
                    if _match:
                        start_pos += _match.end()
                        continue

                    inner, next_pos = extract_and_concat_nested_csname(
                        content[start_pos:]
                    )
                    if next_pos != -1:
                        start_pos += next_pos
                        inner_csnames.append(inner)
                        continue

                cmd_str = "\\"
                if inner_csnames:
                    cmd_str = ""
                    for inner in inner_csnames:
                        cmd_str += "\\" + inner.replace(" ", "")

                search_prefix = prefix + cmd_str
                if content[start_pos] == "\\":
                    start_pos += 1
                search_text = search_prefix + content[start_pos:]
                full_match = full_pattern.match(search_text)
                if full_match:
                    token, end_pos = handler(search_text, full_match)
                    if token and inner_csnames:  # allow csname regex compile
                        first_inner = inner_csnames[0]
                        # Partition the usage_pattern to remove up to and including cmd_str
                        usage_suffix = r"(?![a-zA-Z@])"
                        if add_usage_suffix:
                            _, _, usage_suffix = token["usage_pattern"].partition(
                                "\\" + first_inner.replace(" ", "")
                            )
                        inner_csname_regex = (
                            r"\\csname" + first_inner + r"\\endcsname" + usage_suffix
                        )
                        token["usage_pattern"] = (
                            token["usage_pattern"] + "|" + inner_csname_regex
                        )
                    return token, start_pos + end_pos - len(search_prefix)

                break

        return None, 0

    # parse \def\command(?#1#2){definition}
    # where #1, #2 are optional parameter markers
    # we need to make regex for usage pattern
    # if it is the last arg, and not wrapped in {}, then it is a delimiter
    # otherwise, it is a parameter
    def _handle_def(self, content: str, match) -> Tuple[Optional[Dict], int]:
        r"""Handle \def command definitions"""
        start_pos = match.end()
        definition, end_pos = extract_nested_content(content[start_pos - 1 :])
        if definition is None:
            return None, start_pos

        is_edef = r"\edef" in content[: match.start(1) or match.start(2)]

        # Get command name (will be clean now, without parameters)
        cmd_name = match.group(1) or match.group(2)
        if cmd_name.startswith("\\"):
            cmd_name = cmd_name[1:]

        # Get parameter pattern (now properly separated)
        param_pattern = match.group(3).strip() if match.group(3) else ""

        usage_pattern = rf"{cmd_name}{param_pattern}"

        # Don't escape the entire pattern, instead handle delimiters and parameters separately
        parts = []
        current_pos = 0
        param_count = 0
        for param in re.finditer(r"#(\d+)", usage_pattern):
            # Add everything before the parameter as escaped text
            before_param = usage_pattern[current_pos : param.start()]
            if before_param:
                parts.append(re.escape(before_param))

            # Add the parameter pattern to capture delimiters and parameters e.g. {xxx} or x
            # e.g. \def\foo#1{bar #1} \foo{xxx} will match 'xxx' arg, \foo xaaa will match 'x' arg
            # Update regex to handle escaped braces and normal braces
            parts.append(r"\s*(?:\{((?:[^{}]|\\\{|\\\}|{[^{}]*})*)\}|([^\}]+?))")

            current_pos = param.end()
            param_count += 1

        # Add any remaining text after the last parameter
        if current_pos < len(usage_pattern):
            parts.append(re.escape(usage_pattern[current_pos:]))

        parts = "".join(parts)
        # Add check at the very end to prevent partial matches (e.g., \foo matching \foobar)
        usage_pattern = r"\\" + parts + r"(?![a-zA-Z@])"

        token = {
            "type": "def",
            "name": cmd_name,
            "content": definition,
            "num_args": param_count,
            "usage_pattern": usage_pattern,
            "is_edef": is_edef,
        }

        return token, start_pos + end_pos - 1


if __name__ == "__main__":
    handler = NewDefinitionHandler()

    def clean_groups(match):
        """Remove None values from regex match groups"""
        if match:
            return tuple(g for g in match.groups() if g is not None)
        return tuple()

    def check_usage(text, search):
        print("Checking", text, "with SEARCH:   ", search)
        token, end_pos = handler.handle(text)
        if token:
            if token["usage_pattern"]:
                regex = re.compile(token["usage_pattern"])
                match = regex.match(search)
                print(token["usage_pattern"], token["content"])
                if match:
                    print(clean_groups(match))
        print()

    text = r"""
    \let\arXiv\arxiv
    \def\doi
    """.strip()

    print(handler.handle(text))
