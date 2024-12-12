import re
from typing import Callable, Dict, List, Optional, Tuple
from src.handlers.base import TokenHandler
from src.tex_utils import (
    extract_nested_content,
    extract_nested_content_pattern,
    find_matching_env_block,
)

BEGIN_GROUP_PATTERN = re.compile(r"\\begingroup\b")
END_GROUP_PATTERN = re.compile(r"\\endgroup\b")

ENV_NAME_BRACE_PATTERN = r"\{([^}]*?)\}"

# e.g. \list \endlist, \xxx \endxxx etc
# make sure to tweak the '1' in end\1 to match the relevant regex group if combining with other patterns
ENV_PAIR_PATTERN = r"\\((?:\w|@)+)(\s*(?:\{[^}]*\}|\[[^]]*\])*\s*.*)\\end\1"

# Check for both \begin{xxx} and \xxx \endxxx e.g. \list \endlist, etc
ENVIRONMENT_PATTERN = re.compile(
    r"\\begin\s*%s|%s" % (ENV_NAME_BRACE_PATTERN, ENV_PAIR_PATTERN[:-1] + "2"),
    re.DOTALL,
)

NEW_ENVIRONMENT_PATTERN = re.compile(
    r"\\(?:new|renew|provide)environment\*?\s*%s" % (ENV_NAME_BRACE_PATTERN),
)

LIST_ENVIRONMENTS = ["itemize", "enumerate", "description"]

LAYOUT_ENVIRONMENTS = [
    "group",
    "center",
    "flushleft",
    "flushright",
    "minipage",
    "adjustbox",
    "spacing",
    "small",
    "subequations",
]

# Mathematical/Proof environments
MATH_ENVIRONMENTS = [
    "theorem",
    "lemma",
    "proposition",
    "corollary",
    "definition",
    "proof",
    "example",
    "remark",
    "note",
    "claim",
    "conjecture",
    "axiom",
]

# Map environment names to their types
ENV_TYPES = {
    "document": "document",
    "abstract": "abstract",
    "thebibliography": "bibliography",
    "appendix": "appendix",
    "appendices": "appendix",
    "table": "table",
    "subtable": "table",
    "subsubtable": "table",
    "tabular": "tabular",  # should be handled in tabular handler
    "figure": "figure",
    "subfigure": "figure",
    "subfloat": "figure",  # another common figure subdivision
    "algorithm": "algorithm",
    "algorithmic": "algorithmic",
    "quote": "quote",
    "list": "list",  # \list \endlist
    **{env: "list" for env in LIST_ENVIRONMENTS},
    **{env: "group" for env in LAYOUT_ENVIRONMENTS},
    **{env: "math_env" for env in MATH_ENVIRONMENTS},
}

# Add to your environment configurations
ENV_ARGS = {
    "thebibliography": {"mandatory": 1},  # Expects 1 mandatory argument
    "minipage": {"mandatory": 1},  # Expects 1 mandatory argument
    "list": {"mandatory": 2},  # usually used as \list{label}{spacing}
    # "tabular": {"mandatory": 1},          # Expects 1 mandatory argument for column spec
    "table": {"optional": 1},  # Expects 1 optional argument for placement
    "figure": {"optional": 1},  # Expects 1 optional argument for placement
    # ... other environments with known argument patterns
}


def convert_any_env_pairs_to_begin_end(content: str) -> str:
    r"""Convert any \aa \endaa pairs to \begin{aa} \end{aa}"""
    pattern = re.compile(ENV_PAIR_PATTERN, re.DOTALL)

    match = pattern.search(content)
    while match:
        env_name = match.group(1)
        start_pos, end_pos, inner_content = extract_nested_content_pattern(
            content, r"\\" + env_name, r"\\end" + env_name
        )
        inner_content = convert_any_env_pairs_to_begin_end(inner_content)
        inner_content = r"\begin{%s}%s\end{%s}" % (env_name, inner_content, env_name)
        content = content[:start_pos] + inner_content + content[end_pos:]
        match = pattern.search(content)
    return content


def find_matching_group_end(text: str, start_pos: int = 0) -> int:
    """Find the matching endgroup for a begingroup, handling nested groups"""
    nesting_level = 1
    current_pos = start_pos

    while nesting_level > 0 and current_pos < len(text):
        begin_match = BEGIN_GROUP_PATTERN.search(text[current_pos:])
        end_match = END_GROUP_PATTERN.search(text[current_pos:])

        if not end_match:
            return -1  # No matching endgroup found

        # Find which comes first - a begin or an end
        begin_pos = begin_match.start() if begin_match else float("inf")
        end_pos = end_match.start()

        if begin_pos < end_pos:
            # Found nested begingroup
            nesting_level += 1
            current_pos += begin_pos + len("\\begingroup")
        else:
            # Found endgroup
            nesting_level -= 1
            current_pos += end_pos + len("\\endgroup")
            if nesting_level == 0:
                return current_pos - len("\\endgroup")

    return -1 if nesting_level > 0 else current_pos


class EnvironmentProcessor:
    def __init__(self):
        self.environments: Dict[str, Dict[str, any]] = {}

    def clear(self):
        self.environments = {}

    def process_environment_definition(
        self,
        env_name: str,
        begin_def: str,
        end_def: str,
        num_args: Optional[int] = None,
        optional_args: Optional[List[str]] = None,
    ) -> None:
        """Store a new or renewed environment definition"""
        environment = {
            "name": env_name,
            "begin_def": begin_def,
            "end_def": end_def,
            "args": {
                "num_args": int(num_args) if num_args else 0,
                "optional_args": optional_args or [],
            },
        }

        self.environments[env_name] = environment

    def has_environment(self, env_name: str) -> bool:
        return env_name in self.environments

    def expand_environments(self, env_name: str, text: str) -> str:
        """Expand defined environments in the text

        Args:
            env_name: Name of the environment to expand
            text: The content inside the environment (between begin/end tags)

        Returns:
            The processed content with the environment expanded
        """
        if self.has_environment(env_name):
            env_info = self.environments[env_name]

            # Extract arguments and content
            args = []
            content = text

            # Handle optional arguments [arg]
            for _ in env_info["args"]["optional_args"]:
                if content.startswith("["):
                    arg, end_pos = extract_nested_content(content, "[", "]")
                    content = content[end_pos:]
                    args.append(arg)
                else:
                    args.append(None)

            # Handle required arguments {arg}
            for _ in range(env_info["args"]["num_args"]):
                if content.startswith("{"):
                    arg, end_pos = extract_nested_content(content, "{", "}")
                    content = content[end_pos:]
                    args.append(arg)
                else:
                    args.append("")  # Empty string for missing required args

            # Process begin definition with arguments
            result = env_info["begin_def"] + "\n"  # add trailing space to pad
            for i, arg in enumerate(args, 1):
                if arg is not None:
                    # Replace unescaped #i with arg, preserve \#
                    result = re.sub(r"(?<!\\)#" + str(i), arg, result)

            # Add content and end definition
            result += content + "\n" + env_info["end_def"]

            return result

        return text


class BaseEnvironmentHandler(TokenHandler):
    def __init__(self):
        super().__init__()
        self._newtheorems: Dict[str, str] = {}

    def process_newtheorem(self, var_name: str, title: str):
        self._newtheorems[var_name] = title

    def clear(self):
        self._newtheorems = {}

    def can_handle(self, content: str) -> bool:
        return (
            ENVIRONMENT_PATTERN.match(content) is not None
            or BEGIN_GROUP_PATTERN.match(content) is not None
        )

    def _handle_environment(self, env_name: str, inner_content: str) -> None:

        contains_asterisk = "*" in env_name
        env_name = env_name.replace("*", "")

        env_name = self._newtheorems.get(env_name, env_name)
        token = {"type": "environment", "name": env_name}

        env_type = ENV_TYPES.get(env_name.lower(), "environment")
        token["type"] = env_type

        if not contains_asterisk and env_type in ["table", "figure", "math_env"]:
            token["numbered"] = True

        # Extract title if present (text within square brackets after environment name)
        title, end_pos = extract_nested_content(inner_content, "[", "]")
        if title:
            inner_content = inner_content[end_pos:]
            token["title"] = title

        # Extract arguments based on environment type
        if env_name in ENV_ARGS and ENV_ARGS[env_name].get("mandatory", 0) > 0:
            args = []
            num_args = ENV_ARGS[env_name].get("mandatory")
            for _ in range(num_args):
                # Handle as argument
                arg, end_pos = extract_nested_content(inner_content, "{", "}")
                if end_pos > 0:
                    inner_content = inner_content[
                        end_pos:
                    ]  # Remove argument from content
                    args.append(arg)
            token["args"] = args

        token["content"] = inner_content

        return token

    def _try_match_env(
        self, content: str, match: Optional[re.Match] = None
    ) -> Tuple[Optional[Dict], int]:
        """Try to match an environment pattern"""
        if not match:
            match = ENVIRONMENT_PATTERN.match(content)
        if match and match.re.pattern == ENVIRONMENT_PATTERN.pattern:
            # Verify it's an environment match
            is_begin = match.group(0).startswith("\\begin")
            # Find the correct ending position for this environment
            if is_begin:
                env_name = match.group(1).strip()
                start_pos, end_pos, inner_content = find_matching_env_block(
                    content, env_name
                )
            else:
                env_name = match.group(2).strip()

                start_pos, end_pos, inner_content = extract_nested_content_pattern(
                    content, r"\\" + env_name, r"\\end" + env_name
                )
                if env_name == "@float":
                    # e.g. \@float{table} -> \begin{@float}{table} -> \begin{table}
                    inner_match = re.match(
                        r"\s*" + ENV_NAME_BRACE_PATTERN, inner_content
                    )
                    if inner_match:
                        env_name = inner_match.group(1).strip()  # i.e. table
                        inner_content = inner_content[inner_match.end() :]

            if end_pos == -1:
                # No matching end found, treat as plain text
                return match.group(0), match.end()
            else:
                env_token = self._handle_environment(env_name, inner_content)
                return env_token, end_pos
        return None, 0

    def _try_match_group(
        self, content: str, match: Optional[re.Match] = None
    ) -> Tuple[Optional[Dict], int]:
        """Try to match a group pattern"""
        if not match:
            match = BEGIN_GROUP_PATTERN.match(content)
        if (
            match and match.re.pattern == BEGIN_GROUP_PATTERN.pattern
        ):  # Verify it's a group match
            start_pos = match.end()
            end_pos = find_matching_group_end(content, start_pos)

            if end_pos == -1:
                # No matching endgroup found, treat as plain text
                return match.group(0), match.end()

            # Extract content between begingroup and endgroup
            inner_content = content[start_pos:end_pos].strip()

            token = {
                "type": ENV_TYPES.get("group", "environment"),
                "name": "group",
                "content": inner_content,
            }

            return token, end_pos + len("\\endgroup")

        return None, 0

    def handle(
        self, content: str, prev_token: Optional[Dict] = None
    ) -> Tuple[Optional[Dict], int]:
        env, end_pos = self._try_match_env(content)
        if env:
            return env, end_pos

        return self._try_match_group(content)

    def search(self, content: str) -> Optional[re.Match]:
        """Search for the next environment or group pattern match"""
        # search both to see which one appears first
        env_match = ENVIRONMENT_PATTERN.search(content)
        group_match = BEGIN_GROUP_PATTERN.search(content)

        # Return the first match found (or None if neither found)
        if not env_match and not group_match:
            return None
        elif not env_match:
            return group_match
        elif not group_match:
            return env_match
        # Return whichever match appears first
        return env_match if env_match.start() < group_match.start() else group_match


class EnvironmentHandler(BaseEnvironmentHandler):
    def __init__(self):
        super().__init__()

        self.environment_processor = EnvironmentProcessor()

    @property
    def environments(self):
        return self.environment_processor.environments

    def clear(self):
        super().clear()
        self.environment_processor.clear()

    def _handle_newenvironment_def(
        self, content: str, match
    ) -> Tuple[Optional[Dict], int]:
        """Handle \newenvironment definitions"""
        env_name = match.group(1)
        current_pos = match.end()

        # Store environment definition
        token = {
            "begin_def": "",
            "end_def": "",
            "name": env_name,
            "args": [],
            "optional_args": [],
        }

        # Look for optional arguments [n][default]...
        while current_pos < len(content):
            # Skip whitespace
            while current_pos < len(content) and content[current_pos].isspace():
                current_pos += 1

            if current_pos >= len(content) or content[current_pos] != "[":
                break

            # Find matching closing bracket
            bracket_count = 1
            search_pos = current_pos + 1
            bracket_start = search_pos

            while search_pos < len(content) and bracket_count > 0:
                if content[search_pos] == "[":
                    bracket_count += 1
                elif content[search_pos] == "]":
                    bracket_count -= 1
                search_pos += 1

            if bracket_count == 0:
                # Successfully found matching bracket
                arg = content[bracket_start : search_pos - 1].strip()

                # First bracket usually contains number of arguments
                if len(token["args"]) == 0 and arg.isdigit():
                    token["args"] = [f"#{i+1}" for i in range(int(arg))]
                else:
                    token["optional_args"].append(arg)

                current_pos = search_pos
            else:
                break

        # Get begin definition
        next_brace = content[current_pos:].find("{")
        if next_brace == -1:
            return None, current_pos

        begin_def, first_end = extract_nested_content(
            content[current_pos + next_brace :]
        )
        if begin_def is None:
            return None, current_pos
        token["begin_def"] = begin_def

        first_end = current_pos + next_brace + first_end

        # Find next brace for end definition
        next_brace = content[first_end:].find("{")
        if next_brace == -1:
            return None, first_end
        next_pos = first_end + next_brace

        end_def, final_end = extract_nested_content(content[next_pos:])
        if end_def is None:
            return None, first_end

        token["end_def"] = end_def
        final_end = next_pos + final_end

        return token, final_end

    def can_handle(self, content: str) -> bool:
        return (
            super().can_handle(content)
            or NEW_ENVIRONMENT_PATTERN.match(content) is not None
        )

    def _handle_environment(self, env_name: str, inner_content: str) -> None:
        if self.environment_processor.has_environment(env_name):
            # check if expanded and changed
            inner_content = self.environment_processor.expand_environments(
                env_name, inner_content
            )

            return {"type": "environment", "name": env_name, "content": inner_content}

        return super()._handle_environment(env_name, inner_content)

    def handle(
        self, content: str, prev_token: Optional[Dict] = None
    ) -> Tuple[Optional[Dict], int]:
        # check for new environment definition first
        new_env_match = NEW_ENVIRONMENT_PATTERN.match(content)
        if new_env_match:
            token, end_pos = self._handle_newenvironment_def(content, new_env_match)
            if token:
                env_name = token["name"]
                # DO NOT OVERRIDE EXISTING (IMPORTANT) ENVIRONMENTS
                if env_name not in ENV_TYPES.values():
                    self.environment_processor.process_environment_definition(
                        env_name,
                        token["begin_def"],
                        token["end_def"],
                        len(token["args"]),
                        token["optional_args"],
                    )
            return None, end_pos

        return super().handle(content, prev_token)


if __name__ == "__main__":
    handler = EnvironmentHandler()

    # content = r"\begin{figure*}[h]\end{figure*}"
    # print(handler.handle(content))

    content = r"\xxx \item[] \endxxx"
    # print(ENVIRONMENT_PATTERN.match(content))
    print(handler.handle(content))
