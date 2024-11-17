from typing import Tuple

def find_matching_delimiter(text: str, open_delim: str='{', close_delim: str='}', start: int = 0) -> int:
    """
    Find the position of the matching closing delimiter, handling nested delimiters.
    Returns the position of the matching closing delimiter, or -1 if not found.
    """
    stack = []
    i = start
    while i < len(text):
        # Check for escaped delimiters
        if i > 0 and text[i-1] == '\\':
            i += 1
            continue
            
        if text[i] == open_delim:
            stack.append(i)
        elif text[i] == close_delim:
            if not stack:
                return -1  # Unmatched closing delimiter
            stack.pop()
            if not stack:  # Found the matching delimiter
                return i
        i += 1
    return -1  # No matching delimiter found

def extract_nested_content(text: str, open_delim: str='{', close_delim: str='}') -> Tuple[str, str]:
    """
    Extract content between delimiters, handling nesting.
    Returns (content, remaining_text) or (None, text) if no valid content found.
    
    Args:
        text: The input text
        open_delim: Opening delimiter (e.g., '{' or '[')
        close_delim: Closing delimiter (e.g., '}' or ']')
    """
    if not text.startswith(open_delim):
        return None, text
        
    end_pos = find_matching_delimiter(text, open_delim, close_delim)
    if end_pos == -1:
        return None, text
        
    # Return content without the delimiters and the remaining text
    content = text[1:end_pos]
    return content, end_pos
