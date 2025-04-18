import re
from typing import Callable, Dict, List, Optional, Tuple
from latex2json.parser.handlers.base import TokenHandler
from latex2json.utils.tex_utils import (
    extract_args,
    extract_nested_content,
    extract_nested_content_pattern,
    extract_nested_content_sequence_blocks,
    find_matching_env_block,
    substitute_args,
)
import logging

BEGIN_GROUP_PATTERN = re.compile(r"\\(?:begin|b)group\b")

ENV_NAME_BRACE_PATTERN = r"\{([^}]*?)\}"

# e.g. \list \endlist, \xxx \endxxx etc
# make sure to tweak the '1' in end\1 to match the relevant regex group if combining with other patterns
ENV_PAIR_PATTERN = r"\\((?:\w|@)+\b)(\s*(?:\{[^}]*\}|\[[^]]*\])*\s*.*)\\end\1"

# Check for both \begin{xxx} and \xxx \endxxx e.g. \list \endlist, etc
ENVIRONMENT_PATTERN = re.compile(
    r"\\begin\s*%s|%s" % (ENV_NAME_BRACE_PATTERN, ENV_PAIR_PATTERN[:-1] + "2"),
    re.DOTALL,
)

NEW_ENVIRONMENT_PATTERN = re.compile(
    r"\\(?:new|renew|provide)environment\*?\s*\{([^}]*?)\}",
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

# Mathematical/Proof environments - numbered ones
NUMBERED_MATH_ENVIRONMENTS = [
    "theorem",
    "lemma",
    "proposition",
    "corollary",
    "definition",
    "conjecture",
    "axiom",
    "example",
    "exercise",
    # could be variable
    "remark",
    "observation",
]

# All math environments (numbered + unnumbered)
MATH_ENVIRONMENTS = NUMBERED_MATH_ENVIRONMENTS + [
    # unnumbered environments
    "proof",
    "notation",
    "solution",
    "note",
    "claim",
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
    "subfigure": "subfigure",
    "subfloat": "subfigure",  # another common figure subdivision
    "wrapfigure": "figure",
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
    "adjustwidth": {"mandatory": 2},  # usually used as \adjustwidth{left}{right}
    "spacing": {"mandatory": 1},  # usually used as \spacing{1em}
    "multicols": {"mandatory": 1},  # usually used as \multicols{2}
    # "tabular": {"mandatory": 1},          # Expects 1 mandatory argument for column spec
    "table": {"optional": 1},  # Expects 1 optional argument for placement
    "figure": {"optional": 1},  # Expects 1 optional argument for placement
    "subfigure": {"optional": 1, "mandatory": 1},
    "wrapfigure": {"optional": 1, "mandatory": 2},
    "adjustbox": {"mandatory": 1},  # Expects 1 mandatory argument for width
    # ... other environments with known argument patterns
    "CJK": {"mandatory": 2},
}


def get_env_type(env_name: str) -> str:
    return ENV_TYPES.get(env_name.lower(), "environment")


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


def find_pattern_while_skipping_nested_envs(
    content: str,
    pattern: re.Pattern,
    start_pos: int = 0,
) -> int:
    """
    Find the next occurrence of a pattern while properly handling nested environments.

    Args:
        content: The content to search in
        current_pos: Starting position for the search
        pattern: Compiled regex pattern to search for

    Returns:
        Position where the next pattern match begins, or the current position
        if no match is found
    """
    end_pos = -1

    next_match = pattern.search(content[start_pos:])
    while next_match:
        # check for nested inner envs
        env_match = BaseEnvironmentHandler.search(content[start_pos:])
        if not env_match:
            return start_pos + next_match.start()

        start_env = env_match.start()
        # If we find a nested environment after the next match,
        # we can safely exit
        if start_env > next_match.start():
            return start_pos + next_match.start()

        # Handle and skip the inner environment
        inner_token, inner_length = BaseEnvironmentHandler.try_handle(
            content[start_pos + start_env :]
        )
        if not inner_token:
            return end_pos

        start_pos += start_env + inner_length
        end_pos = start_pos

        next_match = pattern.search(content[start_pos:])

    return len(content) if end_pos >= 0 else -1


class BaseEnvironmentHandler(TokenHandler):
    def __init__(self, logger=None, **kwargs):
        super().__init__(**kwargs)
        self.logger = logger or logging.getLogger(__name__)
        self._newtheorems: Dict[str, str] = {}
        self._floatnames: Dict[str, str] = {}

    def process_newtheorem(self, var_name: str, title: str):
        self._newtheorems[var_name] = title

    def process_floatname(self, var_name: str, title: str):
        self._floatnames[var_name] = title

    def clear(self):
        self._newtheorems = {}
        self._floatnames = {}

    def can_handle(self, content: str) -> bool:
        return (
            ENVIRONMENT_PATTERN.match(content) is not None
            or BEGIN_GROUP_PATTERN.match(content) is not None
        )

    def _handle_environment(self, env_name: str, inner_content: str) -> None:

        contains_asterisk = "*" in env_name
        env_name = env_name.replace("*", "")

        env_name = self._newtheorems.get(env_name, env_name)
        token = {
            "type": "environment",
            "name": self._floatnames.get(env_name, env_name),
        }

        env_type = get_env_type(env_name)
        token["type"] = env_type

        # ignore numbering of subfigures/tables?
        if env_type == "math_env" and not contains_asterisk:
            if env_name.lower() in NUMBERED_MATH_ENVIRONMENTS:
                token["numbered"] = True
        elif env_type in ["table", "figure", "algorithm"] and not env_name.startswith(
            "sub"
        ):
            token["numbered"] = True

        # Extract title if present (text within square brackets after environment name)
        opt_found = False
        title, end_pos = extract_nested_content(inner_content, "[", "]")
        if end_pos > 0:
            inner_content = inner_content[end_pos:]
            opt_found = True
        if title and env_type == "math_env":
            token["title"] = title

        # Extract arguments based on environment type
        if env_name in ENV_ARGS:
            d = ENV_ARGS[env_name]

            opt_args = d.get("optional", 0)
            if opt_args > 0:
                if opt_found:
                    opt_args -= 1

            req_args = d.get("mandatory", 0)
            args, end_pos = extract_args(inner_content, req_args, opt_args)
            if args["req"]:
                token["args"] = args["req"]
            inner_content = inner_content[end_pos:]

        token["content"] = inner_content

        return token

    @staticmethod
    def try_match_env(
        content: str, match: Optional[re.Match] = None
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
                all_str = match.group(0)
                env_name = (
                    all_str[all_str.rfind("\\end") :].replace("\\end", "").strip()
                )

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

            token = {
                "name": env_name,
                "match": match,
                "end_pos": end_pos,
                "content": inner_content,
            }
            if end_pos <= 0:
                # could not find matching env block. default to end of match
                end_pos = match.end()
                token["end_pos"] = end_pos
                token["incomplete"] = True
                return True, token

            return True, token
        return False, 0

    @staticmethod
    def try_match_group(
        content: str, match: Optional[re.Match] = None
    ) -> Tuple[Optional[Dict], int]:
        """Try to match a group pattern"""
        if not match:
            match = BEGIN_GROUP_PATTERN.match(content)
        if (
            match and match.re.pattern == BEGIN_GROUP_PATTERN.pattern
        ):  # Verify it's a group match
            is_bgroup = "bgroup" in match.group(0)
            if is_bgroup:
                start_pos, end_pos, inner_content = extract_nested_content_pattern(
                    content, r"\\bgroup\b", r"\\egroup\b"
                )
            else:
                start_pos, end_pos, inner_content = extract_nested_content_pattern(
                    content, r"\\begingroup\b", r"\\endgroup\b"
                )

            if end_pos == -1:
                return None, 0

            token = {
                "type": ENV_TYPES.get("group", "environment"),
                "name": "group",
                "content": inner_content,
            }

            return token, end_pos

        return None, 0

    def handle(
        self, content: str, prev_token: Optional[Dict] = None
    ) -> Tuple[Optional[Dict], int]:
        # If not a definition, proceed with regular environment handling
        matched, out = BaseEnvironmentHandler.try_match_env(content)
        if matched:
            env_name = out["name"]
            if out.get("incomplete"):
                self.logger.warning(
                    f"Could not find matching env block for {env_name}, defaulting to end of match"
                )
            # ignore begin{comment} env
            if env_name == "comment":
                return None, out["end_pos"]

            env_token = self._handle_environment(env_name, out["content"])
            return env_token, out["end_pos"]

        return BaseEnvironmentHandler.try_match_group(content)

    @staticmethod
    def try_handle(content: str) -> Tuple[Optional[Dict], int]:
        matched, out = BaseEnvironmentHandler.try_match_env(content)
        if matched:
            env_name = out["name"]
            env_type = get_env_type(env_name)
            return {
                "type": env_type,
                "name": env_name,
                "content": out["content"],
            }, out["end_pos"]

        return BaseEnvironmentHandler.try_match_group(content)

    @staticmethod
    def search(content: str) -> Optional[re.Match]:
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
            "num_args": int(num_args) if num_args else 0,
            "optional_args": optional_args or [],
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
            num_req_args = env_info["num_args"] - len(env_info["optional_args"])
            for opt_arg in env_info["optional_args"]:
                if content.startswith("["):
                    arg, end_pos = extract_nested_content(content, "[", "]")
                    content = content[end_pos:]
                    args.append(arg)
                else:
                    args.append(opt_arg)

            # Handle required arguments {arg}
            for _ in range(num_req_args):
                if content.startswith("{"):
                    arg, end_pos = extract_nested_content(content, "{", "}")
                    content = content[end_pos:]
                    args.append(arg)
                else:
                    args.append("")  # Empty string for missing required args

            # Process begin definition with arguments
            begin_def = substitute_args(env_info["begin_def"], args)
            end_def = substitute_args(env_info["end_def"], args)

            # Add content and end definition
            result = begin_def + "\n" + content + "\n" + end_def

            return result

        return text


class EnvironmentHandler(BaseEnvironmentHandler):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.environment_processor = EnvironmentProcessor()

    @property
    def environments(self):
        return self.environment_processor.environments

    def clear(self):
        super().clear()
        self.environment_processor.clear()

    def can_handle(self, content: str) -> bool:
        return (
            ENVIRONMENT_PATTERN.match(content) is not None
            or BEGIN_GROUP_PATTERN.match(content) is not None
            or NEW_ENVIRONMENT_PATTERN.match(content) is not None
        )

    def process_newenvironment(
        self,
        env_name: str,
        begin_def: str,
        end_def: str,
        num_args: Optional[int] = None,
        optional_args: Optional[List[str]] = None,
    ) -> None:
        self.environment_processor.process_environment_definition(
            env_name, begin_def, end_def, num_args, optional_args
        )

    def handle_newenvironment(
        self, content: str, match: Optional[re.Match] = None
    ) -> Tuple[Optional[Dict], int]:
        """Handle \newenvironment definitions - copied from new_definition.py"""
        if not match:
            match = NEW_ENVIRONMENT_PATTERN.match(content)
        if not match:
            return None, 0
        env_name = match.group(1)
        current_pos = match.end()

        # Store environment definition
        token = {
            "type": "newenvironment",
            "begin_def": "",
            "end_def": "",
            "name": env_name,
            "num_args": 0,
            "optional_args": [],
        }

        # Look for optional arguments [n][default]...
        blocks, end_pos = extract_nested_content_sequence_blocks(
            content[current_pos:], "[", "]"
        )
        if blocks:
            first_arg = blocks[0].strip()
            if first_arg.isdigit():
                token["num_args"] = int(first_arg)
            for block in blocks[1:]:
                token["optional_args"].append(block.strip())

        current_pos += end_pos
        blocks, end_pos = extract_nested_content_sequence_blocks(
            content[current_pos:], "{", "}", max_blocks=2
        )
        if len(blocks) == 2:
            token["begin_def"] = blocks[0]
            token["end_def"] = blocks[1]

            # Register this environment definition
            self.process_newenvironment(
                env_name,
                blocks[0],
                blocks[1],
                token["num_args"],
                token["optional_args"],
            )
        else:
            return None, current_pos

        current_pos += end_pos
        return token, current_pos

    def _handle_environment(self, env_name: str, inner_content: str) -> None:
        if self.environment_processor.has_environment(env_name):
            # check if expanded and changed
            inner_content = self.environment_processor.expand_environments(
                env_name, inner_content
            )

            env_type = get_env_type(env_name)

            return {"type": env_type, "name": env_name, "content": inner_content}

        return super()._handle_environment(env_name, inner_content)

    def handle(
        self, content: str, prev_token: Optional[Dict] = None
    ) -> Tuple[Optional[Dict], int]:
        # First check for newenvironment definitions
        newenv_match = NEW_ENVIRONMENT_PATTERN.match(content)
        if newenv_match:
            out, end_pos = self.handle_newenvironment(content, newenv_match)
            return None, end_pos

        return super().handle(content, prev_token)


if __name__ == "__main__":
    handler = EnvironmentHandler()

    # content = r"\begin{figure*}[h]\end{figure*}"
    # print(handler.handle(content))
    content = (
        r"\begingroup\bgroup\begin{center}Center\end{center}\egroup\endgroup hahaha"
    )
    token, pos = handler.handle(content)
    print(token)
