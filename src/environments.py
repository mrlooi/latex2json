import re
from typing import Dict, Optional, List, Tuple
from src.tex_utils import extract_nested_content


class EnvironmentProcessor:
    def __init__(self):
        self.environments: Dict[str, Dict[str, any]] = {}

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
                    content = content[end_pos+1:]
                    args.append(arg)
                else:
                    args.append(None)
                    
            # Handle required arguments {arg}
            for _ in range(env_info['args']['num_args']):
                if content.startswith('{'):
                    arg, end_pos = extract_nested_content(content, '{', '}')
                    content = content[end_pos+1:]
                    args.append(arg)
                else:
                    args.append('')  # Empty string for missing required args
            
            # Process begin definition with arguments
            result = env_info['begin_def']
            for i, arg in enumerate(args, 1):
                if arg is not None:
                    # Replace unescaped #i with arg, preserve \#
                    result = re.sub(r'(?<!\\)#' + str(i), arg, result)
                    
            # Add content and end definition
            result += content + env_info['end_def']

            return result
        
        return text
