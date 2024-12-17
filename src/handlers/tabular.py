import re
from typing import Callable, Dict, List, Optional, Tuple
from src.flatten import flatten_tokens
from src.handlers.base import TokenHandler
from src.handlers.environment import BaseEnvironmentHandler
from src.tex_utils import (
    extract_nested_content,
    extract_nested_content_pattern,
    extract_nested_content_sequence_blocks,
    find_matching_env_block,
)


tabular_pattern_1 = r"\\begin\s*\{(tabular|longtable|tabularx|tabulary)\*?\}"
tabular_pattern_2 = r"\\tabular(?![a-zA-Z@])"

# Compile patterns for code blocks
TABULAR_PATTERN = re.compile(
    r"%s|%s" % (tabular_pattern_1, tabular_pattern_2),
    re.DOTALL,
)

ROW_SPLIT_PATTERN = re.compile(r"\\\\(?:\s*\[[^\]]*\])?")
MULTICOLUMN_PATTERN = re.compile(r"\\multicolumn\s*{(\d+)}\s*{", re.DOTALL)
MULTIROW_PATTERN = re.compile(r"\\multirow\s*{(\d+)}\s*{", re.DOTALL)
CELL_SPLIT_PATTERN = re.compile(r"(?<!\\)&")


MAKECELL_SHORTSTACK_PATTERN = re.compile(
    r"\\(?:makecell|shortstack)(?:\s*\[[^\]]*\])?\s*{", re.DOTALL
)


def split_latex_content(
    content: str, delimiter: str, is_row_split: bool = False
) -> List[str]:
    """
    Generic function to split LaTeX content while respecting nested structures.

    Args:
        content: The LaTeX content to split
        delimiter: The delimiter to split on ('\\\\' for rows, '&' for cells)
        is_row_split: Whether this is a row split (affects newline handling)

    Returns:
        List of split content, with separators and empty lines filtered out for rows,
        but preserving empty cells for cell splitting
    """
    # For cell splitting, handle newlines first
    if not is_row_split:
        lines = [line.strip() for line in content.split("\n")]
        lines = [line for line in lines if line]
        content = " ".join(lines)

    parts = []
    current_part = []
    nesting_level = 0
    i = 0

    while i < len(content):
        if content[i] == "{":
            nesting_level += 1
            current_part.append(content[i])
        elif content[i] == "}":
            nesting_level -= 1
            current_part.append(content[i])
        elif content[i : i + len(delimiter)] == delimiter and nesting_level == 0:
            # Only split when we're not inside brackets
            current_part = "".join(current_part).strip()
            if is_row_split:
                # For rows, only add non-empty parts
                if current_part:
                    parts.append(current_part)
            else:
                # For cells, preserve empty cells
                parts.append(current_part)
            current_part = []
            i += len(delimiter) - 1  # Skip the rest of delimiter
        else:
            current_part.append(content[i])
        i += 1

    # Add the last part if it exists (for rows) or always (for cells)
    current_part = "".join(current_part).strip()
    if is_row_split:
        if current_part:
            parts.append(current_part)
    else:
        parts.append(current_part)

    return parts


def split_rows(latex_table: str) -> List[str]:
    """Split table content into rows while respecting nested structures."""
    return split_latex_content(latex_table, r"\\", is_row_split=True)


def split_cells(row: str) -> List[str]:
    """Split row into cells while respecting nested structures."""
    cells = split_latex_content(row, "&", is_row_split=False)
    out_cells = []
    for cell in cells:
        if cell:
            match = MAKECELL_SHORTSTACK_PATTERN.search(cell)
            if match:
                cell, end_pos = extract_nested_content(cell[match.end() - 1 :])
        out_cells.append(cell)
    return out_cells


def parse_tabular(latex_table: str, cell_parser_fn=None) -> List[List[Dict]]:
    """
    Parse LaTeX table into structured format with rows and cells containing content and span information

    Returns:
        List of rows, where each row is a list of cell dictionaries containing:
        - content: List of parsed elements (text/equations)
        - rowspan: Number of rows this cell spans
        - colspan: Number of columns this cell spans
    """
    # Split into rows, ignoring empty lines
    rows = split_rows(latex_table)

    parsed_rows = []

    for row_idx, row in enumerate(rows):
        row = row.strip()
        if row:
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
                    start_pos = mcol_match.end() - 1
                    blocks, end_pos = extract_nested_content_sequence_blocks(
                        content[start_pos:], max_blocks=2
                    )
                    content = blocks[-1].strip() if blocks else ""

                # Then handle multirow within the content
                mrow_match = MULTIROW_PATTERN.search(content)
                if mrow_match:
                    rowspan = int(mrow_match.group(1))
                    start_pos = mrow_match.end() - 1
                    blocks, end_pos = extract_nested_content_sequence_blocks(
                        content[start_pos:], max_blocks=2
                    )
                    content = blocks[-1].strip() if blocks else ""

                # Create cell structure
                parsed_content = cell_parser_fn(content) if cell_parser_fn else content
                parsed_cell = parsed_content
                if rowspan > 1 or colspan > 1:
                    parsed_cell = {
                        "content": parsed_content,
                        "rowspan": rowspan,
                        "colspan": colspan,
                    }

                parsed_row.append(parsed_cell)

            if parsed_row:
                parsed_rows.append(parsed_row)

    # strip out start/end empty rows (incl empty cells)
    if parsed_rows:
        first_row_empty = not any(parsed_rows[0])
        if first_row_empty:
            parsed_rows = parsed_rows[1:]
        if parsed_rows:
            last_row_empty = not any(parsed_rows[-1])
            if last_row_empty:
                parsed_rows = parsed_rows[:-1]

    return parsed_rows


class TabularHandler(BaseEnvironmentHandler):
    def __init__(
        self,
        process_content_fn: Optional[Callable[[str], str]] = None,
        cell_parser_fn: Optional[Callable[[str], List[Dict]]] = None,
    ):
        super().__init__(process_content_fn=process_content_fn)
        self.cell_parser_fn = cell_parser_fn

    def can_handle(self, content: str) -> bool:
        return bool(re.match(TABULAR_PATTERN, content))

    def _clean_cell(self, cell: List | Dict | str) -> List[Dict]:
        if isinstance(cell, list):
            if len(cell) == 1:
                return self._clean_cell(cell[0])
            elif len(cell) == 0:
                return None
        elif isinstance(cell, str):
            return cell
        elif isinstance(cell, dict):
            if "content" in cell and cell["type"] == "text" and "styles" not in cell:
                return cell["content"]
        return cell

    def _parse_cell(self, content: str) -> List[Dict]:
        if self.cell_parser_fn:
            content = self.cell_parser_fn(content)
        return self._clean_cell(content)

    def handle(
        self, content: str, prev_token: Optional[Dict] = None
    ) -> Tuple[Optional[Dict], int]:
        match = re.match(TABULAR_PATTERN, content)

        if not match:
            return None, 0

        env_type = "tabular"
        is_begin = match.group(0).startswith("\\begin")
        if is_begin:
            env_type = match.group(1)  # tabular, tabular*, or tabularx

        # Strip out the beginning and end tags dynamically using the matched environment type

        if is_begin:
            start_pos, end_pos, inner_content = find_matching_env_block(
                content, env_type
            )
        else:
            start_pos, end_pos, inner_content = extract_nested_content_pattern(
                content, r"\\tabular", r"\\endtabular"
            )
        if start_pos == -1:
            return None, 0

        total_pos = end_pos

        # Extract content between begin and end
        inner_content = inner_content.strip()
        # extract optional arg (if exists)
        _, end_pos = extract_nested_content(inner_content, "[", "]")
        inner_content = inner_content[end_pos:]

        token = {
            "type": "tabular",
            "environment": env_type,  # Store the specific environment type
        }

        # Extract column spec using nested content extraction
        column_spec, end_pos = extract_nested_content(inner_content)

        if column_spec is not None:
            # For tabularx, the first argument is the width
            if env_type == "tabularx" or env_type == "tabulary":
                width_spec, width_end = extract_nested_content(inner_content)
                if width_spec is not None:
                    token["width"] = width_spec.strip()
                    # Get the actual column spec after the width
                    column_spec, end_pos = extract_nested_content(
                        inner_content[width_end:]
                    )
                    end_pos += (
                        width_end  # Adjust end position to account for width spec
                    )

            token["column_spec"] = column_spec.strip()

            # Get the table content after the column spec
            inner_content = inner_content[end_pos:]

            # now, we need to parse the table content first into an intermediate format
            # then we can pass it to parse_tabular
            # the reason is that we want to process the content first before we determine row and column splits
            # e.g. there could be \\ inside a nested cell block, so if we dont process first, we will split the row incorrectly
            processed_content = (
                self.process_content_fn(inner_content)
                if self.process_content_fn
                else inner_content
            )

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
                            if isinstance(parsed_content, str):
                                cells.append(
                                    {"type": "text", "content": parsed_content}
                                )
                            else:
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
                        if text_before:  # Only parse if there's actual text before
                            parse_and_add_to_cell(text_before)

                    # Handle the reference key if found
                    if next_ref:
                        cells.append(reference_map[next_ref])
                        current_pos = next_ref_pos + len(next_ref)

                        # Handle any text after the reference until the next reference or end
                        next_ref_start = len(content)
                        for ref_key in reference_map:
                            pos = content.find(ref_key, current_pos)
                            if pos != -1 and pos < next_ref_start:
                                next_ref_start = pos

                        if current_pos < next_ref_start:
                            text_after = content[current_pos:next_ref_start].strip()
                            if text_after:
                                parse_and_add_to_cell(text_after)
                            current_pos = next_ref_start
                    else:
                        # No more references found, handle remaining content
                        remaining = content[current_pos:].strip()
                        if remaining:
                            parse_and_add_to_cell(remaining)
                        break

                if cells:
                    if len(cells) == 1:
                        return cells[0]
                    return cells
                return None

            result = parse_tabular(flattened_content, cell_parser_fn)
            token["content"] = result

        return token, total_pos


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
    \begin{tabular}{cc}
        \makecell{a & b \\ c & d} & 22
    \end{tabular} 
    POST
    """.strip()
    token, end_pos = handler.handle(text)
    print(token)
