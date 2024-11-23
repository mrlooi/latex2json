# src/commands.py

import re
from typing import List, Dict, Optional
from src.patterns import NEWLINE_PATTERN
from src.latex_maps._uni2latexmap import uni2latex
from src.latex_maps._uni2latexmap_xml import uni2latex as uni2latex_xml
from collections import OrderedDict

class CommandProcessor:
    def __init__(self):
        self.commands: Dict[str, Dict[str, any]] = {}
        
        # Add built-in newline normalization command using pre-compiled pattern
        self._init_newline_command()
        
        # Initialize unicode conversion maps and patterns
        self.latex2unicode = self._create_latex_to_unicode_map()
        self.unicode_patterns = self._create_unicode_patterns()

    def _init_newline_command(self):
        newline_command = {
            'definition': '\n',
            'args': {'num_args': 0, 'defaults': [], 'required_args': 0},
            'pattern': NEWLINE_PATTERN,
            'handler': lambda m: '\n'
        }
        self.commands['newline'] = newline_command

    def clear(self):
        self.commands = {}
        self._init_newline_command()

    def has_command(self, command_name: str) -> bool:
        return command_name in self.commands

    def process_command_definition(
        self, 
        command_name: str, 
        definition: str, 
        num_args: Optional[int] = None, 
        defaults: Optional[List[str]] = []
    ) -> None:
        """Store a new or renewed command definition"""
        command = {'definition': definition}
        
        # Process arguments
        args = {}
        if num_args is not None:
            args['num_args'] = int(num_args)
        else:
            used_args = re.findall(r'#(\d+)', definition)
            args['num_args'] = max(int(x) for x in used_args) if used_args else 0

        args['defaults'] = defaults
        args['required_args'] = args['num_args'] - len(defaults)

        command['args'] = args

        # Balance braces and add missing ones
        stack = []
        for char in definition:
            if char == '{':
                stack.append(char)
            elif char == '}':
                if stack:
                    stack.pop()
                else:
                    raise ValueError("Unbalanced closing brace in definition.")
        if stack:
            definition += '}' * len(stack)

        # Create and store the handler with the command
        pattern, handler = self._create_command_handler(command_name, command)
        command['pattern'] = pattern
        command['handler'] = handler

        self.commands[command_name] = command
        return len(stack)

    def _substitute_args(self, definition: str, args: List[str]) -> str:
        """Substitute #1, #2, etc. with the provided arguments in order"""
        result = definition
        # Sort in reverse order to handle #10 before #1, etc.
        for i, arg in enumerate(args, 1):
            if arg is not None:  # Only substitute if we have a value
                result = result.replace(f'#{i}', arg)
        return result

    def _create_command_handler(self, cmd_name: str, cmd_info: dict) -> tuple[re.Pattern, callable]:
        """Creates and returns a cached (pattern, handler) tuple for a command"""
        pattern = r'\\' + re.escape(cmd_name)
        num_args = cmd_info['args']['num_args']
        
        if num_args == 0:
            regex = re.compile(pattern)
            handler = lambda m: cmd_info['definition']
            return regex, handler
            
        # Build pattern for commands with arguments
        num_optional = len(cmd_info['args'].get('defaults', []))
        pattern += ''.join(r'(?:\[(.*?)\])?' for _ in range(num_optional))
        num_required = cmd_info['args']['required_args']
        pattern += ''.join(r'\{(.*?)\}' for _ in range(num_required))
        # use dotall flag to allow for multiline matches
        regex = re.compile(pattern, re.DOTALL)

        def handler(match):
            groups = match.groups()
            args = []
            
            # Handle optional args
            if num_optional:
                defaults = cmd_info['args']['defaults']
                args.extend(groups[i] if groups[i] is not None else defaults[i] 
                          for i in range(num_optional))
            
            # Add required args
            args.extend(groups[num_optional:num_optional + num_required])
            
            return self._substitute_args(cmd_info['definition'], args)

        return regex, handler

    def _create_latex_to_unicode_map(self):
        latex2unicode = OrderedDict()
        
        # Load from XML mappings first
        for k, v in uni2latex_xml.items():
            latex2unicode[v] = k
        
        # Then load from regular mappings, skipping duplicates and ensuremath
        for k, v in uni2latex.items():
            if v in latex2unicode or v.startswith('\\ensuremath'):
                continue
            latex2unicode[v] = k
            
        return latex2unicode

    def _create_unicode_patterns(self):
        patterns = []
        
        # Create patterns for each command
        for cmd in self.latex2unicode.keys():
            if cmd.startswith('\\') or cmd.startswith('{'):
                # Add negative lookahead to prevent partial matches
                escaped = re.escape(cmd) + r'(?![a-zA-Z])'
                patterns.append(escaped)
        
        # Compile into single pattern if we have any patterns
        if patterns:
            return re.compile('|'.join(patterns))
        return None

    def expand_commands(self, text: str, ignore_unicode: bool = False) -> tuple[str, int]:
        """Recursively expand defined commands in the text until no further expansions are possible."""
        # First handle all regular command expansions
        previous_text = None
        match_count = 0
        while previous_text != text:
            previous_text = text
            for cmd in self.commands.values():
                text = cmd['pattern'].sub(cmd['handler'], text)
                if previous_text != text:
                    match_count += 1
        
        # Finally, handle unicode conversions
        if not ignore_unicode and self.unicode_patterns:
            text = self.unicode_patterns.sub(
                lambda m: chr(self.latex2unicode[m.group(0)]), 
                text
            )
        
        return text, match_count
