import re
from typing import List, Dict, Tuple, Union

from src.patterns import CAPTION_PATTERN, TABULAR_PATTERN, LABEL_PATTERN, CITATION_PATTERN

def parse_table(text: str) -> Dict[str, Union[str, Dict, None]]:
    """Parse LaTeX table environment into structured data"""
    # Extract caption
    caption_match = re.search(CAPTION_PATTERN, text)
    caption = caption_match.group(1).strip() if caption_match else None
    
    # Extract label
    label_match = re.search(LABEL_PATTERN, text)
    label = label_match.group(1) if label_match else None
    
    # Extract tabular environment
    tabular_match = re.search(
        TABULAR_PATTERN,
        text,
        re.DOTALL
    )
    if not tabular_match:
        return {"type": "table", "caption": caption, "label": label, "table": text}
    
    content = tabular_match.group(2).strip()

    table_data = parse_tabular(content)
    
    return {
        "type": "table",
        "label": label,
        "caption": caption,
        "data": table_data
    }

def parse_tabular(latex_table):
    """
    Parse LaTeX table into structured format
    """
    # Split into rows and clean up
    rows = []
    for row in latex_table.split('\\\\'):
        row: str = row.strip()
        if row and not row.startswith('%') and not is_separator_row(row):
            rows.append(row)

    if not rows:
        return None

    # Analyze header structure
    header_rows_needed = 1  # default
    first_row = rows[0]
    if '\\multirow' in first_row:
        # Find max multirow span
        matches = re.finditer(r'\\multirow{(\d+)}', first_row)
        header_rows_needed = max(
            [int(m.group(1)) for m in matches], 
            default=1
        )

    # Ensure we have enough rows
    if len(rows) < header_rows_needed:
        return None

    # Split into header and data sections
    header_rows = rows[:header_rows_needed]
    data_rows = rows[header_rows_needed:]

    # Parse headers
    headers = parse_headers(header_rows)
    
    # Calculate total columns from header structure
    total_columns = calculate_total_columns(headers)

    # Parse data rows
    parsed_rows = [parse_data_row(row, total_columns) for row in data_rows]

    return {
        "headers": headers,
        "rows": parsed_rows
    }

def parse_headers(header_rows):
    """
    Parse header rows into structured format.
    Handles multirow/multicolumn and varying number of header rows.
    """
    if not header_rows:
        return []

    headers = []
    main_row = header_rows[0]
    main_cells = split_cells(main_row)
    
    # Track subheader cells if we have them
    sub_cells = []
    if len(header_rows) > 1:
        sub_cells = split_cells(header_rows[1])
    
    current_sub_idx = 0
    for cell_idx, cell in enumerate(main_cells):
        if "\\multirow" in cell:
            match = re.search(r'\\multirow{(\d+)}{[^}]*}{([^}]*)}', cell)
            if match:
                headers.append({
                    "content": clean_content(match.group(2)),
                    "rowspan": int(match.group(1))
                })
            current_sub_idx += 1
            
        elif "\\multicolumn" in cell:
            match = re.search(r'\\multicolumn{(\d+)}{[^}]*}{([^}]*)}', cell)
            if match:
                colspan = int(match.group(1))
                content = match.group(2)
                
                # Get subheaders if they exist
                these_subs = []
                if sub_cells and current_sub_idx < len(sub_cells):
                    these_subs = [
                        clean_content(sh) 
                        for sh in sub_cells[current_sub_idx:current_sub_idx + colspan] 
                        if sh.strip()
                    ]
                
                headers.append({
                    "content": clean_content(content),
                    "subheaders": these_subs if these_subs else None
                })
                current_sub_idx += colspan
                
        elif cell.strip():
            headers.append({
                "content": clean_content(cell)
            })
            current_sub_idx += 1
            
        else:
            headers.append(None)
            current_sub_idx += 1

    return headers

def parse_data_row(row, total_columns):
    """
    Parse a data row into structured format
    """
    cells = split_cells(row)
    parsed_cells = []
    
    # Pad with None if needed
    cells.extend([None] * (total_columns - len(cells)))
    
    for cell in cells[:total_columns]:
        if not cell or not cell.strip():
            parsed_cells.append(None)
            continue
            
        # Extract citations if present
        citations = extract_citations(cell)
        content = clean_content(cell)
        
        if citations:
            parsed_cells.append({
                "content": content,
                "citations": citations
            })
        else:
            parsed_cells.append(content)
    
    return parsed_cells

def calculate_total_columns(headers):
    """
    Calculate total number of columns from header structure
    """
    total = 0
    for header in headers:
        if header is None:
            total += 1
        elif header.get('subheaders'):
            total += len(header['subheaders'])
        else:
            total += 1
    return total

def extract_citations(text):
    """
    Extract citations from text
    """
    citations = []
    # Match \cite{...} or \citep{...}
    matches = re.finditer(CITATION_PATTERN, text)
    for match in matches:
        citations.extend(match.group(1).split(','))
    return [c.strip() for c in citations] if citations else None

def clean_content(text):
    """
    Clean LaTeX formatting while preserving essential content
    """
    if not text:
        return None
        
    # Remove common formatting commands
    text = re.sub(r'\\vspace{[^}]*}', '', text)
    text = re.sub(r'\\hspace{[^}]*}', '', text)
    text = re.sub(CITATION_PATTERN, '', text)
    
    # Clean up whitespace
    return text.strip()

def split_cells(row):
    """
    Split row into cells by & but handle escaped &
    """
    return [cell.strip() for cell in re.split(r'(?<!\\)&', row)]

def is_separator_row(row):
    """
    Check if row contains only separator commands
    """
    separators = ['\\hline', '\\midrule', '\\toprule', 
                 '\\bottomrule', '\\cmidrule']
    return row and all(
        only_contains_separators(part.strip(), separators) 
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
    # table_text = """
    # \\toprule
    # \\multirow{2}{*}{\\vspace{-2mm}Model} & \\multicolumn{2}{c}{BLEU} & & \\multicolumn{2}{c}{Training Cost (FLOPs)} \\\\
    # \\cmidrule{2-3} \\cmidrule{5-6} 
    # & EN-DE & EN-FR & & EN-DE & EN-FR \\\\ 
    # \\hline
    # ByteNet \\citep{NalBytenet2017} & 23.75 & & & &\\\\
    # Deep-Att + PosUnk \\citep{DBLP:journals/corr/ZhouCWLX16} & & 39.2 & & & $1.0\\cdot10^{20}$ \\\\
    # Transformer (big) & \\textbf{28.4} & \\textbf{41.8} & & \\multicolumn{2}{c}{$2.3\\cdot10^{19}$} \\\\
    # """

    # parsed_table = parse_table(table_text)
    # print(parsed_table)
    # print()

    # table_text = """
    # {\\bf Parser}  & {\\bf Training} & {\\bf WSJ 23 F1} \\\\
    # Vinyals \\& Kaiser el al. (2014) \\cite{KVparse15}
    #     & WSJ only, discriminative & 88.3 \\\\
    # """

    # parsed_table = parse_table(table_text)
    # print(parsed_table)

    table_text = """
        \\hline\\rule{0pt}{2.0ex}
        & \\multirow{2}{*}{$N$} & \\multirow{2}{*}{$\\dmodel$} &
        \\multirow{2}{*}{$\\dff$} & \\multirow{2}{*}{$h$} & 
        \\multirow{2}{*}{$d_k$} & \\multirow{2}{*}{$d_v$} & 
        \\multirow{2}{*}{$P_{drop}$} & \\multirow{2}{*}{$\\epsilon_{ls}$} &
        train & PPL & BLEU & params \\\\
        & & & & & & & & & steps & (dev) & (dev) & $\times10^6$ \\\\
        % & & & & & & & & & & & & \\\\
        \\hline\\rule{0pt}{2.0ex}
        base & 6 & 512 & 2048 & 8 & 64 & 64 & 0.1 & 0.1 & 100K & 4.92 & 25.8 & 65 \\\\
        \\hline\\rule{0pt}{2.0ex}
        \\multirow{4}{*}{(A)}
        & & & & 1 & 512 & 512 & & & & 5.29 & 24.9 &  \\\\
        & & & & 4 & 128 & 128 & & & & 5.00 & 25.5 &  \\\\
        & & & & 16 & 32 & 32 & & & & 4.91 & 25.8 &  \\\\
        & & & & 32 & 16 & 16 & & & & 5.01 & 25.4 &  \\\\
        \\hline\\rule{0pt}{2.0ex}
        \\multirow{2}{*}{(B)}
        & & & & & 16 & & & & & 5.16 & 25.1 & 58 \\\\
        & & & & & 32 & & & & & 5.01 & 25.4 & 60 \\\\
        \\hline\\rule{0pt}{2.0ex}
        \\multirow{7}{*}{(C)}
        & 2 & & & & & & & &            & 6.11 & 23.7 & 36 \\\\
        & 4 & & & & & & & &            & 5.19 & 25.3 & 50 \\\\
        & 8 & & & & & & & &            & 4.88 & 25.5 & 80 \\\\
        & & 256 & & & 32 & 32 & & &    & 5.75 & 24.5 & 28 \\\\
        & & 1024 & & & 128 & 128 & & & & 4.66 & 26.0 & 168 \\\\
        & & & 1024 & & & & & &         & 5.12 & 25.4 & 53 \\\\
        & & & 4096 & & & & & &         & 4.75 & 26.2 & 90 \\\\
        \\hline\\rule{0pt}{2.0ex}
        \\multirow{4}{*}{(D)}
        & & & & & & & 0.0 & & & 5.77 & 24.6 &  \\\\
        & & & & & & & 0.2 & & & 4.95 & 25.5 &  \\\\
        & & & & & & & & 0.0 & & 4.67 & 25.3 &  \\\\
        & & & & & & & & 0.2 & & 5.47 & 25.7 &  \\\\
        \\hline\\rule{0pt}{2.0ex}
        (E) & & \\multicolumn{7}{c}{positional embedding instead of sinusoids} & & 4.92 & 25.7 & \\\\
        \\hline\\rule{0pt}{2.0ex}
        big & 6 & 1024 & 4096 & 16 & & & 0.3 & & 300K & \\textbf{4.33} & \\textbf{26.4} & 213 \\\\
        \\hline
    """

    parsed_table = parse_tabular(table_text)
    print(parsed_table)