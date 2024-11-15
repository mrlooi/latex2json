from typing import Tuple

def find_matching_brace(text: str, start: int = 0) -> int:
    """
    Find the position of the matching closing brace, handling nested braces.
    Returns the position of the matching closing brace, or -1 if not found.
    """
    stack = []
    i = start
    while i < len(text):
        if text[i] == '{':
            stack.append(i)
        elif text[i] == '}':
            if not stack:
                return -1  # Unmatched closing brace
            stack.pop()
            if not stack:  # Found the matching brace
                return i
        i += 1
    return -1  # No matching brace found

def extract_nested_content(text: str, start: int) -> Tuple[str, int]:
    """
    Extract content between braces, handling nested braces.
    Returns (content, end_position) or (None, start) if no valid content found.
    """
    if start >= len(text) or text[start] != '{':
        return None, start
        
    end_pos = find_matching_brace(text, start)
    if end_pos == -1:
        return None, start
        
    # Return content without the braces and the end position
    return text[start + 1:end_pos], end_pos