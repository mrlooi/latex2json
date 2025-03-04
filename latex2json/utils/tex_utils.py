from typing import Callable, Dict, List, Tuple
import re
import os

from latex2json.utils.encoding import detect_encoding, read_file


def find_matching_delimiter(
    text: str, open_delim: str = "{", close_delim: str = "}", start: int = 0
) -> Tuple[int, int]:
    """
    Find the position of the matching closing delimiter, handling nested delimiters.
    Returns a tuple of (start_pos, end_pos) where:
        - start_pos is the position of the opening delimiter
        - end_pos is the position of the matching closing delimiter
    Returns (-1, -1) if no valid delimiters found.
    Handles:
        - Nested delimiters
        - Escaped characters (odd number of backslashes)
        - LaTeX comments (unescaped % to end of line)
    """

    def count_preceding_backslashes(pos: int) -> int:
        """Count number of backslashes immediately preceding the position."""
        count = 0
        pos -= 1
        while pos >= 0 and text[pos] == "\\":
            count += 1
            pos -= 1
        return count

    def is_escaped(pos: int) -> bool:
        """Check if character at position is escaped by backslashes."""
        return count_preceding_backslashes(pos) % 2 == 1

    # Skip leading whitespace
    while start < len(text) and text[start].isspace():
        start += 1

    if start >= len(text) or text[start] != open_delim:
        return -1, -1

    stack = []
    i = start
    while i < len(text):
        char = text[i]

        # Handle comments: unescaped % skips to next line
        if char == "%" and not is_escaped(i):
            i = text.find("\n", i)
            if i == -1:  # No more newlines found
                break
            i += 1  # Move past the newline
            continue

        # Handle delimiters
        if char in (open_delim, close_delim) and not is_escaped(i):
            if char == open_delim:
                stack.append(i)
            else:  # close_delim
                if not stack:
                    return -1, -1  # Unmatched closing delimiter
                stack.pop()
                if not stack:  # Found the matching delimiter
                    return start, i + 1

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
    content = text[start_pos + 1 : end_pos - 1]
    return content, end_pos


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

    # Find the first beginning pattern that isn't commented
    begin_match = begin_pattern.search(text)
    while begin_match and has_comment_on_sameline(text, begin_match.start()):
        begin_match = begin_pattern.search(text, begin_match.end())
    if not begin_match:
        return -1, -1, ""

    nesting_level = 1
    current_pos = begin_match.end()
    content_start = current_pos
    start_pos = begin_match.start()

    while nesting_level > 0 and current_pos < len(text):
        # Find next begin/end patterns, skipping commented ones
        begin_match = begin_pattern.search(text, current_pos)
        while begin_match and has_comment_on_sameline(text, begin_match.start()):
            begin_match = begin_pattern.search(text, begin_match.end())

        end_match = end_pattern.search(text, current_pos)
        while end_match and has_comment_on_sameline(text, end_match.start()):
            end_match = end_pattern.search(text, end_match.end())

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


def normalize_whitespace_and_lines(text: str) -> str:
    # Step 1: Replace two or more newlines (with optional surrounding spaces) with a unique marker.
    # This marker should be something unlikely to appear in your text.
    marker = "<PARA_BREAK>"
    text = re.sub(r"(?:[ \t]*\n[ \t]*){2,}", marker, text)

    # Step 2: Replace any remaining single newline (with optional surrounding spaces) with a single space.
    text = re.sub(r"[ \t]*\n[ \t]*", " ", text)

    # Step 3: Collapse multiple spaces into a single space.
    text = re.sub(r"[ \t]+", " ", text)

    # Step 4: Replace the marker with an actual newline (or any delimiter you prefer).
    text = text.replace(marker, "\n")

    # Optionally, trim leading and trailing whitespace.
    return text.strip()


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


def read_tex_file_content(file_path: str, extension: str = ".tex") -> str:
    """
    Attempts to read content from an input file.

    Args:
        file_path: Path to the input file
        extension: Default file extension to try (e.g., ".tex")

    Returns:
        str: Content of the file

    Raises:
        FileNotFoundError: If file doesn't exist or is a directory
    """
    # Clean up input
    file_path = str(file_path).strip()

    # Try both with and without extension
    paths_to_try = [file_path]
    if not file_path.endswith(extension):
        paths_to_try.append(file_path + extension)

    for path in paths_to_try:
        if os.path.exists(path):
            if os.path.isdir(path):
                continue
            return read_file(path)

    raise FileNotFoundError(f"Failed to read input file '{file_path}'")


def has_comment_on_sameline(content: str, pos: int) -> bool:
    """Check if there's an uncommented % before pos on the current line"""
    # Find start of current line
    line_start = content.rfind("\n", 0, pos)
    if line_start == -1:
        line_start = 0
    else:
        line_start += 1  # Move past the newline

    # Get content from start of current line to position
    line_before = content[line_start:pos]

    # Look for unescaped %
    i = 0
    while i < len(line_before):
        if line_before[i] == "%":
            if i == 0 or line_before[i - 1] != "\\":
                return True
        i += 1
    return False


def strip_latex_comments(text: str) -> str:
    r"""
    Remove all LaTeX comments (lines starting with % or inline comments after unescaped %)
    while preserving escaped \% characters.

    Args:
        text: Input LaTeX text

    Returns:
        Text with all comments removed
    """
    lines = []
    for line in text.splitlines():
        processed_line = ""
        i = 0
        while i < len(line):
            # Handle escaped %
            if i < len(line) - 1 and line[i : i + 2] == r"\%":
                processed_line += r"\%"
                i += 2
                continue
            # Handle unescaped %
            if line[i] == "%":
                break
            processed_line += line[i]
            i += 1
        lines.append(processed_line.rstrip())

    return "\n".join(lines)


def flatten_all_to_string(tokens: List[Dict | str | List] | str) -> str:
    if isinstance(tokens, str):
        return tokens

    def flatten_token(token):
        if isinstance(token, str):
            return token
        elif isinstance(token, list):
            return flatten_all_to_string(token)
        elif isinstance(token, dict) and isinstance(token.get("content"), list):
            return flatten_all_to_string(token["content"])
        else:
            return token["content"]

    return " ".join(flatten_token(token) for token in tokens)


def flatten_group_token(token: Dict) -> Dict | List[Dict]:
    if token.get("type") == "group" and isinstance(token["content"], list):
        flat_content = token["content"]
        if token.get("styles"):
            for content in flat_content:
                content_styles = content.get("styles", [])
                content["styles"] = token["styles"] + content_styles
        return flat_content
    return token


if __name__ == "__main__":
    text = r"% comment\n\begin{test}"
    pos = text.find(r"\begin")

    # Debug prints
    print(f"Full text: {repr(text)}")
    print(f"Position of \\begin: {pos}")
    line_start = text.rfind("\n", 0, pos) + 1
    print(f"Line start: {line_start}")
    line_before = text[line_start:pos]
    print(f"Line before: {repr(line_before)}")

    print(has_comment_on_sameline(text, text.find(r"\begin")))
