import pytest
from src.tex_utils import (
    extract_nested_content_sequence_blocks,
    extract_nested_content_pattern,
    find_matching_env_block,
)
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
    start, end, content = extract_nested_content_pattern(text, r"\(", r"\)")
    assert start == 0
    assert text[end:] == " post"
    assert content == "(inner)"

    # Test with compiled patterns
    begin_pat = re.compile(r"\(")
    end_pat = re.compile(r"\)")
    start, end, content = extract_nested_content_pattern(text, begin_pat, end_pat)
    assert start == 0
    assert text[end:] == " post"
    assert content == "(inner)"

    # Test with multiple nesting levels
    text = "((a(b)c)) post"
    start, end, content = extract_nested_content_pattern(text, r"\(", r"\)")
    assert start == 0
    assert text[end:] == " post"
    assert content == "(a(b)c)"

    # Test with no match
    text = "(unclosed"
    start, end, content = extract_nested_content_pattern(text, r"\(", r"\)")
    assert (start, end, content) == (-1, -1, "")

    # Test with no begin pattern
    text = "no patterns here"
    start, end, content = extract_nested_content_pattern(text, r"\(", r"\)")
    assert (start, end, content) == (-1, -1, "")

    # Test with LaTeX-style environments
    text = r"\begin{test}content\begin{inner}nested\end{inner}more\end{test}"
    start, end, content = extract_nested_content_pattern(
        text, r"\\begin\{test\}", r"\\end\{test\}"
    )
    assert start == 0
    assert end == len(text)
    assert content == r"content\begin{inner}nested\end{inner}more"

    # real csname test
    text = r"\def \csname test\endcsname POST"
    start, end, content = extract_nested_content_pattern(
        text, r"\\csname", r"\\endcsname"
    )
    assert start == text.index(r"\csname")
    assert text[end:] == " POST"
    assert content.strip() == "test"


def test_extract_nested_content_blocks():
    text = r"{test}{test2} {test3} sssss"
    blocks, total_pos = extract_nested_content_sequence_blocks(text, "{", "}", 3)
    assert blocks == ["test", "test2", "test3"]
    assert text[total_pos:] == " sssss"

    blocks, total_pos = extract_nested_content_sequence_blocks(text, "{", "}", 2)
    assert blocks == ["test", "test2"]
    assert text[total_pos:] == " {test3} sssss"

    text = r"ssss {ssss}"
    blocks, total_pos = extract_nested_content_sequence_blocks(text, "{", "}", 2)
    assert blocks == []
    assert text[total_pos:] == "ssss {ssss}"

    # with nested nested blocks
    text = r"{ aaaa {bbbb}   } {11{22{33 }}  } aaaa {1123}"
    blocks, total_pos = extract_nested_content_sequence_blocks(text, "{", "}", 4)
    assert blocks == [" aaaa {bbbb}   ", "11{22{33 }}  "]
    assert text[total_pos:] == " aaaa {1123}"
