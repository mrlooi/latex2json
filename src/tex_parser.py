import re
from typing import List, Dict, Tuple, Union

from src.environments import EnvironmentProcessor
from src.handlers import CodeBlockHandler, EquationHandler, TokenHandler, ContentCommandHandler, NewDefinitionHandler, TabularHandler, FormattingHandler
from src.patterns import ENV_TYPES, PATTERNS
from src.commands import CommandProcessor
from src.tex_utils import extract_nested_content

# Add these compiled patterns at module level
# match $ or % only if not preceded by \
# Update DELIM_PATTERN to also match double backslashes
DELIM_PATTERN = re.compile(r'(?<!\\)(?:\\\\|\$|%|\\(?![$%&_#{}^~\\]))')
ESCAPED_AMPERSAND_SPLIT = re.compile(r'(?<!\\)&')
TRAILING_BACKSLASH = re.compile(r'\\+$')
UNKNOWN_COMMAND_PATTERN = re.compile(r'([ \t\n]*\\[a-zA-Z]+(?:\{(?:[^{}]|{[^{}]*})*\})*[ \t\n]*)')


class LatexParser:
    def __init__(self):
        # Regex patterns for different LaTeX elements
        self.command_processor = CommandProcessor()
        self.environment_processor = EnvironmentProcessor()

        self.labels = {}
        self.current_env = None  # Current environment token (used for associating nested labels)
        
        # Precompile frequently used patterns
        self._env_pattern_cache = {}  # Cache for environment patterns

        self.handlers: List[TokenHandler] = [
            EquationHandler(self._expand_command),
            CodeBlockHandler(),
            ContentCommandHandler(self._expand_command),
            # for tabular, on the first pass we process content and maintain the '\\' delimiter to maintain row integrity
            TabularHandler(process_content_fn=lambda x: self.parse(x, r'\\'), cell_parser_fn=self.parse),
            FormattingHandler()
        ]
        self.new_definition_handler = NewDefinitionHandler()

    # getter for commands
    @property
    def commands(self):
        return self.command_processor.commands
    
    @property
    def environments(self):
        return self.environment_processor.environments

    def _expand_command(self, content: str) -> str:
        """Expand LaTeX commands in the content"""
        out, match_count = self.command_processor.expand_commands(content)
        return out

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
    
    def _handle_label(self, content: str, tokens: List[Dict[str, str]]) -> None:
        """Handle labels by associating them with the current environment or adding them as a separate token"""
        if self.current_env:
            # Associate label with current environment
            if 'labels' not in self.current_env:
                self.current_env['labels'] = []
            self.current_env['labels'].append(content)
            self.labels[content] = self.current_env
        else:
            # No current environment, associate with previous token if exists
            if tokens and tokens[-1]:
                if 'labels' not in tokens[-1]:
                    tokens[-1]['labels'] = []
                tokens[-1]['labels'].append(content)
                self.labels[content] = tokens[-1]
            else:
                tokens.append({
                    "type": 'label',
                    "content": content
                })
    
    def _parse_cell(self, cell_content: str) -> List[Dict]:
        cell = self.parse(cell_content)
        return self._clean_cell(cell)

    def _clean_cell(self, cell: List[Dict]) -> List[Dict]:
        if len(cell) == 0: 
            return None
        elif len(cell) == 1:
            if cell[0]['type'] == 'text':
                return cell[0]['content']
            return cell[0]
        return cell
    
    def _handle_environment(self, env_name: str, inner_content: str) -> None:
        token = {}

        if self.environment_processor.has_environment(env_name):
            # check if expanded and changed
            inner_content = self.environment_processor.expand_environments(env_name, inner_content)
            token = {
                "type": "environment",
                "name": env_name
            }
        else:
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
            
            if env_name == "item":
                token["type"] = "item"
            else:
                env_type = ENV_TYPES.get(env_name, "environment")
                token["type"] = env_type
                if env_type not in ["list", "table", "figure"]:
                    token["name"] = env_name
        
        # Save previous environment and set current
        prev_env = self.current_env
        self.current_env = token
        token["content"] = self.parse(inner_content)
        self.current_env = prev_env

        return token

    def _handle_unknown_command(self, match) -> Dict[str, str]:
        """Convert unknown LaTeX command into a text token with original syntax"""
        # Get the full matched text to preserve all arguments
        content = match.group(0)

        matched = False
        if content:
            content, matched = self.command_processor.expand_commands(content)
            # Only parse if the content changed during expansion
            if r'\begin{' in content and content != match.group(0):
                content = self._parse_cell(content)
                return content
        
        return {
            "type": "text" if matched else "command",
            "content": content
        }
    
    def _check_for_new_definitions(self, content: str) -> None:
        """Check for new definitions in the content and process them"""
        if self.new_definition_handler.can_handle(content):
            token, end_pos = self.new_definition_handler.handle(content)
            if token:
                if token['type'] == 'newcommand':
                    cmd_name = token['name']
                    self.command_processor.process_command_definition(cmd_name, token["content"], token["num_args"], token["defaults"])
                elif token['type'] == 'newenvironment':
                    env_name = token['name']
                    self.environment_processor.process_environment_definition(env_name, token["begin_def"], token["end_def"], len(token["args"]), token["optional_args"])
                elif token['type'] == 'newtheorem':
                    pass
        
            return end_pos
        return 0

    def parse(self, content: str, line_break_delimiter: str = "\n") -> List[Dict[str, str]]:
        tokens = []
        current_pos = 0

        def add_text_token(text: str):
            if text:
                if tokens and tokens[-1] and tokens[-1]['type'] == 'text':
                    tokens[-1]['content'] += text
                else:
                    tokens.append({
                        "type": "text",
                        "content": text
                    })
        
        while current_pos < len(content):
            # Skip whitespace
            while current_pos < len(content) and content[current_pos].isspace():
                current_pos += 1
            if current_pos >= len(content):
                break

            # Add handling for bare braces at the start i.e. latex grouping {content here}
            if content[current_pos] == '{':
                # Find matching closing brace
                inner_content, end_pos = extract_nested_content(content[current_pos:])
                if inner_content is not None:
                    # Parse the content within the braces
                    nested_tokens = self.parse(inner_content)
                    if nested_tokens:
                        # could use append here but we want to keep flatten it out since {} are used just for basic grouping and don't preserve meaningful structure
                        tokens.extend(nested_tokens)
                    current_pos += end_pos
                    continue
            
            next_command = DELIM_PATTERN.search(content[current_pos:])
            if not next_command:
                if current_pos < len(content):
                    remaining_text = content[current_pos:]
                    if remaining_text:
                        unknown_cmd = UNKNOWN_COMMAND_PATTERN.match(remaining_text)
                        if unknown_cmd:
                            tokens.append(self._handle_unknown_command(unknown_cmd))
                        else:
                            add_text_token(remaining_text)
                break

            # Add text before the next command if it exists
            if next_command.start() > 0:
                plain_text = content[current_pos:current_pos + next_command.start()].strip()
                if plain_text:
                    add_text_token(plain_text)
                current_pos += next_command.start()
                continue
            
            # check for new definition commands
            end_pos = self._check_for_new_definitions(content[current_pos:])
            if end_pos > 0:
                current_pos += end_pos
                continue
            
            # try each handler
            matched = False
            for handler in self.handlers:
                if handler.can_handle(content[current_pos:]):
                    token, end_pos = handler.handle(content[current_pos:])
                    if token:
                        if token['type'] == 'footnote':
                            token["content"] = self._parse_cell(token["content"])
                        tokens.append(token)
                    current_pos += end_pos
                    matched = True
                    break
            
            if matched:
                continue
            
            # Try each pattern
            for pattern_type, pattern in PATTERNS.items():
                match = re.match(pattern, content[current_pos:])
                if match:
                    matched_type = pattern_type
                    break
            
            if match:
                if matched_type == 'label':
                    start_pos = current_pos + match.end() - 1 # -1 to account for the label command '{'
                    label, end_pos = extract_nested_content(content[start_pos:])
                    if label:
                        self._handle_label(label, tokens)
                    current_pos = start_pos + end_pos
                    continue
                # Handle environments
                elif matched_type == 'environment':
                    env_name = match.group(1).strip()
                    # Find the correct ending position for this environment
                    start_content = current_pos + match.start(2)
                    end_pos = self._find_matching_env_block(content, env_name, start_content)

                    if end_pos == -1:
                        # No matching end found, treat as plain text
                        add_text_token(match.group(0))
                    else:
                        # Extract content between begin and end
                        inner_content = content[start_content:end_pos].strip()
                        
                        env_token = self._handle_environment(env_name, inner_content)
                        
                        tokens.append(env_token)
                        current_pos = end_pos + len(f"\\end{{{env_name}}}")
                        continue
                elif matched_type == 'item':
                    item = match.group(2).strip()
                    if item: 
                        # treat item as a mini environment
                        item = self._handle_environment('item', item)
                        tokens.append(item)
                elif matched_type == 'newline' or matched_type == 'break_spacing':
                    add_text_token(line_break_delimiter)
                else:
                    # For all other token types, expand any commands in their content
                    x = match.group(1) if match.groups() else match.group(0)
                    x = self._expand_command(x)
                    tokens.append({ 
                        "type": matched_type,
                        "content": x
                    })
                
                current_pos += match.end()
            else:
                unknown_cmd = UNKNOWN_COMMAND_PATTERN.match(content[current_pos:])
                if unknown_cmd:
                    tokens.append(self._handle_unknown_command(unknown_cmd))
                    # Adjust position by the full match length including whitespace
                    current_pos += len(unknown_cmd.group(0))
                else:
                    current_pos += 1
        
        return tokens

if __name__ == "__main__":
    # from tests.latex_samples_data import RESULTS_SECTION_TEXT

    # text = RESULTS_SECTION_TEXT

    text =  r"""
        \begin{table}[htbp]
        \centering
        \begin{tabular}{|c|c|c|c|}
            \hline
            \multicolumn{2}{|c|}{\multirow{2}{*}{Region}} & \multicolumn{2}{c|}{Sales} \\
            \cline{3-4}
            \multicolumn{2}{|c|}{} & 2022 & 2023 \\
            \hline
            \multirow{2}{*}{North} & Urban & $x^2 + y^2 = z^2$ & 180 \\
            & Rural & 100 & 120 \\
            \hline
            \multirow{2}{*}{South} & Urban & 200 & \begin{align} \label{eq:1} E = mc^2 \\ $F = ma$ \end{align} \\
            & & 130 & 160 \\
            \hline
        \end{tabular}
        \caption{Regional Sales Distribution}
        \label{tab:sales}
        \end{table}
    """

    # Example usage
    parser = LatexParser()
    parsed_tokens = parser.parse(text)

    print(parsed_tokens)

    # # print all equations
    # table_token = None
    # for token in parsed_tokens:
    #     if token["type"] == 'table':
    #         print(token)
    #         table_token = token
    