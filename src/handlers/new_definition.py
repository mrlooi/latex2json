import re
from typing import Callable, Dict, Optional, Tuple
from src.handlers.base import TokenHandler
from src.tex_utils import extract_nested_content

# Compile patterns for definition commands
PATTERNS = {
    # Matches newcommand/renewcommand, supports both {\commandname} and \commandname syntax
    'newcommand': re.compile(r'\\(?:new|renew)command\*?(?:{\\([^}]+)}|\\([^\s{[]+))(?:\s*\[(\d+)\])?((?:\s*\[[^]]*\])*)\s*{'),
    
    # Matches newenvironment up to \newenvironment{name} only
    'newenvironment': re.compile(r'\\(?:new|renew)environment\*?\s*{([^}]+)}'),
    
    # Matches newtheorem with all its optional arguments
    'newtheorem': re.compile(r'\\newtheorem{([^}]*)}(?:\[([^]]*)\])?{([^}]*)}(?:\[([^]]*)\])?'),
}

class NewDefinitionHandler(TokenHandler):
    def __init__(self):
        pass

    def can_handle(self, content: str) -> bool:
        """Check if the content contains any definition commands"""
        return any(pattern.match(content) for pattern in PATTERNS.values())
    
    def handle(self, content: str) -> Tuple[Optional[Dict], int]:
        """Handle definition commands and return appropriate token with definition details"""
        for pattern_name, pattern in PATTERNS.items():
            match = pattern.match(content)
            if match:
                if pattern_name == 'newcommand':
                    return self._handle_newcommand(content, match)
                elif pattern_name == 'newenvironment':
                    return self._handle_newenvironment(content, match)
                elif pattern_name == 'newtheorem':
                    return self._handle_newtheorem(match)
        
        return None, 0
    
    def _handle_newcommand(self, content: str, match) -> Tuple[Optional[Dict], int]:
        """Handle \newcommand and \renewcommand definitions"""
        start_pos = match.end() 
        definition, end_pos = extract_nested_content(content[start_pos - 1:]) # -1 to go back {
        if definition is None:
            return None, start_pos
        
        # Get command name from either group 1 (with braces) or group 2 (without braces)
        cmd_name = match.group(1) or match.group(2)
        if cmd_name.startswith('\\'): # Handle case where command name starts with backslash
            cmd_name = cmd_name[1:]
        
        token = {
            "type": "newcommand",
            "name": cmd_name,
            "content": definition,
            "num_args": None,
            "defaults": []
        }
        
        # Add number of arguments if specified
        if match.group(3):
            token["num_args"] = int(match.group(3))
        
        # Add default values if present
        if match.group(4):
            defaults = []
            for default in re.finditer(r'\[(.*?)\]', match.group(4)):
                defaults.append(default.group(1))
            if defaults:
                token["defaults"] = defaults
        
        return token, start_pos + end_pos - 1
    
    def _handle_newenvironment(self, content: str, match) -> Tuple[Optional[Dict], int]:
        """Handle \newenvironment definitions"""
        env_name = match.group(1)
        current_pos = match.end()
        
        # Store environment definition
        token = {
            "type": "newenvironment",
            "begin_def": "",
            "end_def": "",
            "name": env_name,
            "args": [],
            "optional_args": []
        }
        
        # Look for optional arguments [n][default]...
        while current_pos < len(content):
            # Skip whitespace
            while current_pos < len(content) and content[current_pos].isspace():
                current_pos += 1
                
            if current_pos >= len(content) or content[current_pos] != '[':
                break
                
            # Find matching closing bracket
            bracket_count = 1
            search_pos = current_pos + 1
            bracket_start = search_pos
            
            while search_pos < len(content) and bracket_count > 0:
                if content[search_pos] == '[':
                    bracket_count += 1
                elif content[search_pos] == ']':
                    bracket_count -= 1
                search_pos += 1
                
            if bracket_count == 0:
                # Successfully found matching bracket
                arg = content[bracket_start:search_pos-1].strip()
                
                # First bracket usually contains number of arguments
                if len(token['args']) == 0 and arg.isdigit():
                    token['args'] = [f'#{i+1}' for i in range(int(arg))]
                else:
                    token['optional_args'].append(arg)
                
                current_pos = search_pos
            else:
                break
        
        # Get begin definition
        next_brace = content[current_pos:].find('{')
        if next_brace == -1:
            return None, current_pos

        begin_def, first_end = extract_nested_content(content[current_pos + next_brace:])
        if begin_def is None:
            return None, current_pos
        token['begin_def'] = begin_def.strip()
        
        first_end = current_pos + next_brace + first_end
        
        # Find next brace for end definition
        next_brace = content[first_end:].find('{')
        if next_brace == -1:
            return None, first_end
        next_pos = first_end + next_brace

        end_def, final_end = extract_nested_content(content[next_pos:])
        if end_def is None:
            return None, first_end
        
        token['end_def'] = end_def.strip()
        final_end = next_pos + final_end
        
        return token, final_end
    
    def _handle_newtheorem(self, match) -> Tuple[Optional[Dict], int]:
        """Handle \newtheorem definitions"""
        token = {
            "type": "theorem",
            "name": match.group(1),
            "title": match.group(3)
        }
        
        # Handle optional counter specification
        if match.group(2):
            token["counter"] = match.group(2)
            
        # Handle optional numbering within
        if match.group(4):
            token["within"] = match.group(4)
            
        return token, match.end() 
    
if __name__ == "__main__":
    handler = NewDefinitionHandler()
    token, pos = handler.handle(r"\newcommand{\cmd")
    print(token, pos)

    print(handler.can_handle(r"\newcommand{\cmd"))