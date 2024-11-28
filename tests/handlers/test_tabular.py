import pytest
from src.handlers.formatting import FormattingHandler
from src.handlers.tabular import TabularHandler


@pytest.fixture
def handler():
    format_handler = FormattingHandler()

    def parse_cell(content):
        content = content.strip()
        current_pos = 0
        if format_handler.can_handle(content[current_pos:]):
            token, end_pos = format_handler.handle(content[current_pos:])
            current_pos += end_pos
        return content[current_pos:].strip()

    return TabularHandler(cell_parser_fn=parse_cell)


def test_basic_tabular(handler):
    text = r"""
    \begin{tabular}{c|c}
        a & b \\
        c & d
    \end{tabular}
    """.strip()
    token, end_pos = handler.handle(text.strip())

    assert token is not None
    assert token["type"] == "tabular"
    assert token["column_spec"] == "c|c"
    assert len(token["content"]) == 2  # Two rows
    assert token["content"][0] == ["a", "b"]  # First row
    assert token["content"][1] == ["c", "d"]  # Second row


def test_tabular_with_multicolumn(handler):
    text = r"""
    \begin{tabular}{|c|c|c|}
        \hline
        \multicolumn{2}{|c|}{Header} & Value \\
        \hline
        a & b & c \\
        \hline
    \end{tabular}
    """.strip()
    token, end_pos = handler.handle(text.strip())

    assert token is not None
    assert token["type"] == "tabular"
    assert token["column_spec"] == "|c|c|c|"
    assert len(token["content"]) == 2

    # First row with multicolumn
    assert len(token["content"][0]) == 2

    first_row = token["content"][0]
    assert first_row[0]["content"] == "Header"
    assert first_row[0]["colspan"] == 2
    assert first_row[1] == "Value"

    # Second row
    assert token["content"][1] == ["a", "b", "c"]


def test_tabular_with_equations(handler):
    text = r"""
    \begin{tabular}{{cc}}
        $x^2$ & $y^2$ \\
        $\alpha$ & $\beta$
    \end{tabular}
    """.strip()
    token, end_pos = handler.handle(text.strip())

    assert token is not None
    assert token["type"] == "tabular"
    assert token["column_spec"] == "{cc}"
    assert len(token["content"]) == 2

    # Check equations in cells
    rows = token["content"]
    assert rows[0][0] == "$x^2$"
    assert rows[0][1] == "$y^2$"
    assert rows[1][0] == r"$\alpha$"
    assert rows[1][1] == r"$\beta$"


def test_tabular_with_empty_cells(handler):
    text = r"""
    \begin{tabular}{ccc}
        & & \\
        a & & c \\
        & b & \\
        & & \\
    \end{tabular}
    """.strip()
    token, end_pos = handler.handle(text.strip())
    assert token is not None
    assert token["type"] == "tabular"

    # stripped out start/end empty rows
    assert len(token["content"]) == 2

    assert token["content"][0] == ["a", "", "c"]
    assert token["content"][1] == ["", "b", ""]


def test_can_handle_method(handler):
    valid_text = r"\begin{tabular}{cc} a & b \\ \end{tabular}"
    invalid_text = r"\begin{other}{cc} a & b \\ \end{other}"

    assert handler.can_handle(valid_text) is True
    assert not handler.can_handle(invalid_text)


def test_nested_tabulars(handler):
    # Note that we dont separately parse nested tabular cells in the handler alone
    # generally this type of recursion parsing should be handled by the caller
    # so in this example, the \\ in the nested tabular is not escaped and will be parsed as a line break delimiter

    text = r"""
    \begin{tabularx}{\textwidth}{|X|X|}
        Cell 1 & \begin{tabular}{cc} a & b \\ c & d \end{tabular} \\
    \end{tabularx}
    """.strip()
    token, end_pos = handler.handle(text.strip())

    assert token is not None
    assert token["type"] == "tabular"
    assert token["column_spec"] == "|X|X|"
    assert len(token["content"]) == 2
    assert token["content"][0][0] == "Cell 1"
    assert token["content"][0][1].startswith(r"\begin{tabular}{cc}")
