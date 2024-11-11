import re
from typing import List, Dict, Tuple, Union

try:
    from ttt import parse_table
except ImportError:
    from .ttt import parse_table  # Try relative import

try:
    from commands import CommandProcessor
except ImportError:
    from .commands import CommandProcessor  # Try relative import

PATTERNS = {
    'section': r'\\section{([^}]*)}',
    'subsection': r'\\subsection{([^}]*)}',
    'paragraph': r'\\paragraph{([^}]*)}',
    # Handle specific environments first (python 3.7+ is ordered dict)
    'equation': r'\\begin\{equation\*?\}(.*?)\\end\{equation(?:\*)?\}',
    'align': r'\\begin\{align\*?\}(.*?)\\end\{align(?:\*)?\}',
    'table': r'\\begin\{table\*?\}(.*?)\\end\{table(?:\*)?\}',  # Add table pattern
    'tabular': r'\\begin\{tabular\}\{([^}]*)\}(.*?)\\end\{tabular\}',  # Add tabular pattern
    # Generic environment pattern comes last
    # 'environment': r'\\begin\{([^}]*)\}(.*?)\\end\{([^}]*)\}',

    'equation_inline': r'\$([^$]*)\$',
    'citation': r'\\(?:cite|citep){([^}]*)}',
    'ref': r'\\ref{([^}]*)}',
    'comment': r'%([^\n]*)',
    'label': r'\\label{([^}]*)}',
    'newcommand': r'\\(?:new|renew)command{\\([^}]+)}\{([^}]*)\}',  # Handles both new and renew
    'newcommand_args': r'\\(?:new|renew)command\*?(?:{\\([^}]+)}|\\([^[\s{]+))(?:\s*\[(\d+)\])?((?:\s*\[[^]]*\])*)\s*{((?:[^{}]|{(?:[^{}]|{[^{}]*})*})*)}',
}

class LatexParser:
    def __init__(self):
        # Regex patterns for different LaTeX elements
        self.command_processor = CommandProcessor()
    
    def _parse_tabular(self, text: str) -> Dict[str, Union[str, Dict, None]]:
        """Parse LaTeX tabular environment into structured data"""
        return parse_table(text)
    
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
        separators = ['\\hline', '\\midrule', '\\toprule', '\\bottomrule', '\\cmidrule']
        return any(sep in row for sep in separators)

    def _extract_citations(self, cell: str) -> List[str]:
        """Extract citation keys from a cell"""
        citations = []
        matches = re.finditer(r'\\cite[p]?{([^}]*)}', cell)
        for match in matches:
            citations.extend(match.group(1).split(','))
        return [c.strip() for c in citations] if citations else None
        
    def _parse_table(self, text: str) -> Dict[str, Union[str, Dict, None]]:
        """Parse LaTeX table environment into structured data"""
        # Extract caption
        caption_match = re.search(r'\\caption{([^}]*)}', text)
        caption = caption_match.group(1).strip() if caption_match else None
        
        # Extract label
        label_match = re.search(r'\\label{([^}]*)}', text)
        label = label_match.group(1) if label_match else None
        
        # Extract tabular environment
        tabular_match = re.search(r'\\begin{tabular}{([^}]*)}(.*?)\\end{tabular}', text, re.DOTALL)
        if not tabular_match:
            return {"type": "table", "caption": caption, "label": label, "table": text}
        
        content = tabular_match.group(2).strip()

        table_data = self._parse_tabular(content)
        
        return {
            "type": "table",
            "label": label,
            "caption": caption,
            "data": table_data
        }
    
    def _expand_command(self, content: str) -> str:
        """Expand LaTeX commands in the content"""
        return self.command_processor.expand_commands(content)

    def parse(self, text: str) -> List[Dict[str, str]]:
        tokens = []
        current_pos = 0
        
        while current_pos < len(text):
            # Try to match each pattern at the current position
            match = None
            matched_type = None
            
            # Handle plain text until next LaTeX command
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
                if matched_type == 'section':
                    tokens.append({
                        "type": "section",
                        "title": match.group(1).strip(),
                        "level": 1
                    })
                # elif matched_type == 'environment':
                #     # Recursively parse the content inside the environment
                #     inner_content = match.group(2).strip()
                #     parsed_inner_content = self.parse(inner_content)
                #     tokens.append({
                #         "type": "environment",
                #         "name": match.group(1).strip(),
                #         "content": parsed_inner_content,  # Keep original content for reference
                #     })
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
                    label_match = re.search(r'\\label{([^}]*)}', content)
                    label = label_match.group(1) if label_match else None
                    
                    # Remove the label command from the content if it exists
                    if label_match:
                        content = content.replace(label_match.group(0), '').strip()
                    
                    tokens.append({
                        "type": "equation",
                        "content": self._expand_command(content),
                        "display": "block",
                        "label": label
                    })
                elif matched_type == 'equation_inline':
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
                elif matched_type == 'ref':
                    tokens.append({
                        "type": "ref",
                        "content": match.group(1).strip()
                    })
                elif matched_type == 'comment':
                    tokens.append({
                        "type": "comment",
                        "content": self._expand_command(match.group(1).strip())
                    })
                elif matched_type == 'label':
                    tokens.append({
                        "type": "label",
                        "content": match.group(1).strip()
                    })
                elif matched_type in ['table', 'tabular']:
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
                else:
                    # For all other token types, expand any commands in their content
                    content = match.group(1) if match.groups() else match.group(0)
                    content = self._expand_command(content)
                    # ... rest of existing token processing ...
                
                current_pos += match.end()
            else:
                # No match found, move forward one character
                current_pos += 1
        
        return tokens

if __name__ == "__main__":
    # from tests.latex_samples_data import RESULTS_SECTION_TEXT

    # text = RESULTS_SECTION_TEXT

    text = r"""
    \newcommand{\tensor}[3]{\mathbf{#1}_{#2}^{#3}}
    \newcommand{\norm}[3][2]{\|#2\|_{#3}^{#1}}
    $\tensor{T}{i}{j}$
    \newcommand{\pow}[2][2]{#2^{#1}}

    \newcommand{\integral}[4][10]{\int_{#1}^{#2} #3 \, d#4}
    $\pow[5]{3}$
    $\integral{b}{f(x)}{x}$
    $\norm[p]{x}{2}$

    \newcommand{\tensorNorm}[4]{\norm{\tensor{#1}{#2}{#3}}{#4}}
    $\tensorNorm{T}{i}{j}{\infty}$
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
    