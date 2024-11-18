import re
from typing import List, Dict, Tuple, Union

from src.environments import EnvironmentProcessor
from src.flattern import flatten_tokens
from src.patterns import ENV_TYPES, EQUATION_PATTERNS, PATTERNS, LABEL_PATTERN, SECTION_LEVELS, NESTED_BRACE_COMMANDS
from src.tables import parse_tabular
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

    def _handle_newcommand(self, text: str, start_pos: int, match):
        content, end_pos = extract_nested_content(text[start_pos - 1:])
        if content is None:
            return start_pos
        end_pos = start_pos + end_pos - 1 # move back one to account for start_pos -1
    
        # Get command name from either group 1 (with braces) or group 2 (without braces)
        cmd_name = match.group(1) or match.group(2)
        if cmd_name.startswith('\\'): # Handle case where command name starts with backslash
            cmd_name = cmd_name[1:]
        
        num_args = match.group(3)
        trailing_added = self.command_processor.process_command_definition(cmd_name, content, num_args, match.group(4))
        return end_pos + trailing_added
    
    def _handle_newenvironment(self, text: str, start_pos: int, match):
        """Handle \newenvironment command with multiple possible arguments"""
        # Get environment name
        env_name = match.group(1)
        current_pos = start_pos
        
        # Store environment definition
        env_def = {
            'name': env_name,
            'args': [],
            'optional_args': []
        }
        
        # Look for optional arguments [n][default]...
        while current_pos < len(text):
            # Skip whitespace
            while current_pos < len(text) and text[current_pos].isspace():
                current_pos += 1
                
            if current_pos >= len(text) or text[current_pos] != '[':
                break
                
            # Find matching closing bracket
            bracket_count = 1
            search_pos = current_pos + 1
            bracket_start = search_pos
            
            while search_pos < len(text) and bracket_count > 0:
                if text[search_pos] == '[':
                    bracket_count += 1
                elif text[search_pos] == ']':
                    bracket_count -= 1
                search_pos += 1
                
            if bracket_count == 0:
                # Successfully found matching bracket
                arg = text[bracket_start:search_pos-1].strip()
                
                # First bracket usually contains number of arguments
                if len(env_def['args']) == 0 and arg.isdigit():
                    env_def['args'] = [f'#{i+1}' for i in range(int(arg))]
                else:
                    env_def['optional_args'].append(arg)
                
                current_pos = search_pos
            else:
                break
        
        # Get begin definition
        next_brace = text[current_pos:].find('{')
        if next_brace == -1:
            return start_pos

        begin_def, first_end = extract_nested_content(text[current_pos + next_brace:])
        if begin_def is None:
            return start_pos
        env_def['begin_def'] = begin_def.strip()

        first_end = current_pos + next_brace + first_end
        
        # Find next brace for end definition
        next_brace = text[first_end+1:].find('{')
        if next_brace == -1:
            return first_end
        next_pos = first_end + next_brace

        end_def, final_end = extract_nested_content(text[next_pos:])
        if end_def is None:
            return first_end
        
        final_end = next_pos + final_end
        
        env_def['end_def'] = end_def.strip()

        self.environment_processor.process_environment_definition(env_name, begin_def, end_def, len(env_def['args']), env_def['optional_args'])
        if env_name in self._env_pattern_cache:
            del self._env_pattern_cache[env_name]
                
        return final_end

    def _handle_nested_brace_command(self, matched_type: str, match, text: str, start_pos: int) -> Tuple[Dict, int]:
        content, end_pos = extract_nested_content(text[start_pos - 1:])
        if content is None:
            return None, start_pos
        end_pos = start_pos + end_pos - 1 # move back one to account for start_pos -1

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
            # Handle references
            elif matched_type == 'ref' or matched_type == 'eqref':
                token = {
                    "type": "ref",
                    "content": content
                }
            
            # Handle citations, comments, footnotes and graphics
            elif matched_type == 'citation':
                # Extract both the optional text and citation keys
                token = {
                    "type": "citation",
                    "content": content
                }
                optional_text = match.group(1) if match.group(1) else None
                if optional_text:
                    token["title"] = optional_text.strip()
            elif matched_type == 'includegraphics':
                token = {
                    "type": "includegraphics",
                    "content": content
                }
            
            # handle URL stuffs
            elif matched_type == 'url':
                token = {
                    "type": "url",
                    "content": content
                }

        return token, end_pos
    
    def _handle_tabular(self, match):
        # get entire match data
        # Get position after \begin{tabular}
        inner_content = match.group(0)
        # strip out the beginning \begin{tabular} and \end{tabular}
        inner_content = inner_content[len(r'\begin{tabular}'):-len(r'\end{tabular}')]
        
        token = {
            "type": "tabular",
        }
        # Extract column spec using nested content extraction
        column_spec, end_pos = extract_nested_content(inner_content)
        if column_spec is not None:
            token["column_spec"] = column_spec.strip()

            # Get the table content after the column spec
            inner_content = inner_content[end_pos+1:]

            # now, we need to parse the table content first into an intermediate format
            # then we can pass it to parse_tabular
            parsed_content = self.parse(inner_content, r'\\') # preserve \\ line break to maintain tabular row delimiter \\ integrity
            # then flatten it out to text form and pass it to parse_tabular
            flattened_content, reference_map = flatten_tokens(parsed_content)

            def cell_parser_fn(content: str):
                content = content.strip()
                cells = []
                current_pos = 0

                # check if content even has any references
                for ref_key in reference_map:
                    if ref_key in content:
                        break
                else:
                    return self._parse_cell(content)
                
                def parse_and_add_to_cell(text: str):
                    if text:
                        parsed_content = self.parse(text)
                        if parsed_content:
                            cells.extend(parsed_content)
                
                while current_pos < len(content):
                    # Look for the next reference key
                    next_ref = None
                    next_ref_pos = len(content)
                    
                    # Find the earliest occurring reference key
                    for ref_key in reference_map:
                        pos = content.find(ref_key, current_pos)
                        if pos != -1 and pos < next_ref_pos:
                            next_ref = ref_key
                            next_ref_pos = pos
                    
                    # Handle text before the reference key
                    if next_ref_pos > current_pos:
                        text_before = content[current_pos:next_ref_pos].strip()
                        parse_and_add_to_cell(text_before)
                    
                    # Handle the reference key if found
                    if next_ref:
                        cells.append(reference_map[next_ref])
                        current_pos = next_ref_pos + len(next_ref)
                    else:
                        # No more references found, only parse remaining content if we haven't reached the end
                        if current_pos < len(content):
                            remaining = content[current_pos:].strip()
                            parse_and_add_to_cell(remaining)
                        break
                    
                if cells:
                    if len(cells) == 1: return cells[0]
                    return cells
                return None

            result = parse_tabular(flattened_content, cell_parser_fn)
            if result:
                token["content"] = result

        return token
 
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
                end_pos = current_pos + end_pos # move back one to account for current_pos
                if inner_content is not None:
                    # Parse the content within the braces
                    nested_tokens = self.parse(inner_content)
                    if nested_tokens:
                        # could use append here but we want to keep flatten it out since {} are used just for basic grouping and don't preserve meaningful structure
                        tokens.extend(nested_tokens)
                    current_pos = end_pos + 1
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
            
            # Try each pattern
            for pattern_type, pattern in PATTERNS.items():
                match = re.match(pattern, content[current_pos:])
                if match:
                    matched_type = pattern_type
                    break
            
            trailing_added = 0
            if match:
                # Special handling for nested brace commands
                if matched_type == 'newcommand':
                    start_pos = current_pos + match.end()
                    current_pos = self._handle_newcommand(content, start_pos, match) + 1
                    continue
                elif matched_type == 'newenvironment':
                    # add new environment
                    # Get environment name and content
                    start_pos = current_pos + match.end()
                    current_pos = self._handle_newenvironment(content, start_pos, match) + 1
                    continue
                elif matched_type == 'newtheorem':
                    # ignore
                    pass
                elif matched_type in NESTED_BRACE_COMMANDS:
                    start_pos = current_pos + match.end()
                    token, end_pos = self._handle_nested_brace_command(matched_type, match, content, start_pos)
                    if token:
                        tokens.append(token)
                        current_pos = end_pos + 1
                        continue
                elif matched_type == 'label':
                    start_pos = current_pos + match.end()
                    label, end_pos = extract_nested_content(content[start_pos-1:])
                    if label:
                        self._handle_label(label, tokens)
                    current_pos = start_pos +end_pos
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
                elif matched_type == 'verbatim_env':
                    tokens.append({
                        "type": "code",
                        "content": match.group(1).strip()
                    })
                elif matched_type == 'verb_command':
                    tokens.append({
                        "type": "code",
                        "content": match.group(2)
                    })
                elif matched_type == 'lstlisting':
                    tokens.append({
                        "type": "code",
                        "content": match.group(2),
                        "title": match.group(1).strip() if match.group(1) else None
                    })
                elif matched_type == 'tabular':
                    token = self._handle_tabular(match)
                    if token:
                        tokens.append(token)
                    # print(text[current_pos+match.end():])
                elif matched_type in EQUATION_PATTERNS:
                    # Extract label if present in the equation content
                    equation = match.group(1).strip()
                    if equation:
                        label_match = re.search(LABEL_PATTERN, equation)
                        
                        # Remove the label command from the equation if it exists
                        label = None
                        if label_match:
                            start_pos = label_match.end() - 1 # -1 to account for the label command '{'
                            label, end_pos = extract_nested_content(equation[start_pos:])
                            if label:
                                equation = equation[start_pos+end_pos+1:].strip()

                        equation = self._expand_command(equation)
                        token = {
                            "type": "equation",
                            "content": equation,
                            "display": "block"
                        }
                        if label:
                            self.labels[label] = token
                            token["labels"] = [label]
                        
                        tokens.append(token)
                elif matched_type.startswith('equation_'):
                    # we want to parse inline equations in order to roll out any potential newcommand definitions
                    equation = match.group(1).strip()
                    if equation:
                        display = "inline" if matched_type.startswith("equation_inline") else "block"
                        tokens.append({
                            "type": "equation",
                            "content": self._expand_command(equation),
                            "display": display
                        })
                
                elif matched_type == 'comment':
                    pass
                    # content = match.group(1).strip()
                    # if content:
                    #     tokens.append({
                    #         "type": "comment",
                    #         "content": content
                    #         # "content": self._expand_command(content)
                    #     })
                elif matched_type == 'item':
                    item = match.group(2).strip()
                    if item: 
                        # treat item as a mini environment
                        item = self._handle_environment('item', item)
                        tokens.append(item)
                elif matched_type == 'formatting' or matched_type == 'separators':
                    # ignore formatting commands
                    pass
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
                
                current_pos += match.end() + trailing_added
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

    text = r"""
\renewenvironment{boxed}[2][This is a box]
{
    \begin{center}
    Argument 1 (\#1)=#1\\[1ex]
    \begin{tabular}{|p{0.9\textwidth}|}
    \hline\\
    Argument 2 (\#2)=#2\\[2ex]
}
{ 
    \\\\\hline
    \end{tabular} 
    \end{center}
}

\begin{boxed}[BOX]{BOX2}
This text is \textit{inside} the environment.
\end{boxed}
    """

    # text = r"""
    # \begin{tabular}{|c|c|c|c|}
    # \hline
    # \multicolumn{2}{|c|}{\multirow{2}{*}{Region}} & \multicolumn{2}{c|}{Sales} \\
    # \cline{3-4}
    # \multicolumn{2}{|c|}{} & 2022 & 2023 \\
    # \hline
    # \multirow{2}{*}{North} & Urban & $x^2 + y^2 = z^2$ & 180 \\
    # & Rural & 100 & 120 \\
    # \hline
    # \multirow{2}{*}{South} & Urban & 200 & \begin{align} \label{eq:1} E = mc^2 \\ $F = ma$ \end{align} \\
    # & & 130 & 160 \\
    # \hline
    # \end{tabular}
    # """

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
    parsed_tokens = parser.parse(text, r'\\')

    print(parsed_tokens)

    # # print all equations
    # table_token = None
    # for token in parsed_tokens:
    #     if token["type"] == 'table':
    #         print(token)
    #         table_token = token
    