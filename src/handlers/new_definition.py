import re
from typing import Callable, Dict, Optional, Tuple
from src.handlers.base import TokenHandler
from src.tex_utils import extract_nested_content

# Compile patterns for definition commands
PATTERNS = {
    # Matches newcommand/renewcommand, supports both {\commandname} and \commandname syntax
    'newcommand': re.compile(r'\\(?:new|renew)command\*?(?:{\\([^}]+)}|\\([^\s{[]+))(?:\s*\[(\d+)\])?((?:\s*\[[^]]*\])*)\s*{'),
    
    # # UPDATE: newenvironment is handled in the environment handler
    # 'newenvironment': re.compile(r'\\(?:new|renew)environment\*?\s*{([^}]+)}'),
    
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