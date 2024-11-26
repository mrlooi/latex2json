# src/commands.py

import re
from typing import List, Dict, Optional
from src.patterns import NEWLINE_PATTERN
from src.latex_maps.latex_unicode_converter import LatexUnicodeConverter
from collections import OrderedDict

def substitute_args(definition: str, args: List[str]) -> str:
    """Substitute #1, #2, etc. with the provided arguments in order"""
    result = definition
    # Sort in reverse order to handle #10 before #1, etc.
    for i, arg in enumerate(args, 1):
        if arg is not None:  # Only substitute if we have a value
            result = result.replace(f'#{i}', arg)
    return result

class NewCommandProcessor:
    @staticmethod
    def process( 
        command_name: str, 
        definition: str, 
        num_args: Optional[int] = None, 
        defaults: Optional[List[str]] = []
    ):
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

        # Create and store the handler with the command
        pattern, handler = NewCommandProcessor.create_command_handler(command_name, command)
        command['pattern'] = pattern
        command['handler'] = handler

        return command
    
    @staticmethod
    def expand(text: str, commands: Dict[str, Dict[str, any]]) -> tuple[str, int]:
        """Recursively expand defined commands in the text until no further expansions are possible."""
        # First handle all regular command expansions
        previous_text = None
        match_count = 0
        while previous_text != text:
            previous_text = text
            for cmd in commands.values():
                text = cmd['pattern'].sub(cmd['handler'], text)
                if previous_text != text:
                    match_count += 1
        return text, match_count

    @staticmethod
    def create_command_handler(cmd_name: str, cmd_info: dict) -> tuple[re.Pattern, callable]:
        """Creates and returns a cached (pattern, handler) tuple for a command"""
        
        # Replace word boundary with negative lookahead to prevent matching partial commands
        # but still allow numbers to follow immediately
        pattern = r'\\' + re.escape(cmd_name) + r'(?![a-zA-Z])'

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
            
            return substitute_args(cmd_info['definition'], args)

        return regex, handler

class CommandProcessor:
    def __init__(self):
        self.commands: Dict[str, Dict[str, any]] = {}
        
        # Replace the unicode conversion initialization with LatexUnicodeConverter
        self.unicode_converter = LatexUnicodeConverter()

    def clear(self):
        self.commands = {}

    def has_command(self, command_name: str) -> bool:
        return command_name in self.commands

    def process_newcommand(
        self, 
        command_name: str, 
        definition: str, 
        num_args: Optional[int] = None, 
        defaults: Optional[List[str]] = []
    ):
        command = NewCommandProcessor.process(command_name, definition, num_args, defaults)
        if command:
            self.commands[command_name] = command
    
    def process_newdef(self, command_name: str, definition: str, num_args: int, usage_pattern: str):
        def handler(match):
            args = [g for g in match.groups() if g is not None]
            
            return substitute_args(definition, args)
        
        try: 
            command = {
                'definition': definition,
                'args': {'num_args': num_args },
                'pattern': re.compile(usage_pattern, re.DOTALL),
                'handler': handler
            }
            self.commands[command_name] = command
        except Exception as e:
            print(f"Error processing newdef {command_name}: {e}")
            raise e
        
    def expand_commands(self, text: str, ignore_unicode: bool = False) -> tuple[str, int]:
        """Recursively expand defined commands in the text until no further expansions are possible."""
        text, match_count = NewCommandProcessor.expand(text, self.commands)
        
        # Handle unicode conversions using the converter
        if not ignore_unicode:
            text = self.unicode_converter.convert(text)
        
        return text, match_count

    def can_handle(self, text: str) -> bool:
        matched = False
        for cmd in self.commands.values():
            if cmd['pattern'].match(text):
                matched = True
                break
        return matched

    def handle(self, text: str) -> str:
        for cmd in self.commands.values():
            match = cmd['pattern'].match(text)
            if match:
                return cmd['handler'](match), match.end()
        return text, 0

