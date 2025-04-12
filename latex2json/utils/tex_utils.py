from typing import Callable, Dict, List, Tuple
import re
import os

from latex2json.utils.encoding import detect_encoding, read_file


def count_preceding_backslashes(text: str, pos: int) -> int:
    """Count number of backslashes immediately preceding the position."""
    count = 0
    pos -= 1
    while pos >= 0 and text[pos] == "\\":
        count += 1
        pos -= 1
    return count


def is_escaped(pos: int, text: str) -> bool:
    """Check if character at position is escaped by backslashes."""
    return count_preceding_backslashes(text, pos) % 2 == 1


def find_matching_delimiter(
    text: str, open_delim: str = "{", close_delim: str = "}", start: int = 0
) -> Tuple[int, int]:
    """
    Find the position of the matching closing delimiter, handling nested delimiters.
    Returns a tuple of (start_pos, end_pos) where:
        - start_pos is the position of the opening delimiter
        - end_pos is the position after the matching closing delimiter
    Returns (-1, -1) if no valid delimiters found.
    Handles:
        - Nested delimiters
        - Escaped characters (odd number of backslashes)
    """
    # Skip leading whitespace
    while start < len(text) and text[start].isspace():
        start += 1

    if start >= len(text) or text[start] != open_delim:
        return -1, -1

    stack = []
    i = start
    while i < len(text):
        if text[i] == open_delim and not is_escaped(i, text):
            stack.append(i)
        elif text[i] == close_delim and not is_escaped(i, text):
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

    # Find the first beginning pattern
    begin_match = begin_pattern.search(text)
    if not begin_match:
        return -1, -1, ""

    nesting_level = 1
    current_pos = begin_match.end()
    content_start = current_pos
    start_pos = begin_match.start()

    while nesting_level > 0 and current_pos < len(text):
        # Find next begin/end patterns
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


def count_preceding_backslashes(text: str, pos: int) -> int:
    """Count number of backslashes immediately preceding the position."""
    count = 0
    pos -= 1
    while pos >= 0 and text[pos] == "\\":
        count += 1
        pos -= 1
    return count


def is_escaped(pos: int, text: str) -> bool:
    """Check if character at position is escaped by backslashes."""
    return count_preceding_backslashes(text, pos) % 2 == 1


def strip_latex_comments(text: str) -> str:
    r"""
    Remove all LaTeX comments while preserving escaped \% characters.

    A % starts a comment if it is preceded by an even number (including zero)
    of consecutive backslashes. An odd number indicates that the % is escaped.

    Args:
        text: Input LaTeX text

    Returns:
        Text with all comments removed.
    """
    lines = []
    for line in text.splitlines():
        result = []
        i = 0
        while i < len(line):
            if line[i] == "%":
                # Use helper to decide if this % is escaped.
                if not is_escaped(i, line):
                    break  # Unescaped % starts a comment
                else:
                    # Escaped percent: include literal %
                    result.append("%")
                    i += 1
                    continue
            else:
                result.append(line[i])
                i += 1
        lines.append("".join(result).rstrip())
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


def check_delimiter_balance(
    text: str, open_delim: str = "{", close_delim: str = "}"
) -> bool:
    """Check if delimiters are properly balanced in the text, handling escapes."""
    stack = []
    i = 0
    while i < len(text):
        if text[i] == open_delim and not is_escaped(i, text):
            stack.append(text[i])
        elif text[i] == close_delim and not is_escaped(i, text):
            if not stack:
                return False
            stack.pop()
        i += 1
    return len(stack) == 0


def find_delimiter_end(content: str, start_pos: int, delimiter: str) -> int:
    """
    Find the end position of a delimiter (like $ or $$), respecting nested braces.
    Returns the position after the closing delimiter, or -1 if not found.
    """
    stack = []
    i = start_pos
    while i < len(content):
        if content[i] == "{" and not is_escaped(i, content):
            stack.append("{")
        elif content[i] == "}" and not is_escaped(i, content):
            if stack:
                stack.pop()
        elif (
            content[i:].startswith(delimiter)
            and not is_escaped(i, content)
            and not stack  # Only match delimiter when not inside braces
        ):
            return i + len(delimiter)
        i += 1
    return -1


def extract_equation_content(content: str, delimiter: str) -> Tuple[str, int]:
    """Extract equation content and find proper end position.

    Args:
        content: Input text containing equation
        delimiter: Equation delimiter ($ or $$)

    Returns:
        Tuple[str, int]: (equation content, end position)
    """
    if not content.startswith(delimiter):
        return "", 0

    start = len(delimiter)
    end_pos = find_delimiter_end(content, start, delimiter)

    if end_pos < 0:
        return "", 0

    equation = content[start : end_pos - len(delimiter)].strip()
    return equation, end_pos


def extract_args(content: str, req_args=0, opt_args=0):
    """
    Opt args come first, then req args.
    """
    end_pos = 0
    opt = []
    if opt_args > 0:
        opt, end_pos = extract_nested_content_sequence_blocks(
            content, "[", "]", max_blocks=opt_args
        )
        if end_pos > 0:
            content = content[end_pos:]

    req = []
    if req_args > 0:
        req, end_pos = extract_nested_content_sequence_blocks(
            content, "{", "}", max_blocks=req_args
        )
        if end_pos > 0:
            content = content[end_pos:]

    return {"req": req, "opt": opt}, end_pos


NO_ESC_HASH_NUMBER_PATTERN = re.compile(r"(?<!\\)(#+)(\d+)")

HASH_NUMBER_PATTERN = re.compile(r"(\\#)|(#+)(\d+)")


def check_string_has_hash_number(text: str) -> bool:
    return bool(NO_ESC_HASH_NUMBER_PATTERN.search(text))


def substitute_args(definition: str, args: List[str], math_mode=False) -> str:
    r"""
    Substitute argument patterns in LaTeX command definitions.
    First finds the smallest sequence of unescaped #s in the definition (e.g. #1, ##1, or ###1),
    then only substitutes patterns with exactly that number of #s.
    Escaped \# characters are preserved and not counted in the sequence.

    When math_mode is True, the two surrounding characters (if any) are checked; if either
    is alphabetic then the substitution is wrapped in curly braces.
    """
    if not args:
        return definition

    # Use a regex that only finds unescaped '#' sequences.
    matches = list(NO_ESC_HASH_NUMBER_PATTERN.finditer(definition))
    if not matches:
        return definition
    min_hashes = min((len(m.group(1)) for m in matches), default=0)
    if min_hashes < 1:
        return definition

    def sub_fn(match):
        # If group(1) matched, it's an escaped hash, so leave it as is.
        if match.group(1) is not None:
            return match.group(0)
        # Otherwise, it's an unescaped substitution token.
        hashes = match.group(2)
        number = match.group(3)
        if len(hashes) == min_hashes:
            arg_index = int(number) - 1  # convert to 0-based index
            if arg_index >= len(args):
                return match.group(0)
            # Retrieve the replacement text.
            replacement = "" if args[arg_index] is None else args[arg_index]

            # If math_mode is enabled, check surrounding characters.
            if math_mode and replacement:
                start_index = match.start()
                end_index = match.end()
                char_before = definition[start_index - 1] if start_index > 0 else ""
                char_after = (
                    definition[end_index] if end_index < len(definition) else ""
                )
                # If either the preceding or following character is alphabetic,
                # wrap the replacement in braces.
                if (char_before.isalpha()) or (char_after.isalpha()):
                    replacement = "{" + replacement + "}"
            return replacement
        else:
            return match.group(0)

    return HASH_NUMBER_PATTERN.sub(sub_fn, definition)


def extract_delimited_args(
    content: str, delimiter_pattern: str
) -> Tuple[List[str | None], int]:
    """
    Extract nested content based on a pattern of delimiters.

    Args:
        content: Input text to process
        delimiter_pattern: String of opening delimiters where:
            '{' indicates required curly braces
            '[' indicates optional square brackets

    Returns:
        Tuple of (extracted_contents, end_position) where:
            - extracted_contents is a list of contents up until first missing required arg
            - end_position is the position after the last successfully processed delimiter

    Example:
        extract_delimited_args("foo{a}\n[b]{c}", "{[{")
        -> (["a", "b", "c"], 13)

        extract_delimited_args("foo{a}", "{[{")
        -> (["a"], 5)  # Stops at first missing required argument
    """
    results = []
    current_pos = 0

    total_end_pos = 0
    for delimiter in delimiter_pattern:
        # Skip all whitespace characters (including newlines)
        while current_pos < len(content) and content[current_pos].isspace():
            current_pos += 1

        if current_pos >= len(content):
            break

        current_char = content[current_pos]
        if current_char not in ["{", "["]:
            current_pos -= 1
            break

        if delimiter == "{":
            # Required argument
            content_slice = content[current_pos:]
            nested_content, end_pos = extract_nested_content(content_slice, "{", "}")
            if nested_content is None:
                return results, current_pos  # Stop at first missing required arg
            results.append(nested_content)
            current_pos += end_pos
            total_end_pos = current_pos
        elif delimiter == "[":
            # Optional argument
            content_slice = content[current_pos:]
            nested_content, end_pos = extract_nested_content(content_slice, "[", "]")
            if nested_content is not None:
                results.append(nested_content)
                current_pos += end_pos
                total_end_pos = current_pos
            else:
                results.append(None)

    return results, total_end_pos


if __name__ == "__main__":
    text = r"{ssss"
    print(find_matching_delimiter(text, "{", "}"))
