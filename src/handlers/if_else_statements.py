from typing import Dict, Optional, Tuple
import re

from src.handlers.base import TokenHandler

IF_PATTERN = re.compile(r"\\if(.*)([^\n]*)", re.IGNORECASE)
ELSE_PATTERN = re.compile(r"\\else\b", re.IGNORECASE)
ELSIF_PATTERN = re.compile(
    r"\\els(?:e)?if(.*)([^\n]*)", re.IGNORECASE
)  # Matches both \elsif and \elseif
FI_PATTERN = re.compile(r"\\fi\b", re.IGNORECASE)


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


class IfElseBlockHandler(TokenHandler):
    def can_handle(self, content: str) -> bool:
        return IF_PATTERN.match(content)

    def handle(
        self, content: str, prev_token: Optional[Dict] = None
    ) -> Tuple[Optional[Dict], int]:
        match = IF_PATTERN.match(content)
        if match:
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
\if{sdd}
  1 ONE uNO
\elseif{222}
    ELSE IF x2
\elseif{sss}
  \iftwo
    2
  \else
      2.3
  \fi
  4
\else
  ELSE 5
\fi

\ifthree
  content
\else
  else content
\fi
""".strip()

    handler = IfElseBlockHandler()
    print(handler.handle(text))
