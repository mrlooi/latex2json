from typing import Callable, Dict, Tuple
import re
import os


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


def extract_nested_content_sequence_blocks(
    text: str, open_delim: str = "{", close_delim: str = "}", max_blocks=float("inf")
) -> Tuple[list[str], int]:
    """
    Extract multiple nested content blocks and return their contents along with the final position.
    Returns a tuple of (blocks, total_end_pos) where:
        - blocks is a list of extracted content strings
        - total_end_pos is the position after the last closing delimiter
    """
    i = 0
    blocks = []
    total_pos = 0
    last_valid_pos = 0
    current_text = text

    while i < max_blocks:
        # Skip any leading whitespace
        while current_text and current_text[0].isspace():
            current_text = current_text[1:]
            total_pos += 1

        content, next_pos = extract_nested_content(
            current_text, open_delim, close_delim
        )
        if next_pos == 0:
            # If no more blocks found, return the position of the last successful block
            return blocks, last_valid_pos

        blocks.append(content)
        current_text = current_text[next_pos:]
        total_pos += next_pos
        last_valid_pos = total_pos
        i += 1

    return blocks, last_valid_pos


def extract_nested_content_pattern(
    text: str, begin_pattern: re.Pattern | str, end_pattern: re.Pattern | str
) -> Tuple[int, int, str]:
    """
    Extract content between regex patterns, handling nesting.
    Returns a tuple of (start_pos, end_pos, content) where:
        - start_pos is the position of the beginning pattern
        - end_pos is the position after the end pattern
        - content is the text between patterns
    Returns (-1, -1, "") if no valid match is found.
    """
    # Convert string patterns to compiled regex if needed
    if isinstance(begin_pattern, str):
        begin_pattern = re.compile(begin_pattern)
    if isinstance(end_pattern, str):
        end_pattern = re.compile(end_pattern)

    # Find the first beginning pattern
    begin_match = begin_pattern.search(text)
    if not begin_match:
        return -1, -1, ""

    nesting_level = 1
    current_pos = begin_match.end()
    content_start = current_pos
    start_pos = begin_match.start()

    while nesting_level > 0 and current_pos < len(text):
        begin_match = begin_pattern.search(text, current_pos)
        end_match = end_pattern.search(text, current_pos)

        if not end_match:
            return -1, -1, ""

        if not begin_match or end_match.start() < begin_match.start():
            nesting_level -= 1
            if nesting_level == 0:
                content = text[content_start : end_match.start()]
                return start_pos, end_match.end(), content
            current_pos = end_match.end()
        else:
            nesting_level += 1
            current_pos = begin_match.end()

    return -1, -1, ""


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

    # Adjust for start_pos by slicing the text and adjusting returned positions
    text_slice = text[start_pos:]
    start, end, content = extract_nested_content_pattern(
        text_slice, begin_pattern, end_pattern
    )

    if start == -1:
        return -1, -1, ""

    return start + start_pos, end + start_pos, content.strip()


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


def read_tex_file_content(
    file_path: str, dir_path: str = None, extension=".tex"
) -> str:
    """
    Attempts to read content from an input file, handling both absolute and relative paths.

    Args:
        file_path: Path to the input file (absolute or relative)

    Returns:
        str: Content of the file if successful, error message if failed
    """
    try:
        input_path = file_path
        # If path is not absolute and we know the current file's directory
        if not os.path.isabs(input_path) and dir_path:
            input_path = os.path.join(dir_path, input_path)

        # Try different extensions if file not found
        if not os.path.exists(input_path):
            for ext in ["", extension]:
                test_path = input_path + ext
                if os.path.exists(test_path):
                    input_path = test_path
                    break

        with open(input_path, "r") as f:
            return f.read()
    except (FileNotFoundError, IOError) as e:
        raise FileNotFoundError(f"Failed to read input file '{file_path}': {str(e)}")
