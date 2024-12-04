import re
from typing import Callable, Dict, Optional, Tuple
from src.handlers.base import TokenHandler
from src.tex_utils import extract_nested_content

POST_NEW_COMMAND_PATTERN_STR = (
    r"\*?\s*(?:{\\([^}]+)}|\\([^\s{[]+))(?:\s*\[(\d+)\])?((?:\s*\[[^]]*\])*)\s*{"
)

# Compile patterns for definition commands
PATTERNS = {
    # Matches newcommand/renewcommand, supports both {\commandname} and \commandname syntax
    "newcommand": re.compile(
        r"\\(?:new|renew|provide)command" + POST_NEW_COMMAND_PATTERN_STR, re.DOTALL
    ),
    "let": re.compile(r"\\let\s*\\([^\s{\\]+)\s*(=.*|\\[^\s{]+)", re.DOTALL),
    "declaremathoperator": re.compile(
        r"\\DeclareMathOperator" + POST_NEW_COMMAND_PATTERN_STR, re.DOTALL
    ),  # for math mode
    "declarerobustcommand": re.compile(
        r"\\DeclareRobustCommand" + POST_NEW_COMMAND_PATTERN_STR, re.DOTALL
    ),
    # Matches \def commands - always with backslash before command name
    "def": re.compile(
        r"(?:\\long)?\\def\s*\\([^\s{#]+)(((?:#\d+|[^{])*)\s*{)", re.DOTALL
    ),
    # Matches newtheorem with all its optional arguments
    "newtheorem": re.compile(
        r"\\newtheorem{([^}]*)}(?:\[([^]]*)\])?{([^}]*)}(?:\[([^]]*)\])?", re.DOTALL
    ),
    "crefname": re.compile(r"\\crefname{([^}]*)}{([^}]*)}{([^}]*)}", re.DOTALL),
    "newif": re.compile(r"\\newif\s*\\if([^\s{\\]+)", re.DOTALL),
}


class NewDefinitionHandler(TokenHandler):

    def can_handle(self, content: str) -> bool:
        """Check if the content contains any definition commands"""
        return any(pattern.match(content) for pattern in PATTERNS.values())

    def handle(self, content: str) -> Tuple[Optional[Dict], int]:
        """Handle definition commands and return appropriate token with definition details"""
        for pattern_name, pattern in PATTERNS.items():
            match = pattern.match(content)
            if match:
                # declaremathoperator is for math mde
                if pattern_name == "newcommand" or pattern_name.startswith("declare"):
                    return self._handle_newcommand(content, match)
                elif pattern_name == "let":
                    return self._handle_let(match)
                elif pattern_name == "newtheorem":
                    return self._handle_newtheorem(match)
                elif pattern_name == "def":
                    return self._handle_def(content, match)
                elif pattern_name == "crefname":
                    return self._handle_crefname(match)
                elif pattern_name == "newif":
                    return self._handle_newif(match)
                else:
                    return None, match.end()

        return None, 0

    def _handle_newif(self, match) -> Tuple[Optional[Dict], int]:
        r"""Handle \newif definitions"""
        var_name = match.group(1)
        token = {"type": "newif", "name": var_name}
        return token, match.end()

    def _handle_crefname(self, match) -> Tuple[Optional[Dict], int]:
        r"""Handle \crefname definitions"""
        token = {
            "type": "crefname",
            "counter": match.group(1),
            "singular": match.group(2),
            "plural": match.group(3),
        }
        return token, match.end()

    def _handle_let(self, match) -> Tuple[Optional[Dict], int]:
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

        token = {
            "type": "newcommand",
            "name": cmd_name,
            "content": definition,
            "num_args": 0,
            "defaults": [],
        }

        # Add number of arguments if specified
        if match.group(3):
            token["num_args"] = int(match.group(3))

        # Add default values if present
        if match.group(4):
            defaults = []
            for default in re.finditer(r"\[(.*?)\]", match.group(4)):
                defaults.append(default.group(1))
            if defaults:
                token["defaults"] = defaults

        return token, start_pos + end_pos - 1

    def _handle_newtheorem(self, match) -> Tuple[Optional[Dict], int]:
        """Handle \newtheorem definitions"""
        token = {"type": "theorem", "name": match.group(1), "title": match.group(3)}

        # Handle optional counter specification
        if match.group(2):
            token["counter"] = match.group(2)

        # Handle optional numbering within
        if match.group(4):
            token["within"] = match.group(4)

        return token, match.end()

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
        for param in re.finditer(r"#(\d)", usage_pattern):
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

        usage_pattern = "".join(parts)
        # Add check at the very end to prevent partial matches (e.g., \foo matching \foobar)
        usage_pattern = r"\\" + usage_pattern + r"(?![a-zA-Z@])"

        token = {
            "type": "def",
            "name": cmd_name,
            "content": definition,
            "num_args": param_count,
            "usage_pattern": usage_pattern,
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
