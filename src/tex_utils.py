from typing import Callable, Dict, Tuple
import re


def find_matching_delimiter(
    text: str, open_delim: str = "{", close_delim: str = "}", start: int = 0
) -> Tuple[int, int]:
    """
    Find the position of the matching closing delimiter, handling nested delimiters.
    Returns a tuple of (start_pos, end_pos) where:
        - start_pos is the position of the opening delimiter
        - end_pos is the position of the matching closing delimiter
    Returns (-1, -1) if no valid delimiters found.
    """
    # Skip leading whitespace
    while start < len(text) and text[start].isspace():
        start += 1

    if start >= len(text) or text[start] != open_delim:
        return -1, -1

    stack = []
    i = start
    while i < len(text):
        # Check for escaped delimiters
        if i > 0 and text[i - 1] == "\\":
            i += 1
            continue

        if text[i] == open_delim:
            stack.append(i)
        elif text[i] == close_delim:
            if not stack:
                return -1, -1  # Unmatched closing delimiter
            stack.pop()
            if not stack:  # Found the matching delimiter
                return start, i
        i += 1
    return -1, -1  # No matching delimiter found


def extract_nested_content(
    text: str, open_delim: str = "{", close_delim: str = "}"
) -> Tuple[str | None, int]:
    """
    Extract content between delimiters, handling nesting.
    Returns a tuple of (content, next_position) where:
        - content is the text between delimiters (or None if not found)
        - next_position is the position after the closing delimiter (or 0 if not found)
    """
    start_pos, end_pos = find_matching_delimiter(text, open_delim, close_delim)
    if start_pos == -1:
        return None, 0

    # Return content without the delimiters and the next position to process
    content = text[start_pos + 1 : end_pos]
    return content, end_pos + 1


def extract_nested_content_pattern(
    text: str, begin_pattern: re.Pattern | str, end_pattern: re.Pattern | str
) -> Tuple[str | None, int]:
    """
    Extract content between regex patterns, handling nesting.
    Returns a tuple of (content, next_position) where:
        - content is the text between patterns (or None if not found)
        - next_position is the position after the end pattern (or 0 if not found)
    """
    # Convert string patterns to compiled regex if needed
    if isinstance(begin_pattern, str):
        begin_pattern = re.compile(begin_pattern)
    if isinstance(end_pattern, str):
        end_pattern = re.compile(end_pattern)

    # Find the first beginning pattern
    begin_match = begin_pattern.search(text)
    if not begin_match:
        return None, 0

    nesting_level = 1
    current_pos = begin_match.end()
    content_start = current_pos

    while nesting_level > 0 and current_pos < len(text):
        # Look for both patterns from current position
        begin_match = begin_pattern.search(text, current_pos)
        end_match = end_pattern.search(text, current_pos)

        # If no end pattern found, return None
        if not end_match:
            return None, 0

        # If no begin pattern found or end pattern comes first
        if not begin_match or end_match.start() < begin_match.start():
            nesting_level -= 1
            if nesting_level == 0:
                content = text[content_start : end_match.start()]
                return content, end_match.end()
            current_pos = end_match.end()
        else:
            nesting_level += 1
            current_pos = begin_match.end()

    return None, 0


def find_matching_env_block(
    text: str, env_name: str, start_pos: int = 0
) -> Tuple[int, int, str]:
    r"""Find the matching \end{env_name} for a \begin{env_name}, handling nested environments.
    Returns a tuple of (start_pos, end_pos, inner_content) where:
        - start_pos is the position of the beginning of \begin{env_name}
        - end_pos is the position of the end of \end{env_name}
        - inner_content is the text between \begin{env_name} and \end{env_name}
    Returns (-1, -1, "") if no valid match is found.
    """
    escaped_name = re.escape(env_name)
    begin_pattern = r"\\begin\s*\{" + escaped_name + "}"
    end_pattern = r"\\end\s*\{" + escaped_name + "}"

    # Find the first \begin
    begin_match = re.search(begin_pattern, text[start_pos:])
    if not begin_match:
        return -1, -1, ""

    absolute_start = start_pos + begin_match.start()
    content, end_pos = extract_nested_content_pattern(
        text[start_pos:], begin_pattern, end_pattern
    )

    if content is None:
        return -1, -1, ""

    return absolute_start, start_pos + end_pos, content.strip()


def strip_latex_newlines(latex_str: str) -> str:
    # Replace LaTeX line break commands with a space
    latex_str = re.sub(r"\\\\|\\newline", " ", latex_str)

    # Remove any remaining newline characters
    latex_str = latex_str.replace("\n", " ")

    # Optionally, collapse multiple spaces into a single space
    latex_str = re.sub(r"\s+", " ", latex_str)

    return latex_str.strip()


def flatten(lst):
    """Recursively flatten nested lists/tuples, preserving dictionaries as single elements."""
    result = []
    for item in lst:
        if isinstance(item, (list, tuple)):
            result.extend(flatten(item))
        else:
            result.append(item)
    return result


def substitute_patterns(
    text: str,
    patterns: Dict[str, re.Pattern],
    substitute_fn: Callable[[str, re.Match, str], Tuple[str, int]],
) -> str:
    """
    Substitute patterns in text with their handlers.
    """
    for key, pattern in patterns.items():
        current_pos = 0
        match = pattern.search(text)
        while match:
            start_pos = current_pos + match.start()

            converted, end_pos = substitute_fn(text[current_pos:], match, key)
            current_pos += end_pos

            diff = len(converted) - (current_pos - start_pos)
            text = text[:start_pos] + converted + text[current_pos:]
            current_pos += diff

            match = pattern.search(text[current_pos:])

    return text
