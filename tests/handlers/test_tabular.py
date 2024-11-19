# import pytest
# from src.handlers.tabular import TabularHandler

# @pytest.fixture
# def handler():
#     return TabularHandler()

# def test_basic_tabular(handler):
#     text = r"""
#     \begin{tabular}{c|c}
#         a & b \\
#         c & d
#     \end{tabular}
#     """.strip()
#     token, end_pos = handler.handle(text.strip())
    
#     assert token is not None
#     assert token["type"] == "tabular"
#     assert token["column_spec"] == "c|c"
#     assert len(token["content"]) == 2  # Two rows
#     assert token["content"][0] == ["a", "b"]  # First row
#     assert token["content"][1] == ["c", "d"]  # Second row

# def test_tabular_with_multicolumn(handler):
#     text = r"""
#     \begin{tabular}{|c|c|c|}
#         \hline
#         \multicolumn{2}{|c|}{Header} & Value \\
#         \hline
#         a & b & c \\
#         \hline
#     \end{tabular}
#     """
#     token, end_pos = handler.handle(text.strip())
    
#     assert token is not None
#     assert token["type"] == "tabular"
#     assert token["column_spec"] == "|c|c|c|"
#     assert len(token["content"]) == 2
    
#     # First row with multicolumn
#     assert len(token["content"][0]) == 2
#     assert token["content"][0][0] == "Header"
#     assert token["content"][0][0]["colspan"] == 2
#     assert token["content"][0][1] == "Value"
    
#     # Second row
#     assert token["content"][1] == ["a", "b", "c"]

# def test_tabular_with_equations(handler):
#     text = r"""
#     \begin{tabular}{cc}
#         $x^2$ & $y^2$ \\
#         $\alpha$ & $\beta$
#     \end{tabular}
#     """.strip()
#     token, end_pos = handler.handle(text.strip())
    
#     assert token is not None
#     assert token["type"] == "tabular"
#     assert token["column_spec"] == "cc"
#     assert len(token["content"]) == 2
    
#     # Check equations in cells
#     for row in token["content"]:
#         for cell in row:
#             assert cell["type"] == "equation"
#             assert cell["display"] == "inline"

# def test_tabular_with_nested_content(handler):
#     text = r"""
#     \begin{tabular}{|l|c|}
#         \hline
#         Text & \begin{equation} E = mc^2 \end{equation} \\
#         \hline
#         More text & \begin{align} F = ma \\ p = mv \end{align} \\
#         \hline
#     \end{tabular}
#     """.strip()
#     token, end_pos = handler.handle(text.strip())
    
#     assert token is not None
#     assert token["type"] == "tabular"
#     assert token["column_spec"] == "|l|c|"
#     assert len(token["content"]) == 2
    
#     # Check first row
#     assert token["content"][0][0] == "Text"
#     assert token["content"][0][1]["type"] == "equation"
#     assert token["content"][0][1]["display"] == "block"
#     assert "E = mc^2" in token["content"][0][1]["content"]
    
#     # Check second row
#     assert token["content"][1][0] == "More text"
#     assert token["content"][1][1]["type"] == "equation"
#     assert token["content"][1][1]["display"] == "block"
#     assert "F = ma" in token["content"][1][1]["content"]
#     assert "p = mv" in token["content"][1][1]["content"]

# def test_tabular_with_custom_cell_parser(handler):
#     def custom_cell_parser(content):
#         return {"type": "custom", "content": content}
    
#     handler = TabularHandler(cell_parser_fn=custom_cell_parser)
#     text = r"""
#     \begin{tabular}{cc}
#         Cell1 & Cell2 \\
#         Cell3 & Cell4
#     \end{tabular}
#     """.strip()
#     token, end_pos = handler.handle(text.strip())
    
#     assert token is not None
#     assert token["type"] == "tabular"
    
#     # Check custom parsing of cells
#     for row in token["content"]:
#         for cell in row:
#             assert cell["type"] == "custom"
#             assert "content" in cell

# def test_invalid_tabular(handler):
#     text = r"""
#     \begin{not_tabular}{cc}
#         a & b \\
#         c & d
#     \end{not_tabular}
#     """.strip()
#     token, end_pos = handler.handle(text.strip())
#     assert token is None
#     assert end_pos == 0

# def test_tabular_with_process_content(handler):
#     def process_content(content):
#         return content.replace("REPLACE", "processed")
    
#     handler = TabularHandler(process_content_fn=process_content)
#     text = r"""
#     \begin{tabular}{cc}
#         REPLACE & normal \\
#         also & REPLACE
#     \end{tabular}
#     """.strip()
#     token, end_pos = handler.handle(text.strip())
    
#     assert token is not None
#     assert token["type"] == "tabular"
#     assert "processed" in token["content"][0][0]
#     assert "processed" in token["content"][1][1]

# def test_tabular_with_empty_cells(handler):
#     text = r"""
#     \begin{tabular}{ccc}
#         a & & c \\
#         & b & 
#     \end{tabular}
#     """.strip()
#     token, end_pos = handler.handle(text.strip())
    
#     assert token is not None
#     assert token["type"] == "tabular"
#     assert len(token["content"]) == 2
#     assert token["content"][0] == ["a", "", "c"]
#     assert token["content"][1] == ["", "b", ""]

# def test_can_handle_method(handler):
#     valid_text = r"\begin{tabular}{cc} a & b \\ \end{tabular}"
#     invalid_text = r"\begin{other}{cc} a & b \\ \end{other}"
    
#     assert handler.can_handle(valid_text) is True
#     assert handler.can_handle(invalid_text) is False
