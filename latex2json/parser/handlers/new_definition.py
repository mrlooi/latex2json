import re
from typing import Callable, Dict, List, Optional, Tuple
from latex2json.parser.handlers.base import TokenHandler
from latex2json.parser.patterns import (
    BRACE_CONTENT_PATTERN,
    command_pattern,
    command_with_opt_brace_pattern,
)
from latex2json.utils.tex_utils import (
    extract_nested_content,
    extract_nested_content_pattern,
    extract_nested_content_sequence_blocks,
)


POST_NEW_COMMAND_PATTERN_STR = (
    r"\*?\s*(?:{%s}|%s)(?:\s*\[(\d+)\])?((?:\s*\[[^]]*\])*)\s*{"
    % (command_pattern, command_pattern)
)

DEF_COMMAND_PREFIX = r"(?:\\long)?\\(?:e|g|x)?def\s*\\"
LET_COMMAND_PREFIX = r"\\(?:future)?let\s*\\"

DEF_COMMAND_PATTERN = re.compile(
    r"%s([^\s{#]+)(((?:#\d+|[^{])*)\s*{)" % (DEF_COMMAND_PREFIX), re.DOTALL
)
LET_COMMAND_PATTERN = re.compile(
    r"%s([^\s{\\]+)\s*(=.*|\\[^\s{]+)" % (LET_COMMAND_PREFIX), re.DOTALL
)

EXPAND_PATTERN = re.compile(r"\\(?:expandafter|noexpand)(?:\w+)?(?![a-zA-Z])")
START_CSNAME_PATTERN = re.compile(r"\\csname(?![a-zA-Z])")
END_CSNAME_PATTERN = re.compile(r"\\endcsname(?![a-zA-Z])")


declare_pattern_N_blocks = {
    # "DeclareFontFamily": 3,
    # "DeclareFontShape": 6,
    # "DeclareOption": 2,
    # "SetMathAlphabet": 6,
    # both of the below create new macros, we handle this in newdef
    "DeclareMathAlphabet": 5,
    "DeclareSymbolFontAlphabet": 2,
}

# Compile patterns for definition commands
PATTERNS = {
    # Matches newcommand/renewcommand, supports both {\commandname} and \commandname syntax
    "newcommand": re.compile(
        r"\\(?:new|renew|provide)command" + POST_NEW_COMMAND_PATTERN_STR, re.DOTALL
    ),
    "let": re.compile(LET_COMMAND_PREFIX),
    # declares
    "declarerobustcommand": re.compile(
        r"\\DeclareRobustCommand" + POST_NEW_COMMAND_PATTERN_STR, re.DOTALL
    ),
    "declarepairedelimiter": re.compile(
        r"\\DeclarePairedDelimiter\s*(?:{\\([^\s{}]+)}|\\([^\s{]+))\s*{",
        re.DOTALL,
    ),
    # declares for math mode
    "declaremathoperator": re.compile(
        r"\\DeclareMathOperator" + POST_NEW_COMMAND_PATTERN_STR, re.DOTALL
    ),
    "declarealphabets": re.compile(
        r"\\(DeclareMathAlphabet|DeclareSymbolFontAlphabet)\s*{",
        re.DOTALL,
    ),
    # Matches \def commands - always with backslash before command name
    "def": re.compile(DEF_COMMAND_PREFIX),
    "@namedef": re.compile(r"\\@namedef\s*{([^}]*)}"),
    # Matches newtheorem with all its optional arguments
    "newtheorem": re.compile(
        r"\\newtheorem\*?{([^}]*)}(?:\[([^]]*)\])?{([^}]*)}(?:\[([^]]*)\])?", re.DOTALL
    ),
    "newtheoremstyle": re.compile(r"\\newtheoremstyle\*?{", re.DOTALL),
    "crefname": re.compile(r"\\[cC]refname{([^}]*)}{([^}]*)}(?:{([^}]*)})?", re.DOTALL),
    "newtoks": re.compile(
        r"\\newtoks\s*(%s)" % (command_with_opt_brace_pattern), re.DOTALL
    ),
    "newif": re.compile(r"\\(?:re)?newif\s*\\if([^\s{\\]+)", re.DOTALL),
    "newboolean": re.compile(
        r"\\(?:re)?newboolean\s*" + BRACE_CONTENT_PATTERN, re.DOTALL
    ),
    "newlength": re.compile(
        r"\\((?:re)?newlength)\s*" + command_with_opt_brace_pattern, re.DOTALL
    ),
    "setlength": re.compile(
        r"\\(setlength|addtolength|settoheight|settodepth|settowidth)\s*%s\s*{"
        % (command_with_opt_brace_pattern),
        re.DOTALL,
    ),
    "newcounter": re.compile(
        r"\\(?:(?:re)?newcounter|stepcounter)\s*" + BRACE_CONTENT_PATTERN, re.DOTALL
    ),
    "newother": re.compile(r"\\(?:re)?new(?:count|dimen|skip|muskip)\s*\\([^\s{[]+)"),
    "newcolumntype": re.compile(
        r"\\(?:newcolumntype|renewcolumntype)\s*\{[^}]*\}(?:\s*\[\d+\])?\s*{", re.DOTALL
    ),
    "newfam": re.compile(r"\\newfam\s*\\([^\s{[]+)"),
    "setcounter": re.compile(
        r"\\setcounter\s*%s\s*%s" % (BRACE_CONTENT_PATTERN, BRACE_CONTENT_PATTERN),
        re.DOTALL,
    ),
    "floatname": re.compile(r"\\floatname{([^}]*)}{([^}]*)}"),
    "expandafter": EXPAND_PATTERN,
    "endcsname": END_CSNAME_PATTERN,  # for trailing \endcsname?
    # color/font
    "definecolor": re.compile(r"\\definecolor\s*{"),
    "font": re.compile(
        r"\\font\s*\\([^\s=]+)\s*=\s*([^\s]+)(?:\s+at\s+(\d+(?:\.\d+)?)(pt|cm|mm|in|ex|em|bp|dd|pc|sp))?"
    ),
}

USAGE_SUFFIX = r"(?![a-zA-Z@])"


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
                if pattern_name == "declarepairedelimiter":
                    return self._handle_paired_delimiter(content, match)
                elif pattern_name == "declarealphabets":
                    return self._handle_declare_alphabets(content, match)
                elif pattern_name == "declaremathoperator":
                    token, end_pos = self._handle_newcommand(content, match)
                    if token:
                        token["math_mode_only"] = True
                    return token, end_pos
                elif pattern_name == "newcommand" or pattern_name.startswith("declare"):
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
                elif pattern_name == "@namedef":
                    return self._handle_namedef(content, match)
                elif pattern_name == "definecolor":
                    return self._handle_definecolor(content, match)
                elif pattern_name == "font":
                    return self._handle_font(match)
                elif pattern_name == "newtoks":
                    return self._handle_newtoks(match)
                elif pattern_name == "newtheorem":
                    return self._handle_newtheorem(match)
                elif pattern_name == "newtheoremstyle":
                    return self._handle_newtheoremstyle(content, match)
                elif pattern_name == "crefname":
                    return self._handle_crefname(match)
                elif pattern_name == "newif":
                    return self._handle_newif(match)
                elif pattern_name == "newlength":
                    return self._handle_newlength(match)
                elif pattern_name == "setlength":
                    return self._handle_setlength(content, match)
                elif pattern_name == "newfam":
                    return self._handle_newfam(match)
                elif pattern_name == "newcounter" or pattern_name == "setcounter":
                    return self._handle_newcounter(match)
                elif pattern_name == "newother":
                    return self._handle_newother(match)
                elif pattern_name == "floatname":
                    return {
                        "type": "floatname",
                        "name": match.group(1),
                        "title": match.group(2),
                    }, match.end()
                elif pattern_name in ["expandafter", "endcsname"]:
                    next_pos = match.end()
                    token, end_pos = self.handle(content[next_pos:])
                    return token, next_pos + end_pos
                elif pattern_name == "newcolumntype":
                    return self._handle_newcolumntype(content, match)
                else:
                    return None, match.end()

        return None, 0

    def _handle_declare_alphabets(
        self, content: str, match
    ) -> Tuple[Optional[Dict], int]:
        r"""Handle \DeclareMathAlphabet and \DeclareSymbolFontAlphabet definitions"""
        declare_type = match.group(1)
        start_pos = match.end() - 1
        N_blocks = declare_pattern_N_blocks.get(declare_type, 1)
        blocks, end_pos = extract_nested_content_sequence_blocks(
            content[start_pos:], "{", "}", max_blocks=N_blocks
        )
        end_pos += start_pos
        if len(blocks) < 1:
            return None, end_pos
        cmd = blocks[0]
        token = {
            "type": "newcommand",
            "name": cmd.strip("\\"),
            "content": "#1",
            "math_mode_only": True,
            "num_args": 1,
            "defaults": [],
            "usage_pattern": re.escape(cmd) + USAGE_SUFFIX,
        }
        return token, end_pos

    def _handle_newcolumntype(self, content: str, match) -> Tuple[Optional[Dict], int]:
        r"""Handle \newcolumntype definitions"""
        start_pos = match.end() - 1
        _, end_pos = extract_nested_content(content[start_pos:])
        end_pos += start_pos
        # token = {"type": "newcolumntype", "name": match.group(1).strip()}
        return None, end_pos

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

    def _parse_varname_from_brace_or_backslash(
        self, var_name: str
    ) -> Tuple[Optional[str], int]:
        if var_name.startswith("{"):
            _var_name, _ = extract_nested_content(var_name)
            if _var_name:
                var_name = _var_name.strip()
        if var_name.startswith("\\"):
            var_name = var_name[1:]
        if "{" in var_name:
            var_name = var_name[: var_name.find("{")].strip()
        return var_name

    def _handle_newlength(self, match: re.Match) -> Tuple[Optional[Dict], int]:
        r"""Handle \newlength definitions"""
        s = match.group(0)
        s = s[match.end(1) :]
        var_name = self._parse_varname_from_brace_or_backslash(s)
        if not var_name:
            return None, match.end()
        token = {"type": "newlength", "name": var_name}
        return token, match.end()

    def _handle_setlength(
        self, content: str, match: re.Match
    ) -> Tuple[Optional[Dict], int]:
        r"""Handle \newlength definitions"""
        s = match.group(0)
        s = s[match.end(1) : -1]
        var_name = self._parse_varname_from_brace_or_backslash(s)
        start_pos = match.end(0) - 1
        len_def, end_pos = extract_nested_content(content[start_pos:])
        end_pos += start_pos
        if not var_name:
            return None, end_pos
        token = {"type": "newlength", "name": var_name}
        return token, end_pos

    def _handle_newtoks(self, match) -> Tuple[Optional[Dict], int]:
        r"""Handle \newtoks definitions"""
        var_name = self._parse_varname_from_brace_or_backslash(match.group(1).strip())
        if not var_name:
            return None, match.end()
        token = {"type": "newtoks", "name": var_name}
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
            "plural": match.group(3) or "",
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

        # HACK: treat futurelet as newcommand?
        if match.group(0).startswith("\\futurelet"):
            token = {
                "type": "newcommand",
                "name": name,
                "content": content,
                "num_args": 0,
                "defaults": [],
                "usage_pattern": r"\\" + name + USAGE_SUFFIX,
            }
        else:
            token = {
                "type": "let",
                "name": name,
                "content": content,
                "usage_pattern": r"\\" + name + USAGE_SUFFIX,
            }
        return token, match.end()

    def _handle_newcommand(self, content: str, match) -> Tuple[Optional[Dict], int]:
        r"""Handle \newcommand and \renewcommand definitions"""
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

        # Don't add negative lookahead for commands ending in special chars
        needs_lookahead = cmd_name[-1].isalnum()
        postfix = USAGE_SUFFIX if needs_lookahead else ""
        pattern = r"\\" + re.escape(cmd_name) + postfix

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

    def _handle_newtheoremstyle(
        self, content: str, match
    ) -> Tuple[Optional[Dict], int]:
        start_pos = match.end() - 1
        blocks, end_pos = extract_nested_content_sequence_blocks(
            content[start_pos:], "{", "}", max_blocks=9
        )
        end_pos += start_pos
        return None, end_pos

    def _handle_namedef(self, content: str, match) -> Tuple[Optional[Dict], int]:
        r"""Handle \@namedef definitions"""
        end_pos = match.end()
        # convert to \def format and add csname to also match both cases
        search_prefix = r"\def\csname " + match.group(1) + r" \endcsname "
        search_text = search_prefix + content[end_pos:]
        # run matching exactly same as \def
        match = re.match(DEF_COMMAND_PREFIX, search_text)
        if match:
            token, total_pos = self._handle_def_prefix(
                search_text,
                match,
                DEF_COMMAND_PATTERN,
                self._handle_def,
                max_csname_blocks=1,
            )
            return token, end_pos + total_pos - len(search_prefix)
        return None, end_pos

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
                        usage_suffix = USAGE_SUFFIX
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
                    total_pos = start_pos + end_pos - len(search_prefix)
                    return token, total_pos

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

        parts, param_count = self._extract_def_pattern_parts(
            rf"{cmd_name}{param_pattern}"
        )
        usage_pattern = r"\\" + "".join(parts)

        token = {
            "type": "def",
            "name": cmd_name,
            "content": definition,
            "num_args": param_count,
            "usage_pattern": usage_pattern,
            "is_edef": is_edef,
        }

        return token, start_pos + end_pos - 1

    def _extract_def_pattern_parts(self, pattern: str) -> Tuple[List[str], int]:
        # Don't escape the entire pattern, instead handle delimiters and parameters separately
        parts = []
        param_count = 0

        arg_start = re.search(r"#(\d+)", pattern)
        if arg_start:
            start_pos = arg_start.start()
            # first, we split the pattern into pre_arg and args
            pre_arg = pattern[:start_pos]

            parts.append(re.escape(pre_arg))
            # if last char is alpha or @, add negative lookahead
            # this is to avoid matching e.g. \def\foo#1{bar #1} with \fooa \foob \fooxyz etc
            if pre_arg[-1].isalpha() or pre_arg[-1] == "@":
                parts.append(USAGE_SUFFIX)

            # then we handle the args #1 ... #2 etc
            args = pattern[start_pos:]

            # Add the args pattern to capture delimiters and args e.g. {xxx} or x
            # e.g. \def\foo#1{bar #1} \foo{xxx} will match 'xxx' arg, \foo xaaa will match 'x' arg
            # Update regex to handle escaped braces and normal braces
            args_part_pattern = r"\s*(?:\{((?:[^{}]|\\\{|\\\}|{[^{}]*})*)\}|([^\}]+?))"

            current_pos = 0
            for param in re.finditer(r"#(\d+)", args):
                # Add everything before the parameter as escaped text
                before_param = args[current_pos : param.start()]
                if before_param:
                    parts.append(re.escape(before_param))

                parts.append(args_part_pattern)

                current_pos = param.end()
                param_count += 1

            # Add any remaining text after the last parameter
            if current_pos < len(args):
                parts.append(re.escape(args[current_pos:]))
        else:
            parts.append(re.escape(pattern) + USAGE_SUFFIX)

        return parts, param_count

    def _handle_paired_delimiter(
        self, content: str, match
    ) -> Tuple[Optional[Dict], int]:
        r"""Handle \DeclarePairedDelimiter definitions"""
        cmd_name = match.group(1) or match.group(2)
        start_pos = match.end() - 1  # -1 to go back {
        blocks, end_pos = extract_nested_content_sequence_blocks(
            content[start_pos:], "{", "}", max_blocks=2
        )
        if len(blocks) != 2:
            return None, start_pos
        left_delim = blocks[0]
        right_delim = blocks[1]

        token = {
            "type": "paired_delimiter",
            "name": cmd_name,
            "left_delim": left_delim,
            "right_delim": right_delim,
        }

        return token, start_pos + end_pos

    def _handle_definecolor(self, content: str, match) -> Tuple[Optional[Dict], int]:
        r"""Handle \definecolor definitions"""
        start_pos = match.end() - 1  # -1 to go back {
        # 3 blocks: name, format, value e.g. \definecolor{linkcolor}{HTML}{ED1C24}
        blocks, end_pos = extract_nested_content_sequence_blocks(
            content[start_pos:], "{", "}", max_blocks=3
        )
        if len(blocks) != 3:
            return None, start_pos
        name = blocks[0]
        format = blocks[1]
        value = blocks[2]

        token = {
            "type": "definecolor",
            "name": name,
            "format": format,
            "value": value,
        }

        return token, start_pos + end_pos

    def _handle_newfam(self, match) -> Tuple[Optional[Dict], int]:
        r"""Handle \newfam definitions"""
        var_name = match.group(1).strip()
        token = {"type": "newfam", "name": var_name}
        return token, match.end()

    def _handle_font(self, match) -> Tuple[Optional[Dict], int]:
        """Handle \font definitions"""
        font_name = match.group(1)
        font_source = match.group(2)

        token = {
            "type": "font",
            "name": font_name,
            "source": font_source,
        }

        # Add size information if present
        if match.group(3) and match.group(4):
            token["size"] = match.group(3)
            token["unit"] = match.group(4)

        return token, match.end()


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
    \@namedef{ver@everyshi.sty}{}
    \makeatother
    """.strip()

    out, pos = handler.handle(text)
    print(out)
    print(text[pos:])
