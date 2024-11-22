import re
from typing import Callable, Dict, Optional, Tuple
from src.handlers.base import TokenHandler
from src.tex_utils import extract_nested_content

POST_NEW_COMMAND_PATTERN_STR = r'\*?(?:{\\([^}]+)}|\\([^\s{[]+))(?:\s*\[(\d+)\])?((?:\s*\[[^]]*\])*)\s*{'

# Compile patterns for definition commands
PATTERNS = {
    # Matches newcommand/renewcommand, supports both {\commandname} and \commandname syntax
    'newcommand': re.compile(r'\\(?:new|renew|provide)command' + POST_NEW_COMMAND_PATTERN_STR),

    'declaremathoperator': re.compile(r'\\DeclareMathOperator' + POST_NEW_COMMAND_PATTERN_STR), # for math mode
    'declarerobustcommand': re.compile(r'\\DeclareRobustCommand' + POST_NEW_COMMAND_PATTERN_STR),
    
    # Matches \def commands - always with backslash before command name
    'def': re.compile(r'\\def\s*\\([^\s{#]+)(((?:#\d+|[^{])*)\s*{)'),
    
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
                # declaremathoperator is for math mde 
                if pattern_name == 'newcommand' or pattern_name.startswith('declare'):
                    return self._handle_newcommand(content, match)
                elif pattern_name == 'newtheorem':
                    return self._handle_newtheorem(match)
                elif pattern_name == 'def':
                    return self._handle_def(content, match)
        
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
            "num_args": 0,
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
    
    # parse \def\command(?#1#2){definition}
    # where #1, #2 are optional parameter markers
    # we need to make regex for usage pattern
    # if it is the last arg, and not wrapped in {}, then it is a delimiter
    # otherwise, it is a parameter
    def _handle_def(self, content: str, match) -> Tuple[Optional[Dict], int]:
        r"""Handle \def command definitions"""
        start_pos = match.end()
        definition, end_pos = extract_nested_content(content[start_pos - 1:])
        if definition is None:
            return None, start_pos

        # Get command name (will be clean now, without parameters)
        cmd_name = match.group(1) or match.group(2)
        if cmd_name.startswith('\\'): 
            cmd_name = cmd_name[1:]

        # Get parameter pattern (now properly separated)
        param_pattern = match.group(3).strip() if match.group(3) else ''
        
        # print("=== Debug ===")
        # print(f"Command name: {cmd_name}")  # Should now be clean, like "ratio"
        # print(f"Parameter pattern: {param_pattern}")  # Should be like "#1:#2"
        # print(f"Definition: {definition}")
        # print("Match groups:", match.groups())
        # print("============")

        usage_pattern = fr'{cmd_name}{param_pattern}'
        
        # Don't escape the entire pattern, instead handle delimiters and parameters separately
        parts = []
        current_pos = 0
        param_count = 0
        for param in re.finditer(r'#(\d)', usage_pattern):
            # Add everything before the parameter as escaped text
            before_param = usage_pattern[current_pos:param.start()]
            if before_param:
                parts.append(re.escape(before_param))
            
            # Add the parameter pattern to capture delimiters and parameters e.g. {xxx} or x 
            # e.g. \def\foo#1{bar #1} \foo{xxx} will match 'xxx' arg, \foo xaaa will match 'x' arg
            # Update regex to handle escaped braces and normal braces
            parts.append(r'\s*(?:\{((?:[^{}]|\\\{|\\\}|{[^{}]*})*)\}|([^\}]+?))')

            current_pos = param.end()
            param_count += 1
        
        # Add any remaining text after the last parameter
        if current_pos < len(usage_pattern):
            parts.append(re.escape(usage_pattern[current_pos:]))
        
        usage_pattern = ''.join(parts)
        # Add check at the very end to prevent partial matches (e.g., \foo matching \foobar)
        usage_pattern = r'\\' + usage_pattern + r'(?![a-zA-Z@])'

        token = {
            "type": "def",
            "name": cmd_name,
            "content": definition,
            "num_args": param_count,
            "usage_pattern": usage_pattern   
        }

        return token, start_pos + end_pos - 1


if __name__ == "__main__":
    handler = NewDefinitionHandler()

    def clean_groups(match):
        """Remove None values from regex match groups"""
        if match:
            return tuple(g for g in match.groups() if g is not None)
        return tuple()

    def check_usage(text, search):
        print("Checking", text, "with SEARCH:   ", search)
        token, end_pos = handler.handle(text)
        if token:
            if token["usage_pattern"]:
                regex = re.compile(token["usage_pattern"])
                match = regex.match(search)
                print(token["usage_pattern"], token["content"])
                if match:
                    print(clean_groups(match))
        print()

    # check_usage(r"\def\ratio#1:#2{#1 divided by #2}  % Usage: \ratio 3:4", r"\ratio{4}:{42}")
    # check_usage(r"\def\ratio#1:#2{#1 divided by #2}  % Usage: \ratio 3:4", r"\ratio55:42 ss")
    # check_usage(r"\def\foo!#1!{shout #1} sss", r"\foo! hello!!")
    # check_usage(r"\def\foo!#1!{shout #1} sss", r"\foo!{hell  o!}!")
    # check_usage(r"\def\swap#1#2{#2#1} bbb", r"\swap a b")
    # check_usage(r"\def\fullname#1#2{#1 #2}  % Usage: \fullname{John}{Doe}", r"\fullname{John}{Doe}")
    # check_usage(r"\def\pair(#1,#2){#1 and #2} bbb", r"\pair(asd sd ,b)  xx")
    # check_usage(r"\def\grab#1.#2]{#1 and #2}  % Usage: \grab first.second]", r"\grab first.second]")
    # check_usage(r"\def\until#1\end#2{This text until #1 #2}", r"\until some \end3 sss")
    # check_usage(r"\def\gaga{LADY GAGA}", r"\gaga")
    # check_usage(r"\def\gaga{LADY GAGA}", r"\gagaa")
    # check_usage(r"\def\fullname#1#2{#1 #2}", r"\fullname32")
    # check_usage(r"\def\until#1\end#2{This text until #1 #2}", r"\until some \end2")
    # check_usage(r"\def\norm#1{\left\|#1\right\|}", r"\norm{x}")
    # check_usage(r"\def\abs#1{\left|#1\right|}", r"\abs{x + y}")
    # check_usage(r"\def\set#1{\{#1\}}", r"\set{x \in \mathbb{R}}")

    # # Multi-parameter math operators
    # check_usage(r"\def\inner#1#2{\langle#1,#2\rangle}", r"\inner{u}{v}")
    # check_usage(r"\def\pfrac#1#2{\frac{\partial #1}{\partial #2}}", r"\pfrac{f}{x}")
    
    # # Subscript/superscript patterns
    # check_usage(r"\def\tensor#1_#2^#3{#1_{#2}^{#3}}", r"\tensor{T}_i^j")
    # check_usage(r"\def\evalat#1|#2{\left.#1\right|_{#2}}", r"\evalat{f(x)}|{x=0}")
    
    # # # Common text formatting
    # check_usage(r"\def\emphtext#1{\textit{\textbf{#1}}}", r"\emphtext{important}")
    
    # # Multiple optional parts
    # check_usage(r"\def\theorem#1[#2]#3{Theorem #1 (#2): #3}", r"\theorem{1}[Name]{Statement}")