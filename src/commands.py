# src/commands.py

import re
from typing import List, Dict, Optional

class CommandProcessor:
    def __init__(self):
        self.commands: Dict[str, Dict[str, any]] = {}

    def process_command_definition(
        self, 
        command_name: str, 
        definition: str, 
        num_args: Optional[str] = None, 
        defaults_str: Optional[str] = None
    ) -> None:
        """Store a new or renewed command definition"""
        args = {}
        if num_args:
            args['num_args'] = int(num_args)
        else:
            used_args = re.findall(r'#(\d+)', definition)
            args['num_args'] = max(int(x) for x in used_args) if used_args else 0

        if defaults_str:
            defaults = re.findall(r'\[([^]]*)\]', defaults_str)
            args['defaults'] = [d if d else None for d in defaults]
            args['required_args'] = args['num_args'] - len(args['defaults'])
        else:
            args['defaults'] = []
            args['required_args'] = args['num_args']

        # Balance braces using a stack
        # this is added to handle cases where the definition is missing closing braces
        # which unfortunately regex may not always handle
        stack = []
        for char in definition:
            if char == '{':
                stack.append(char)
            elif char == '}':
                if stack:
                    stack.pop()
                else:
                    # Unexpected closing brace
                    raise ValueError("Unbalanced closing brace in definition.")

        # Add the necessary closing braces
        if stack:
            definition += '}' * len(stack)

        self.commands[command_name] = {
            'definition': definition,
            'args': args
        }

        return len(stack)

    def _substitute_args(self, definition: str, args: List[str]) -> str:
        """Substitute #1, #2, etc. with the provided arguments in order"""
        result = definition
        # Sort in reverse order to handle #10 before #1, etc.
        for i, arg in enumerate(args, 1):
            if arg is not None:  # Only substitute if we have a value
                result = result.replace(f'#{i}', arg)
        return result

    def expand_commands(self, text: str) -> str:
        """
        Recursively expand defined commands in the text until no further expansions are possible.
        
        Args:
            text (str): The text containing LaTeX commands to expand.
        
        Returns:
            str: The text with all defined commands expanded.
        """
        previous_text = None
        while previous_text != text:
            previous_text = text
            for cmd_name, cmd_info in self.commands.items():
                pattern = r'\\' + re.escape(cmd_name)
                
                if cmd_info['args']['num_args'] > 0:
                    # Build regex pattern to match optional and required arguments
                    num_optional = len(cmd_info['args'].get('defaults', []))
                    pattern += ''.join([r'(?:\[(.*?)\])?' for _ in range(num_optional)])
                    num_required = cmd_info['args']['required_args']
                    pattern += ''.join([r'\{(.*?)\}' for _ in range(num_required)])

                    # Compile the regex pattern
                    regex = re.compile(pattern)

                    def replace_with_args(match):
                        groups = match.groups()

                        # Extract optional arguments with defaults
                        args = []
                        if num_optional:
                            defaults = cmd_info['args']['defaults']
                            for i in range(num_optional):
                                arg = groups[i] if groups[i] is not None else defaults[i]
                                args.append(arg)

                        # Extract required arguments
                        args.extend(groups[num_optional:num_optional + num_required])

                        # Substitute arguments into the command definition
                        expanded = self._substitute_args(cmd_info['definition'], args)
                        return expanded

                    # Replace all occurrences of the command with its expanded form
                    text = regex.sub(replace_with_args, text)
                else:
                    # Commands without arguments
                    text = re.sub(pattern, lambda m: cmd_info['definition'], text)
        return text