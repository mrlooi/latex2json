import re
from typing import Callable, Dict, List, Optional, Tuple
from src.flatten import flatten_tokens
from src.handlers.base import TokenHandler
from src.handlers.environment import BaseEnvironmentHandler
from src.tex_utils import (
    extract_nested_content,
    extract_nested_content_pattern,
    find_matching_env_block,
)

inside_tabular_pattern = r"(?:\[[^\]]*\])?\{([^}]*)\}(.*?)"

tabular_pattern_1 = (
    r"\\begin\s*\{(tabular\*?|longtable|tabularx|tabulary)\}%s\\end\s*\{\1\}"
    % (inside_tabular_pattern)
)
tabular_pattern_2 = r"\\tabular%s\\endtabular" % (inside_tabular_pattern)

# Compile patterns for code blocks
TABULAR_PATTERN = re.compile(
    r"%s|%s" % (tabular_pattern_1, tabular_pattern_2),
    re.DOTALL,
)

ROW_SPLIT_PATTERN = re.compile(r"\\\\(?:\s*\[[^\]]*\])?")
MULTICOLUMN_PATTERN = re.compile(r"\\multicolumn{(\d+)}{[^}]*}{(.*)}", re.DOTALL)
MULTIROW_PATTERN = re.compile(r"\\multirow{(\d+)}{[^}]*}{(.*)}", re.DOTALL)
CELL_SPLIT_PATTERN = re.compile(r"(?<!\\)&")


def split_rows(latex_table: str) -> List[str]:
    """
    Split table content into rows while respecting nested structures.
    Doesn't split on \\ that appears inside {...} blocks.
    """
    rows = []
    current_row = []
    nesting_level = 0
    i = 0

    while i < len(latex_table):
        if latex_table[i] == "{":
            nesting_level += 1
            current_row.append(latex_table[i])
        elif latex_table[i] == "}":
            nesting_level -= 1
            current_row.append(latex_table[i])
        elif latex_table[i : i + 2] == r"\\" and nesting_level == 0:
            # Only split on \\ when we're not inside brackets
            current_row = "".join(current_row).strip()
            if current_row:
                rows.append(current_row)
            current_row = []
            i += 1  # Skip the second backslash
        else:
            current_row.append(latex_table[i])
        i += 1

    # Add the last row if it exists
    current_row = "".join(current_row).strip()
    if current_row:
        rows.append(current_row)

    return rows


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
    lines = [line.strip() for line in row.split("\n")]
    lines = [line for line in lines if line]

    # Join valid lines back together
    row = " ".join(lines)
    # print(row)

    # Split by unescaped & characters
    return [cell.strip() for cell in CELL_SPLIT_PATTERN.split(row)]


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
	\begin{tabular}{@{}lllllr@{}}	
		\multirow{2}{34mm}{Experiment Setup\\ (training set)\at(test set)}
	\end{tabular}
    """.strip()
    token, end_pos = handler.handle(text.strip())
