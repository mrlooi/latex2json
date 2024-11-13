import re
from typing import List, Dict, Tuple, Union

from src.patterns import SEPARATORS, CITATION_PATTERN, extract_citations

ROW_SPLIT_PATTERN = re.compile(r'\\\\\s*(?:\n|$)')
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
        if not is_separator_row(row):
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
            mcol_match = MULTICOLUMN_PATTERN.match(content)
            if mcol_match:
                colspan = int(mcol_match.group(1))
                content = mcol_match.group(2).strip()
            
            # Then handle multirow within the content
            mrow_match = MULTIROW_PATTERN.match(content)
            if mrow_match:
                rowspan = int(mrow_match.group(1))
                content = mrow_match.group(2).strip()
            
            # Create cell structure
            parsed_content = cell_parser_fn(content) if cell_parser_fn else content
            parsed_cell = None
            if rowspan > 1 or colspan > 1:
                parsed_cell = {
                    'content': parsed_content,
                    'rowspan': rowspan,
                    'colspan': colspan
                }
            else:
                parsed_cell = parsed_content
            
            parsed_row.append(parsed_cell)
        
        if parsed_row:
            parsed_rows.append(parsed_row)
    
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
    lines = [line for line in lines if line and not is_separator_row(line)]
    
    # Join valid lines back together
    row = ' '.join(lines)
    # print(row)
    
    # Split by unescaped & characters
    return [cell.strip() for cell in CELL_SPLIT_PATTERN.split(row)]

def is_separator_row(row):
    """
    Check if row contains only separator commands
    """
    return row and all(
        only_contains_separators(part.strip(), SEPARATORS) 
        for part in row.split('&')
    )

def only_contains_separators(text, separators):
    """
    Check if text only contains separator commands
    """
    text = text.strip()
    if not text:
        return True
    return any(sep in text for sep in separators)

if __name__ == "__main__":

    text = r"""
        \hline
        \multicolumn{2}{|c|}{\multirow{2}{*}{Region}} & \multicolumn{2}{c|}{Sales} \\
        \cline{3-4}
        \multicolumn{2}{|c|}{} & 2022 & 2023 \\
        \hline
        \multirow{2}{*}{North} & Urban & $x^2 + y^2 = z^2$ & 180 \\
        & Rural & 100 & 120 \\
        \hline
        \multirow{2}{*}{South} & Urban & 200 & \begin{align} E = mc^2 \\ $F = ma$ \end{align} \\
        & & 130 & 160 \\
        \hline
    """

    parsed_table = parse_tabular(text)
    print(parsed_table)