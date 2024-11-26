import re
from typing import Callable, Dict, List, Optional, Tuple
from src.handlers.base import TokenHandler
from src.tex_utils import extract_nested_content


ENVIRONMENT_PATTERN = re.compile(r'\\begin\{([^}]*)\}(.*?)\\end\{([^}]*)\}', re.DOTALL)

NEW_ENVIRONMENT_PATTERN = re.compile(r'\\(?:new|renew|provide)environment\*?\s*{([^}]+)}')

LIST_ENVIRONMENTS = ['itemize', 'enumerate', 'description']

# Map environment names to their types
ENV_TYPES = {
    "document": "document",
    "abstract": "abstract",
    "thebibliography": "bibliography",
    "table": "table",
    "subtable": "table",
    "subsubtable": "table",
    "figure": "figure",
    "subfigure": "figure",
    "subfloat": "figure",  # another common figure subdivision
    "quote": "quote",
    **{env: "list" for env in LIST_ENVIRONMENTS}
}

class EnvironmentProcessor:
    def __init__(self):
        self.environments: Dict[str, Dict[str, any]] = {}

    def clear(self):
        self.environments = {}

    def process_environment_definition(
        self,
        env_name: str,
        begin_def: str,
        end_def: str,
        num_args: Optional[int] = None,
        optional_args: Optional[List[str]] = None
    ) -> None:
        """Store a new or renewed environment definition"""
        environment = {
            'name': env_name,
            'begin_def': begin_def,
            'end_def': end_def,
            'args': {
                'num_args': int(num_args) if num_args else 0,
                'optional_args': optional_args or []
            }
        }

        self.environments[env_name] = environment

    def has_environment(self, env_name: str) -> bool:
        return env_name in self.environments

    def expand_environments(self, env_name: str, text: str) -> str:
        """Expand defined environments in the text
        
        Args:
            env_name: Name of the environment to expand
            text: The content inside the environment (between begin/end tags)
            
        Returns:
            The processed content with the environment expanded
        """
        if self.has_environment(env_name):
            env_info = self.environments[env_name]
            
            # Extract arguments and content
            args = []
            content = text
            
            # Handle optional arguments [arg]
            for _ in env_info['args']['optional_args']:
                if content.startswith('['):
                    arg, end_pos = extract_nested_content(content, '[', ']')
                    content = content[end_pos:]
                    args.append(arg)
                else:
                    args.append(None)
                    
            # Handle required arguments {arg}
            for _ in range(env_info['args']['num_args']):
                if content.startswith('{'):
                    arg, end_pos = extract_nested_content(content, '{', '}')
                    content = content[end_pos:]
                    args.append(arg)
                else:
                    args.append('')  # Empty string for missing required args
            
            # Process begin definition with arguments
            result = env_info['begin_def'] + " " # add trailing space to pad
            for i, arg in enumerate(args, 1):
                if arg is not None:
                    # Replace unescaped #i with arg, preserve \#
                    result = re.sub(r'(?<!\\)#' + str(i), arg, result)
                    
            # Add content and end definition
            result += content + env_info['end_def']

            return result
        
        return text

class BaseEnvironmentHandler(TokenHandler):
    def __init__(self):
        super().__init__()

        # Precompile frequently used patterns
        self._env_pattern_cache = {}  # Cache for environment patterns

    def _find_matching_env_block(self, text: str, env_name: str, start_pos: int = 0) -> int:
        """Find the matching end{env_name} for a begin{env_name}, handling nested environments"""
        # Cache the compiled pattern for this environment
        if env_name not in self._env_pattern_cache:
            self._env_pattern_cache[env_name] = re.compile(rf'\\(begin|end)\{{{env_name}}}')
        
        pattern = self._env_pattern_cache[env_name]
        nesting_level = 1
        current_pos = start_pos
        
        while nesting_level > 0 and current_pos < len(text):
            match = re.search(pattern, text[current_pos:])
            if not match:
                return -1  # No matching end found
            
            current_pos += match.start() + 1
            if match.group(1) == 'begin':
                nesting_level += 1
            else:  # 'end'
                nesting_level -= 1
                
            if nesting_level == 0:
                return current_pos - 1
            current_pos += len(match.group(0)) - 1
            
        return -1 if nesting_level > 0 else current_pos

    def can_handle(self, content: str) -> bool:
        return ENVIRONMENT_PATTERN.match(content) is not None

    def _handle_environment(self, env_name: str, inner_content: str) -> None:
        token = {
            "type": "environment",
            "name": env_name
        }
     
        env_type = ENV_TYPES.get(env_name, "environment")
        token["type"] = env_type
        if env_type not in ["list", "table", "figure"]:
            token["name"] = env_name
            
        # Extract title if present (text within square brackets after environment name)
        title, end_pos = extract_nested_content(inner_content, '[', ']')
        if title: 
            inner_content = inner_content[end_pos:]
            token["title"] = title
        
        # Extract optional arguments
        args, end_pos = extract_nested_content(inner_content, '{', '}')
        if args:
            inner_content = inner_content[end_pos:].strip()

        # DEPRECATED: Label handling is now done independently through _handle_label()
        # # Extract any label if present
        # label_match = re.search(LABEL_PATTERN, inner_content)
        # label = label_match.group(1) if label_match else None
        
        # # Remove label from inner content before parsing
        # if label_match:
        #     inner_content = inner_content.replace(label_match.group(0), '').strip()
        
        token["content"] = inner_content

        return token
    
    def handle(self, content: str) -> Tuple[Optional[Dict], int]:
        match = ENVIRONMENT_PATTERN.match(content)
        if match:
            env_name = match.group(1).strip()
            # Find the correct ending position for this environment
            start_pos = match.start(2)
            end_pos = self._find_matching_env_block(content, env_name, start_pos)

            if end_pos == -1:
                # No matching end found, treat as plain text
                return match.group(0), match.end()
            else:
                # Extract content between begin and end
                inner_content = content[start_pos:end_pos].strip()
                
                env_token = self._handle_environment(env_name, inner_content)

                current_pos = end_pos + len(f"\\end{{{env_name}}}")
                return env_token, current_pos
        
        return None, 0
    
class EnvironmentHandler(BaseEnvironmentHandler):
    def __init__(self):
        super().__init__()
    
        self.environment_processor = EnvironmentProcessor()

    @property
    def environments(self):
        return self.environment_processor.environments
    
    def clear(self):
        super().clear()
        self.environment_processor.clear()
    
    def _handle_newenvironment_def(self, content: str, match) -> Tuple[Optional[Dict], int]:
        """Handle \newenvironment definitions"""
        env_name = match.group(1)
        current_pos = match.end()
        
        # Store environment definition
        token = {
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

    def can_handle(self, content: str) -> bool:
        return super().can_handle(content) or NEW_ENVIRONMENT_PATTERN.match(content) is not None
    
    def _handle_environment(self, env_name: str, inner_content: str) -> None:
        if self.environment_processor.has_environment(env_name):
            # check if expanded and changed
            inner_content = self.environment_processor.expand_environments(env_name, inner_content)
            return {
                "type": "environment",
                "name": env_name,
                "content": inner_content
            }
        
        return super()._handle_environment(env_name, inner_content)

    def handle(self, content: str) -> Tuple[Optional[Dict], int]:
        new_env_match = NEW_ENVIRONMENT_PATTERN.match(content)
        if new_env_match:
            token, end_pos = self._handle_newenvironment_def(content, new_env_match)
            if token:
                env_name = token['name']
                self.environment_processor.process_environment_definition(env_name, token["begin_def"], token["end_def"], len(token["args"]), token["optional_args"])
            return None, end_pos
        
        return super().handle(content)


if __name__ == "__main__":
    handler = EnvironmentHandler()

    # text = r"""
    # \renewenvironment{boxed}[2][This is a box]
    # {
    #     \begin{center}
    #     Argument 1 (\#1)=#1\\[1ex]
    #     \begin{tabular}{|p{0.9\textwidth}|}
    #     \hline\\
    #     Argument 2 (\#2)=#2\\[2ex]
    # }
    # { 
    #     \\\\\hline
    #     \end{tabular} 
    #     \end{center}
    # }

    # \begin{boxed}[BOX]{BOX2}
    # This text is \textit{inside} the environment.
    # \end{boxed}
    # """.strip()

    # token, end_pos = handler.handle(text)
    # print(handler.handle(text[end_pos:].strip()))

    content = r"\newenvironment{test}{begin def}{end def}"
    print(handler.handle(content))
