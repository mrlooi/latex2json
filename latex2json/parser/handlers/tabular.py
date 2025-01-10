import re
from typing import Callable, Dict, List, Optional, Tuple
from latex2json.parser.flatten import flatten_tokens
from latex2json.parser.handlers.environment import BaseEnvironmentHandler
from latex2json.utils.tex_utils import (
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

    def _clean_cell(self, cell: List | Dict | str) -> List[Dict] | str | None:
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
            return [cell]
        return cell

    def _parse_cell(self, content: str) -> List[Dict] | str | None:
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
            # tabular, tabular*, or tabularx
            env_type = (
                match.group(0)
                .replace("\\begin", "")
                .replace("{", "")
                .replace("}", "")
                .strip()
            )

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
            return None, match.end()

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
        blocks, end_pos = extract_nested_content_sequence_blocks(
            inner_content, max_blocks=2
        )

        if blocks:
            column_spec = blocks[-1]
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
                    cells = self._parse_cell(content)
                else:
                    if self.cell_parser_fn:
                        cells = self.cell_parser_fn(content)
                    else:
                        cells = [{"type": "text", "content": content}]

                    out_cells = []
                    for cell in cells:
                        if isinstance(cell, dict) and cell.get("type") == "text":
                            # fetch the references in text content and replace it with the reference content token(s) chunks
                            # e.g. {type: "text", content: "hello `|REF_1|` world `|REF_2|`", styles: ["bold"]}
                            # becomes {type: "text", content: "hello "}, REF_1 token, {type: "text", content: " world "}, REF_2 token
                            # and all these token chunks maintain the same styles as original
                            content = cell["content"]
                            styles = cell.get("styles", [])
                            chunks: List[Dict] = []
                            current_pos = 0

                            for ref_key in reference_map:
                                # only one occurence of each reference key and in order
                                if ref_key in content[current_pos:]:
                                    # Find next reference position
                                    ref_pos = content.find(ref_key, current_pos)

                                    # Add text before reference if any
                                    if ref_pos > current_pos:
                                        text_chunk = {
                                            "type": "text",
                                            "content": content[current_pos:ref_pos],
                                        }
                                        chunks.append(text_chunk)

                                    # Add reference token
                                    ref_token = reference_map[ref_key].copy()
                                    chunks.append(ref_token)

                                    current_pos = ref_pos + len(ref_key)

                            # Add remaining text if any
                            if current_pos < len(content):
                                text_chunk = {
                                    "type": "text",
                                    "content": content[current_pos:],
                                }
                                chunks.append(text_chunk)

                            # now add style if exists
                            if styles:
                                for chunk in chunks:
                                    cur_styles = chunk.get("styles", [])
                                    # Preserve order while removing duplicates
                                    chunk["styles"] = list(
                                        dict.fromkeys(styles + cur_styles)
                                    )
                            out_cells.extend(chunks)
                        else:
                            out_cells.append(cell)
                    cells = out_cells

                if cells:
                    return cells
                return None

            result = parse_tabular(flattened_content, cell_parser_fn)
            token["content"] = result

        return token, total_pos


if __name__ == "__main__":
    from latex2json.parser.handlers.formatting import FormattingHandler

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
