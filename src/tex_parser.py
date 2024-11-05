import re
from typing import List, Dict, Union

class LatexParser:
    def __init__(self):
        # Regex patterns for different LaTeX elements
        self.patterns = {
            'section': r'\\section{([^}]*)}',
            'subsection': r'\\subsection{([^}]*)}',
            'paragraph': r'\\paragraph{([^}]*)}',
            # Handle both numbered and unnumbered environments
            'equation': r'\\begin\{equation\*?\}(.*?)\\end\{equation(?:\*)?\}',
            'align': r'\\begin\{align\*?\}(.*?)\\end\{align(?:\*)?\}',
            'equation_inline': r'\$([^$]*)\$',
            'citation': r'\\citep{([^}]*)}',
            'ref': r'\\ref{([^}]*)}',
            'comment': r'%([^\n]*)',
            'label': r'\\label{([^}]*)}',  # Add pattern for \label command
        }
        
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
            for pattern_type, pattern in self.patterns.items():
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
                    tokens.append({
                        "type": "equation",
                        "content": match.group(1).strip(),
                        "display": "block",
                    })
                elif matched_type == 'equation_inline':
                    tokens.append({
                        "type": "equation",
                        "content": match.group(1).strip(),
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
                        "content": match.group(1).strip()
                    })
                elif matched_type == 'label':
                    tokens.append({
                        "type": "label",
                        "content": match.group(1).strip()
                    })
                
                current_pos += match.end()
            else:
                # No match found, move forward one character
                current_pos += 1
        
        return tokens

if __name__ == "__main__":
    from tests.latex_samples_data import RESULTS_SECTION_TEXT

    text = RESULTS_SECTION_TEXT
     
    # Example usage
    parser = LatexParser()
    parsed_tokens = parser.parse(text)

    # print all equations
    for token in parsed_tokens:
        # if token["type"] not in ["citation", "ref", "label", "comment"]: 
        print(token)
