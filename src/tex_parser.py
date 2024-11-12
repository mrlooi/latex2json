import re
from typing import List, Dict, Tuple, Union

from src.patterns import CITATION_PATTERN, PATTERNS, LABEL_PATTERN, SEPARATORS, extract_citations
from src.tables import parse_table
from src.commands import CommandProcessor

class LatexParser:
    def __init__(self):
        # Regex patterns for different LaTeX elements
        self.command_processor = CommandProcessor()
        self.labels = {}
        self.current_env = None  # Current environment token (used for associating nested labels)

    # getter for commands
    @property
    def commands(self):
        return self.command_processor.commands
    
    def _split_cells(self, row: str) -> List[str]:
        """Split by & but handle escaped &"""
        return [cell.strip() for cell in re.split(r'(?<!\\)&', row)]

    def _clean_content(self, cell: str) -> str:
        """Clean up cell content by removing LaTeX formatting commands"""
        if cell is None:
            return None
    
        # strip out trailing \\
        cell = re.sub(r'\\+$', '', cell)
        return cell.strip()

    def _is_separator_row(self, row: str) -> bool:
        """Check if row contains only LaTeX table separators"""
        return any(sep in row for sep in SEPARATORS)

    def _extract_citations(self, cell: str) -> List[str]:
        """Extract citation keys from a cell"""
        return extract_citations(cell)
        
    def _parse_table(self, text: str) -> Dict[str, Union[str, Dict, None]]:
        """Parse LaTeX table environment into structured data"""
        table = parse_table(text)
        if table and "label" in table:
            self.labels[table["label"]] = table
        return table
    
    def _expand_command(self, content: str) -> str:
        """Expand LaTeX commands in the content"""
        return self.command_processor.expand_commands(content)

    def _find_matching_end(self, text: str, env_name: str, start_pos: int = 0) -> int:
        """Find the matching end{env_name} for a begin{env_name}, handling nested environments"""
        pattern = rf'\\(begin|end)\{{{env_name}}}'
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
            self.current_env["label"] = content
            self.labels[content] = self.current_env
        else:
            # No current environment, associate with previous token if exists
            if tokens and tokens[-1]:
                tokens[-1]['label'] = content
                self.labels[content] = tokens[-1]
            else:
                tokens.append({
                    "type": "label",
                    "content": content
                })

    def parse(self, text: str) -> List[Dict[str, str]]:
        tokens = []
        current_pos = 0
        
        while current_pos < len(text):
            # Try to match each pattern at the current position
            match = None
            matched_type = None
            
            # Handle plain text until next LaTeX command 
            # \\ -> new line, $ -> inline equation, % -> comment
            next_command = re.search(r'\\|\$|%', text[current_pos:])
            if not next_command:
                # No more commands, add remaining text
                if current_pos < len(text):
                    remaining_text = text[current_pos:].strip()
                    if remaining_text:
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
                match = re.match(pattern, text[current_pos:], re.DOTALL)
                if match:
                    matched_type = pattern_type
                    break
            
            if match:
                if matched_type == 'environment':
                    env_name = match.group(1).strip()
                    # Find the correct ending position for this environment
                    start_content = current_pos + match.start(2)
                    end_pos = self._find_matching_end(text, env_name, start_content)
                    
                    if end_pos == -1:
                        # No matching end found, treat as plain text
                        tokens.append({
                            "type": "text",
                            "content": match.group(0)
                        })
                    else:
                        # Extract content between begin and end
                        inner_content = text[start_content:end_pos].strip()
                        
                        # Extract title if present (text within square brackets after environment name)
                        title_match = re.match(r'\[(.*?)\]', inner_content)
                        title = title_match.group(1).strip() if title_match else None
                        
                        # Remove title from inner content before parsing
                        if title_match:
                            inner_content = inner_content[title_match.end():].strip()

                        # DEPRECATED: Label handling is now done independently through _handle_label()
                        # # Extract any label if present
                        # label_match = re.search(LABEL_PATTERN, inner_content)
                        # label = label_match.group(1) if label_match else None
                        
                        # # Remove label from inner content before parsing
                        # if label_match:
                        #     inner_content = inner_content.replace(label_match.group(0), '').strip()
                        
                        env_token = {
                            "type": "environment",
                            "name": env_name,
                            "title": title
                        }
                        
                        # Save previous environment and set current
                        prev_env = self.current_env
                        self.current_env = env_token
                        env_token["content"] = self.parse(inner_content)
                        self.current_env = prev_env
                        
                        tokens.append(env_token)
                        current_pos = end_pos + len(f"\\end{{{env_name}}}")
                        continue
                    
                elif matched_type == 'section':
                    tokens.append({
                        "type": "section",
                        "title": match.group(1).strip(),
                        "level": 1
                    })
                elif matched_type == 'subsection':
                    tokens.append({
                        "type": "section",
                        "title": match.group(1).strip(),
                        "level": 2
                    })
                elif matched_type == 'paragraph':
                    tokens.append({
                        "type": "section",
                        "title": match.group(1).strip(),
                        "level": 3
                    })
                elif matched_type in ['equation', 'align']:
                    # Extract label if present in the equation content
                    content = match.group(1).strip()
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
                        token["label"] = label
                    
                    tokens.append(token)
                elif matched_type == 'label':
                    label_content = match.group(1).strip()
                    self._handle_label(label_content, tokens)
                elif matched_type == 'equation_inline':
                    # we want to parse inline equations in order to roll out any potential newcommand definitions
                    tokens.append({
                        "type": "equation",
                        "content": self._expand_command(match.group(1).strip()),
                        "display": "inline"
                    })
                elif matched_type == 'citation':
                    tokens.append({
                        "type": "citation",
                        "content": match.group(1).strip()
                    })
                elif matched_type == 'ref' or matched_type == 'eqref':
                    tokens.append({
                        "type": "ref",
                        "content": match.group(1).strip()
                    })
                elif matched_type == 'comment':
                    tokens.append({
                        "type": "comment",
                        "content": self._expand_command(match.group(1).strip())
                    })

                elif matched_type == 'table':
                    result = self._parse_table(match.group(1).strip())
                    if result:
                        tokens.append(result)
                elif matched_type == 'newcommand':
                    
                    cmd_name, definition = match.groups()
                    trailing_added = self.command_processor.process_command_definition(cmd_name, definition)
                    current_pos += match.end() + trailing_added # for trailing }
                    continue
                elif matched_type == 'newcommand_args':
                    cmd_name = match.group(1) or match.group(2)  # Command name from either syntax
                    num_args = match.group(3)  # Number of arguments
                    defaults_str = match.group(4)  # All optional defaults
                    definition = match.group(5)  # The command definition
                    trailing_added = self.command_processor.process_command_definition(cmd_name, definition, num_args, defaults_str)
                    current_pos += match.end() + trailing_added
                    continue
                elif matched_type == 'footnote':
                    tokens.append({
                        "type": "footnote",
                        "content": match.group(1).strip()
                    })
                else:
                    # For all other token types, expand any commands in their content
                    content = match.group(1) if match.groups() else match.group(0)
                    content = self._expand_command(content)
                    tokens.append({ 
                        "type": matched_type,
                        "content": content
                    })
                
                current_pos += match.end()
            else:
                # No match found, move forward one character
                current_pos += 1
        
        return tokens

if __name__ == "__main__":
    # from tests.latex_samples_data import RESULTS_SECTION_TEXT

    # text = RESULTS_SECTION_TEXT

    text = r"""
        for $k=1,\dots,D!$ and $j=1,\dots,D$.  Thus for instance the first few elements of the sequence\footnote{OEIS A262725} are
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
    