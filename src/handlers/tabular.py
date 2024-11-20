import re
from typing import Callable, Dict, List, Optional, Tuple
from src.flatten import flatten_tokens
from src.handlers.base import TokenHandler
from src.tex_utils import extract_nested_content

# Compile patterns for code blocks
TABULAR_PATTERN = re.compile(r'\\begin\{tabular\}(?:\[[^\]]*\])?\{([^}]*)\}(.*?)\\end\{tabular\}', re.DOTALL)

ROW_SPLIT_PATTERN = re.compile(r'\\\\(?:\s*\[[^\]]*\])?')
MULTICOLUMN_PATTERN = re.compile(r'\\multicolumn{(\d+)}{[^}]*}{(.*)}')
MULTIROW_PATTERN = re.compile(r'\\multirow{(\d+)}{[^}]*}{(.*)}')
CELL_SPLIT_PATTERN = re.compile(r'(?<!\\)&')

def parse_tabular(latex_table: str, cell_parser_fn = None) -> List[List[Dict]]:
    """
    Parse LaTeX table into structured format with rows and cells containing content and span information
    
    Returns:
        List of rows, where each row is a list of cell dictionaries containing:
        - content: List of parsed elements (text/equations)
        - rowspan: Number of rows this cell spans
        - colspan: Number of columns this cell spans
    """
    # Split into rows, ignoring empty lines
    rows = []
    for row in ROW_SPLIT_PATTERN.split(latex_table):
        row = row.strip()
        if row:
            rows.append(row)
    
    parsed_rows = []
    
    for row_idx, row in enumerate(rows):
        cells = split_cells(row)
        parsed_row = []
        
        for cell in cells:
            # Parse nested multicolumn/multirow
            content = cell
            colspan = 1
            rowspan = 1
            
            # Handle multicolumn first
            mcol_match = MULTICOLUMN_PATTERN.search(content)
            if mcol_match:
                colspan = int(mcol_match.group(1))
                content = mcol_match.group(2).strip()
            
            # Then handle multirow within the content
            mrow_match = MULTIROW_PATTERN.search(content)
            if mrow_match:
                rowspan = int(mrow_match.group(1))
                content = mrow_match.group(2).strip()
            
            # Create cell structure
            parsed_content = cell_parser_fn(content) if cell_parser_fn else content
            parsed_cell = parsed_content
            if rowspan > 1 or colspan > 1:
                parsed_cell = {
                    'content': parsed_content,
                    'rowspan': rowspan,
                    'colspan': colspan
                }
            
            parsed_row.append(parsed_cell)
        
        if parsed_row:
            parsed_rows.append(parsed_row)
    
    # strip out start/end empty rows (incl empty cells)
    if parsed_rows:
        first_row_empty = not any(parsed_rows[0])
        if first_row_empty:
            parsed_rows = parsed_rows[1:]
        last_row_empty = not any(parsed_rows[-1])
        if last_row_empty:
            parsed_rows = parsed_rows[:-1]
    
    return parsed_rows

def split_cells(row: str) -> List[str]:
    """
    Split row into cells by & but handle:
    - escaped &
    - newlines
    - row separators like \\hline
    
    Returns:
        List of cell contents, with separators and empty lines filtered out
    """
    # Split by newlines first and filter out separators
    lines = [line.strip() for line in row.split('\n')]
    lines = [line for line in lines if line]
    
    # Join valid lines back together
    row = ' '.join(lines)
    # print(row)
    
    # Split by unescaped & characters
    return [cell.strip() for cell in CELL_SPLIT_PATTERN.split(row)]


class TabularHandler(TokenHandler):
    def __init__(self, process_content_fn: Optional[Callable[[str], str]] = None, cell_parser_fn: Optional[Callable[[str], List[Dict]]] = None):
        super().__init__(process_content_fn)
        self.cell_parser_fn = cell_parser_fn

    def can_handle(self, content: str) -> bool:
        return bool(re.match(TABULAR_PATTERN, content))
    
    def _clean_cell(self, cell: List[Dict] | str) -> List[Dict]:
        if isinstance(cell, list):
            if len(cell) == 1 and 'type' in cell[0] and cell[0]['type'] == 'text':
                return cell[0]['content']
            elif len(cell) == 0:
                return None
        return cell
    
    def _parse_cell(self, content: str) -> List[Dict]:
        if self.cell_parser_fn:
            content = self.cell_parser_fn(content)
        return self._clean_cell(content)
    
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
            # the reason is that we want to process the content first before we determine row and column splits
            # e.g. there could be \\ inside a nested cell block, so if we dont process first, we will split the row incorrectly
            processed_content = self.process_content_fn(inner_content) if self.process_content_fn else inner_content
            
            # then flatten it out to text form and pass it to parse_tabular
            flattened_content, reference_map = flatten_tokens(processed_content)

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
                        parsed_content = self._parse_cell(text)
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
    from src.handlers.formatting import FormattingHandler

    format_handler = FormattingHandler()
    def parse_cell(content):
        content = content.strip()
        current_pos = 0
        if format_handler.can_handle(content[current_pos:]):
            token, end_pos = format_handler.handle(content[current_pos:])
            current_pos += end_pos
        return content[current_pos:].strip()
    
    handler = TabularHandler(cell_parser_fn=parse_cell)
    
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