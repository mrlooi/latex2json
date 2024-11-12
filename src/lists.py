import re
from typing import List, Dict, Union

def parse_item(content: str) -> Dict[str, str]:
    """Parse a single \item command and its content"""
    # Check for nested environments
    nested_env_match = re.search(r'\\begin\{(itemize|enumerate|description)\}(.*?)\\end\{\1\}', content, re.DOTALL)
    if nested_env_match:
        env_type = nested_env_match.group(1)
        nested_content = nested_env_match.group(2)
        # Split content before and after the nested list
        pre_content = content[:nested_env_match.start()].strip()
        post_content = content[nested_env_match.end():].strip()
        
        return {
            "type": "item",
            "content": pre_content,
            "nested": parse_list_environment(nested_content, env_type),
            "post_content": post_content if post_content else None
        }
    return {
        "type": "item",
        "content": content.strip()
    }

def parse_description_item(content: str) -> Dict[str, str]:
    """Parse a description \item[term] content"""
    # Extract [term] if present
    term_match = re.match(r'\[(.*?)\]\s*(.*)', content)
    if term_match:
        return {
            "type": "item",
            "term": term_match.group(1).strip(),
            "content": term_match.group(2).strip()
        }
    return parse_item(content)

def parse_list_environment(content: str, list_type: str) -> Dict[str, Union[str, List]]:
    """Parse itemize, enumerate, or description environments"""
    # Extract optional arguments if present (e.g., [label=(\alph*)])
    options_match = re.match(r'\[(.*?)\](.*)', content, re.DOTALL)
    options = options_match.group(1) if options_match else None
    content = options_match.group(2) if options_match else content
    
    # Split into items, but be careful not to split within nested environments
    items = []
    current_item = []
    depth = 0
    
    for line in content.split('\n'):
        if '\\begin{' in line:
            depth += 1
        if '\\end{' in line:
            depth -= 1
        
        if depth == 0 and '\\item' in line:
            if current_item:
                items.append('\n'.join(current_item))
            current_item = [line.split('\\item', 1)[1]]
        else:
            if current_item or depth > 0:
                current_item.append(line)
    
    if current_item:
        items.append('\n'.join(current_item))
    
    # Clean up items
    items = [item.strip() for item in items if item.strip()]
    
    result = {
        "type": list_type,
        "items": [
            parse_description_item(item) if list_type == "description" 
            else parse_item(item) 
            for item in items
        ]
    }
    
    if options:
        result["options"] = options
        
    return result