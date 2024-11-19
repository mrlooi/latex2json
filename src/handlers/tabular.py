import re
from typing import Callable, Dict, List, Optional, Tuple
from src.flatten import flatten_tokens
from src.handlers.base import TokenHandler
from src.tables import parse_tabular
from src.tex_utils import extract_nested_content

# Compile patterns for code blocks
TABULAR_PATTERN = re.compile(r'\\begin\{tabular\}(?:\[[^\]]*\])?\{([^}]*)\}(.*?)\\end\{tabular\}', re.DOTALL)

class TabularHandler(TokenHandler):
    def __init__(self, process_content_fn: Optional[Callable[[str], str]] = None, cell_parser_fn: Optional[Callable[[str], List[Dict]]] = None):
        super().__init__(process_content_fn)
        self.cell_parser_fn = cell_parser_fn

    def can_handle(self, content: str) -> bool:
        return bool(re.match(TABULAR_PATTERN, content))
    
    def _parse_cell(self, content: str) -> List[Dict]:
        if self.cell_parser_fn:
            return self.cell_parser_fn(content)
        return content
    
    def handle(self, content: str) -> Tuple[Optional[Dict], int]:
        match = re.match(TABULAR_PATTERN, content)

        if not match:
            return None, 0
        
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
            inner_content = inner_content[end_pos:]

            # now, we need to parse the table content first into an intermediate format
            # then we can pass it to parse_tabular
            if self.process_content_fn:
                inner_content = self.process_content_fn(inner_content)
            
            # then flatten it out to text form and pass it to parse_tabular
            flattened_content, reference_map = flatten_tokens(inner_content)

            def cell_parser_fn(content: str):
                content = content.strip()
                cells = []
                current_pos = 0

                # check if content even has any references
                has_references = False
                for ref_key in reference_map:
                    if ref_key in content:
                        has_references = True
                        break
                
                if not has_references:
                    return self._parse_cell(content)
                
                def parse_and_add_to_cell(text: str):
                    if text:
                        parsed_content = self.parse(text) # TODO
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
        
        return token, match.end()
    
if __name__ == "__main__":
    handler = TabularHandler()
    text = r"""
     \begin{tabular}{|c|c|c|}
        \hline
        \multicolumn{2}{|c|}{Header} & Value \\
        \hline
        a & b & c \\
        \hline
    \end{tabular}
    """.strip()
    token, end_pos = handler.handle(text)
    print(token)