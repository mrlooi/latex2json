import pytest
from src.tex_utils import find_matching_env_block


def test_find_matching_env_block():
    # Basic test
    text = r"\begin{test}inner content\end{test}"
    start, end, content = find_matching_env_block(text, "test")
    assert content == "inner content"

    # Nested environments
    text = r"\begin{test}outer\begin{test}inner\end{test}outer\end {test}"
    start, end, content = find_matching_env_block(text, "test")
    assert content == r"outer\begin{test}inner\end{test}outer"

    # No matching environment
    text = r"\begin{test}content without end"
    start, end, content = find_matching_env_block(text, "test")
    assert (start, end, content) == (-1, -1, "")

    # Wrong environment name
    text = r"\begin{test}content\end{other}"
    start, end, content = find_matching_env_block(text, "test")
    assert (start, end, content) == (-1, -1, "")

    # With whitespace
    text = r"\begin {test}  inner content  \end{test}"
    start, end, content = find_matching_env_block(text, "test")
    assert content.strip() == "inner content"
