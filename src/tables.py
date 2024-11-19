import re
from typing import List, Dict, Tuple, Union

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


if __name__ == "__main__":

    text = r"""
    \hline\\
    Argument 2 (\\Some preliminary text)=Some preliminary text\\\\[2ex]

    This text is \textit{inside} the environment.
    """

    text = r"""
        \hline\\
        Argument 2 (Some preliminary text)=Some preliminary text\\[2ex]

        This text is \textit{inside} the environment.\\
        
        \begin{align} 3+2 \\ 332+2 \end{align}
        \\\\\hline 
        
    """

    parsed_table = parse_tabular(text)
    print(parsed_table)