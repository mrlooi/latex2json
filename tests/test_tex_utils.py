import pytest
from src.tex_utils import extract_nested_content_pattern, find_matching_env_block
import re


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

    # test with prefix
    text = r"prefix\begin{test}content\end{test}suffix"
    start, end, content = find_matching_env_block(text, "test", start_pos=6)
    assert start == len("prefix")
    assert content == "content"
    assert text[end:] == "suffix"

    # test with start_pos
    text = r"\begin{test}outer\begin{test}inner\end{test}outer\end {test}"
    check_start = len(r"\begin{test}out")
    start, end, content = find_matching_env_block(text, "test", start_pos=check_start)
    assert start == check_start + len("er")
    assert content == r"inner"
    assert text[end:] == r"outer\end {test}"


def test_extract_nested_content_pattern():
    # Basic test with string patterns
    text = "((inner)) post"
    content, pos = extract_nested_content_pattern(text, r"\(", r"\)")
    assert content == "(inner)"
    assert text[pos:] == " post"

    # Test with compiled patterns
    begin_pat = re.compile(r"\(")
    end_pat = re.compile(r"\)")
    content, pos = extract_nested_content_pattern(text, begin_pat, end_pat)
    assert content == "(inner)"
    assert text[pos:] == " post"

    # Test with multiple nesting levels
    text = "((a(b)c)) post"
    content, pos = extract_nested_content_pattern(text, r"\(", r"\)")
    assert content == "(a(b)c)"
    assert text[pos:] == " post"

    # Test with no match
    text = "(unclosed"
    content, pos = extract_nested_content_pattern(text, r"\(", r"\)")
    assert content is None
    assert pos == 0

    # Test with no begin pattern
    text = "no patterns here"
    content, pos = extract_nested_content_pattern(text, r"\(", r"\)")
    assert content is None
    assert pos == 0

    # Test with LaTeX-style environments
    text = r"\begin{test}content\begin{inner}nested\end{inner}more\end{test}"
    content, pos = extract_nested_content_pattern(
        text, r"\\begin\{test\}", r"\\end\{test\}"
    )
    assert content == r"content\begin{inner}nested\end{inner}more"
    assert pos == len(text)
