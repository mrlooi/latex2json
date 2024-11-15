import re
from typing import List, Dict, Tuple, Union

from src.patterns import ENV_TYPES, EQUATION_PATTERNS, PATTERNS, LABEL_PATTERN, SEPARATORS, SECTION_LEVELS, NESTED_BRACE_COMMANDS
from src.tables import parse_tabular
from src.commands import CommandProcessor
from src.tex_utils import extract_nested_content

# ... rest of the parser code ...
# Add these compiled patterns at module level
DELIM_PATTERN = re.compile(r'\\|\$|%')
ESCAPED_AMPERSAND_SPLIT = re.compile(r'(?<!\\)&')
TRAILING_BACKSLASH = re.compile(r'\\+$')
UNKNOWN_COMMAND_PATTERN = re.compile(r'\\([a-zA-Z]+)(?:\{(?:[^{}]|{[^{}]*})*\})*')


class LatexParser:
    def __init__(self):
        # Regex patterns for different LaTeX elements
        self.command_processor = CommandProcessor()
        self.labels = {}
        self.current_env = None  # Current environment token (used for associating nested labels)
        
        # Precompile frequently used patterns
        self._env_pattern_cache = {}  # Cache for environment patterns

    # getter for commands
    @property
    def commands(self):
        return self.command_processor.commands

    def _expand_command(self, content: str) -> str:
        """Expand LaTeX commands in the content"""
        return self.command_processor.expand_commands(content)

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
        if len(cell) == 0: 
            return None
        elif len(cell) == 1:
            if cell[0]['type'] == 'text':
                return cell[0]['content']
            return cell[0]
        return cell
    
    def _handle_environment(self, env_name: str, inner_content: str) -> None:
        # Extract title if present (text within square brackets after environment name)
        title_match = re.match(r'^\[(.*?)\]', inner_content)
        title = title_match.group(1).strip() if title_match else None
        
        # Remove title from inner content before parsing
        if title_match:
            inner_content = inner_content[title_match.end():].strip()
        
        # Extract optional arguments
        args_match = re.match(r'^\{(.*?)\}', inner_content)
        if args_match:
            # args = args_match.group(1).strip()
            inner_content = inner_content[args_match.end():].strip()

        # DEPRECATED: Label handling is now done independently through _handle_label()
        # # Extract any label if present
        # label_match = re.search(LABEL_PATTERN, inner_content)
        # label = label_match.group(1) if label_match else None
        
        # # Remove label from inner content before parsing
        # if label_match:
        #     inner_content = inner_content.replace(label_match.group(0), '').strip()
        
        token = {}
        if env_name == "item":
            token["type"] = "item"
        else:
            env_type = ENV_TYPES.get(env_name, "environment")
            token["type"] = env_type
            if env_type not in ["list", "table", "figure"]:
                token["name"] = env_name
        if title:
            token["title"] = title
        
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
        if content:
            content = self._expand_command(content)
            if r'\begin{' in content:
                content = self._parse_cell(content)
                return content
        return {
            "type": "command",
            "content": content
        }

    def _handle_newcommand(self, text: str, start_pos: int, match):
        content, end_pos = extract_nested_content(text, start_pos - 1)
        if content is None:
            return None, start_pos
        
        # Get command name from either group 1 (with braces) or group 2 (without braces)
        cmd_name = match.group(1) or match.group(2)
        if cmd_name.startswith('\\'): # Handle case where command name starts with backslash
            cmd_name = cmd_name[1:]
        
        num_args = match.group(3)
        trailing_added = self.command_processor.process_command_definition(cmd_name, content, num_args, match.group(4))
        return end_pos + trailing_added

    def _handle_nested_brace_command(self, matched_type: str, match, text: str, start_pos: int) -> Tuple[Dict, int]:
        content, end_pos = extract_nested_content(text, start_pos - 1)
        if content is None:
            return None, start_pos
        
        token = None

        if content is not None:
            content = self._expand_command(content)
            # Handle sections and paragraphs
            if matched_type in ['section', 'paragraph', 'chapter', 'part']:
                level = match.group(0).count('sub') + SECTION_LEVELS[matched_type]
                token = {
                    "type": 'section',
                    "title": content,
                    "level": level
                }
            elif matched_type == 'caption':
                token = {
                    "type": "caption",
                    "content": content
                }
            elif matched_type == 'captionof':
                token = {
                    "type": "caption",
                    "title": match.group(1).strip(),
                    "content": content
                }
            elif matched_type == 'footnote':
                token = {
                    "type": "footnote",
                    "content": self._parse_cell(content) # footnotes can contain environments
                }
            elif matched_type == 'hyperref':
                token = {
                    "type": "ref",
                    "title": match.group(1).strip(),
                    "content": content
                }
            elif matched_type == 'href':
                # href{link}{text/title} i.e. title is parsed content here
                token = {
                    "type": "url",
                    "title": content,
                    "content": match.group(1).strip()
                }

        return token, end_pos
 
    def parse(self, text: str) -> List[Dict[str, str]]:
        tokens = []
        current_pos = 0
        
        while current_pos < len(text):
            # Skip whitespace
            while current_pos < len(text) and text[current_pos].isspace():
                current_pos += 1
            if current_pos >= len(text):
                break

            # Add handling for bare braces at the start i.e. latex grouping {content here}
            if text[current_pos] == '{':
                # Find matching closing brace
                content, end_pos = extract_nested_content(text, current_pos)
                if content is not None:
                    # Parse the content within the braces
                    nested_tokens = self.parse(content)
                    if nested_tokens:
                        # could use append here but we want to keep flatten it out since {} are used just for basic grouping and don't preserve meaningful structure
                        tokens.extend(nested_tokens)
                    current_pos = end_pos + 1
                    continue
            
            next_command = DELIM_PATTERN.search(text[current_pos:])
            if not next_command:
                if current_pos < len(text):
                    remaining_text = text[current_pos:].strip()
                    if remaining_text:
                        unknown_cmd = UNKNOWN_COMMAND_PATTERN.match(remaining_text)
                        if unknown_cmd:
                            tokens.append(self._handle_unknown_command(unknown_cmd))
                        else:
                            tokens.append({
                                "type": "text",
                                "content": remaining_text
                            })
                break

            # Add text before the next command if it exists
            if next_command.start() > 0:
                plain_text = text[current_pos:current_pos + next_command.start()].strip()
                if plain_text:
                    tokens.append({
                        "type": "text",
                        "content": plain_text
                    })
                current_pos += next_command.start()
                continue
            
            # Try each pattern
            for pattern_type, pattern in PATTERNS.items():
                match = re.match(pattern, text[current_pos:])
                if match:
                    matched_type = pattern_type
                    break
            
            trailing_added = 0
            if match:
                # Special handling for nested brace commands
                if matched_type == 'newcommand':
                    start_pos = current_pos + match.end()
                    current_pos = self._handle_newcommand(text, start_pos, match) + 1
                    continue
                elif matched_type in NESTED_BRACE_COMMANDS:
                    start_pos = current_pos + match.end()
                    token, end_pos = self._handle_nested_brace_command(matched_type, match, text, start_pos)
                    if token:
                        tokens.append(token)
                        current_pos = end_pos + 1
                        continue
                    
                # Handle environments
                elif matched_type == 'environment':
                    env_name = match.group(1).strip()
                    # Find the correct ending position for this environment
                    start_content = current_pos + match.start(2)
                    end_pos = self._find_matching_env_block(text, env_name, start_content)

                    if end_pos == -1:
                        # No matching end found, treat as plain text
                        tokens.append({
                            "type": "text",
                            "content": match.group(0)
                        })
                    else:
                        # Extract content between begin and end
                        inner_content = text[start_content:end_pos].strip()
                        
                        env_token = self._handle_environment(env_name, inner_content)
                        
                        tokens.append(env_token)
                        current_pos = end_pos + len(f"\\end{{{env_name}}}")
                        continue
                # elif matched_type == 'table' or matched_type == 'figure':
                #     result = self._parse_table(match.group(1).strip(), type=matched_type)
                #     if result:
                #         tokens.append(result)
                elif matched_type == 'tabular':
                    # get entire match data
                    token = {
                        "type": "tabular",
                        "column_spec": match.group(1).strip()
                    }
                    result = parse_tabular(match.group(2).strip(), self._parse_cell)
                    if result:
                        token["content"] = result
                    tokens.append(token)
                elif matched_type in EQUATION_PATTERNS:
                    # Extract label if present in the equation content
                    content = match.group(1).strip()
                    if content:
                        # assume only one label per equation?
                        label_match = re.search(LABEL_PATTERN, content)
                        label = label_match.group(1) if label_match else None
                        
                        # Remove the label command from the content if it exists
                        if label_match:
                            content = content.replace(label_match.group(0), '').strip()

                        token = {
                            "type": "equation",
                            "content": self._expand_command(content),
                            "display": "block"
                        }
                        if label:
                            self.labels[label] = token
                            token["labels"] = [label]
                        
                        tokens.append(token)
                elif matched_type.startswith('equation_'):
                    # we want to parse inline equations in order to roll out any potential newcommand definitions
                    content = match.group(1).strip()
                    if content:
                        display = "inline" if matched_type.startswith("equation_inline") else "block"
                        tokens.append({
                            "type": "equation",
                            "content": self._expand_command(content),
                            "display": display
                        })
                # Handle labels and references
                elif matched_type == 'label':
                    content = match.group(1).strip()
                    self._handle_label(content, tokens)
                elif matched_type == 'ref' or matched_type == 'eqref':
                    tokens.append({
                        "type": "ref",
                        "content": match.group(1).strip()
                    })
               
                # Handle citations, comments, footnotes and graphics
                elif matched_type == 'citation':
                    # Extract both the optional text and citation keys
                    token = {
                        "type": "citation",
                        "content": match.group(2).strip()
                    }
                    optional_text = match.group(1) if match.group(1) else None
                    if optional_text:
                        token["title"] = optional_text.strip()
                    tokens.append(token)
                elif matched_type == 'comment':
                    pass
                    # content = match.group(1).strip()
                    # if content:
                    #     tokens.append({
                    #         "type": "comment",
                    #         "content": content
                    #         # "content": self._expand_command(content)
                    #     })
                
                elif matched_type == 'includegraphics':
                    tokens.append({
                        "type": "includegraphics",
                        "content": match.group(2).strip()
                    })
                
                # handle URL stuffs
                elif matched_type == 'url':
                    tokens.append({
                        "type": "url",
                        "content": match.group(1).strip()
                    })
                elif matched_type == 'item':
                    content = match.group(2).strip()
                    if content: 
                        # treat item as a mini environment
                        content = self._handle_environment('item', content)
                        tokens.append(content)
                elif matched_type == 'formatting':
                    # ignore formatting commands
                    pass
                elif matched_type == 'newline':
                    if tokens and tokens[-1] and tokens[-1]['type'] == 'text':
                        tokens[-1]['content'] += "\n"
                    else:
                        tokens.append({
                            "type": "text",
                        "content": "\n"
                        })
                else:
                    # For all other token types, expand any commands in their content
                    content = match.group(1) if match.groups() else match.group(0)
                    content = self._expand_command(content)
                    tokens.append({ 
                        "type": matched_type,
                        "content": content
                    })
                
                current_pos += match.end() + trailing_added
            else:
                unknown_cmd = UNKNOWN_COMMAND_PATTERN.match(text[current_pos:])
                if unknown_cmd:
                    tokens.append(self._handle_unknown_command(unknown_cmd))
                    current_pos += unknown_cmd.end()
                else:
                    current_pos += 1
        
        return tokens

if __name__ == "__main__":
    # from tests.latex_samples_data import RESULTS_SECTION_TEXT

    # text = RESULTS_SECTION_TEXT

    text = r"""

    \newcommand\pow[2]{#1^{#2}}

    {
    \begin{figure}[h]
        inside $\pow{3}{2}$
    \end{figure}

    \\tt someTT
    \\tt{someTT2}

    \\textbf{someBold}
    }

    \\tt{someTT3}
    outside
    """

    # text = r"""
    # \begin{figure}[h]
    #     \label{fig:example}
    #     Some thing interestin here
    #     % haha
    #     \includegraphics[width=0.5\textwidth]{example-image} % Replace with your image file
    #     \caption{Example Image}
    # \end{figure}
    # """

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
    