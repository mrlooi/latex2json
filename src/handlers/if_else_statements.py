from typing import Dict, Optional, Tuple
import re

from src.handlers.base import TokenHandler
from src.tex_utils import extract_nested_content_sequence_blocks

IF_THEN_ELSE_PATTERN = re.compile(r"\\ifthenelse\s*\{", re.DOTALL)
IF_PATTERN = re.compile(r"\\if(?!thenelse)(.*)([^\n]*)")
ELSE_PATTERN = re.compile(r"\\else\b")
ELSIF_PATTERN = re.compile(
    r"\\els(?:e)?if(.*)([^\n]*)"
)  # Matches both \elsif and \elseif
FI_PATTERN = re.compile(r"\\fi\b")

PATTERNS = {
    "if": IF_PATTERN,
    "ifthenelse": IF_THEN_ELSE_PATTERN,
    "equal": re.compile(r"\\equal\s*\{"),
}


def extract_nested_if_else(
    content: str,
    start_delimiter: re.Pattern = IF_PATTERN,
    end_delimiter: re.Pattern = FI_PATTERN,
    else_delimiter: re.Pattern = ELSE_PATTERN,
    elsif_delimiter: re.Pattern = ELSIF_PATTERN,
) -> Tuple[str, str, list, int]:
    nesting_level = 1
    pos = 0
    content_length = len(content)
    if_content = []
    else_content = []
    elsif_branches = []
    current_buffer = if_content

    while pos < content_length and nesting_level > 0:
        # Find all possible next matches
        start_match = start_delimiter.search(content[pos:])
        end_match = end_delimiter.search(content[pos:])
        else_match = else_delimiter.search(content[pos:])
        elsif_match = elsif_delimiter.search(content[pos:])

        valid_matches = []
        if start_match:
            valid_matches.append((start_match.start(), start_match, "start"))
        if end_match:
            valid_matches.append((end_match.start(), end_match, "end"))
        if else_match and nesting_level == 1:  # Only consider else at top level
            valid_matches.append((else_match.start(), else_match, "else"))
        if elsif_match and nesting_level == 1:
            valid_matches.append((elsif_match.start(), elsif_match, "elsif"))

        if not valid_matches:
            raise ValueError("Unclosed conditional block")

        next_pos, next_match, match_type = min(valid_matches, key=lambda x: x[0])

        # Add content up to (but not including) the match for top-level else/elsif/fi
        if nesting_level == 1 and (match_type in ["else", "elsif", "end"]):
            current_buffer.append(content[pos : pos + next_match.start()])
        else:
            # For nested structures, include the full match
            current_buffer.append(content[pos : pos + next_match.end()])

        if match_type == "start":
            nesting_level += 1
        elif match_type == "end":
            nesting_level -= 1
        elif match_type == "else" and nesting_level == 1:
            if elsif_branches:
                condition = elsif_branches[-1][0]
                elsif_branches[-1] = (condition, "".join(current_buffer).strip())
            current_buffer = else_content
        elif match_type == "elsif" and nesting_level == 1:
            # First save the content we've collected so far
            current_content = "".join(current_buffer).strip()
            if current_buffer == if_content:
                if_content = [current_content]
            else:
                # Add the previous elsif branch
                condition = elsif_branches[-1][0]
                elsif_branches[-1] = (condition, current_content)

            # Start new buffer for the next elsif branch
            current_buffer = (
                []
            )  # Create new empty buffer for collecting the next branch
            elsif_condition = next_match.group(1)
            elsif_branches.append((elsif_condition, ""))
            current_buffer = []  # Reset buffer to collect the elsif content

        pos += next_match.end()

    return (
        "".join(if_content).strip(),
        "".join(else_content).strip(),
        elsif_branches,
        pos,
    )


def try_handle_ifthenelse(
    content: str, match: Optional[re.Match] = None
) -> Tuple[Optional[Dict], int]:
    if match is None:
        match = IF_THEN_ELSE_PATTERN.match(content)
    if match:
        start_pos = match.end() - 1  # -1 to exclude the opening brace
        blocks, end_pos = extract_nested_content_sequence_blocks(
            content[start_pos:], "{", "}", max_blocks=3
        )
        if len(blocks) != 3:
            raise ValueError("Invalid \\ifthenelse structure")
        return {
            "type": "conditional",
            "condition": blocks[0],
            "if_content": blocks[1],
            "else_content": blocks[2],
        }, start_pos + end_pos
    return None, 0


class IfElseBlockHandler(TokenHandler):
    def can_handle(self, content: str) -> bool:
        return any(pattern.match(content) for pattern in PATTERNS.values())

    def handle(
        self, content: str, prev_token: Optional[Dict] = None
    ) -> Tuple[Optional[Dict], int]:
        for name, pattern in PATTERNS.items():
            match = pattern.match(content)
            if match:
                if name == "ifthenelse":
                    token, end_pos = try_handle_ifthenelse(content, match)
                    return token, end_pos
                elif name == "equal":
                    start_pos = match.end() - 1
                    blocks, end_pos = extract_nested_content_sequence_blocks(
                        content[start_pos:], max_blocks=1
                    )
                    if len(blocks) == 0:
                        return None, 0
                    # ignore equal anyway
                    return None, start_pos + end_pos
                elif name == "if":
                    condition = match.group(1)
                    start_pos = match.end()
                    try:
                        if_content, else_content, elsif_branches, end_pos = (
                            extract_nested_if_else(content[start_pos:])
                        )
                    except ValueError as e:
                        print(ValueError(f"Unclosed conditional block: {e}"))
                        return None, 0
                    return {
                        "type": "conditional",
                        "condition": condition,
                        "if_content": if_content,
                        "else_content": else_content,
                        "elsif_branches": elsif_branches,
                    }, start_pos + end_pos

        return None, 0


if __name__ == "__main__":
    text = r"""
\ifasdaa{}{}{}
""".strip()

    handler = IfElseBlockHandler()
    print(handler.handle(text))
