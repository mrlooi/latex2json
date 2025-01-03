import pytest
from latex_parser.utils.tex_utils import (
    extract_nested_content_sequence_blocks,
    extract_nested_content_pattern,
    find_matching_env_block,
    has_comment_on_sameline,
    find_matching_delimiter,
    strip_latex_comments,
)
import re


def test_find_matching_delimiter_with_comments():
    # Basic comment case
    text = "{test} % {invalid}"
    start, end = find_matching_delimiter(text)
    assert text[start:end] == "{test}"

    # Comment in the middle of nested delimiters
    text = "{outer{inn % {ignored}\ner}end}"  # removed r-prefix to allow real newline
    start, end = find_matching_delimiter(text)
    assert text[start:end] == "{outer{inn % {ignored}\ner}end}"

    # Multiple comments
    text = "{test} % comment 1 {invalid}\n{next} % comment 2"  # removed r-prefix
    start, end = find_matching_delimiter(text)
    assert text[start:end] == "{test}"

    # Escaped comment character
    text = r"{test \% not a comment {nested}}"
    start, end = find_matching_delimiter(text)
    assert text[start:end] == r"{test \% not a comment {nested}}"

    # Mixed escaped and unescaped comments
    text = (
        "{test \\% not a comment % but this is\nstill in {nested}}"  # removed r-prefix
    )
    start, end = find_matching_delimiter(text)
    assert (
        text[start:end] == "{test \\% not a comment % but this is\nstill in {nested}}"
    )

    text = r"""
    {
        test % }
        POST
    }
""".strip()
    start, end = find_matching_delimiter(text)
    assert text[start + 1 : end - 1].replace("\n", "").replace(" ", "") == "test%}POST"


def test_find_matching_delimiter_with_double_backslash():
    # Test multiple backslashes
    text = r"{not escaped} {\{escaped} \\\{escaped} \\{not escaped}"
    start, end = find_matching_delimiter(text)
    assert text[start:end] == r"{not escaped}"

    start, end = find_matching_delimiter(text, start=end)
    assert text[start:end] == r"{\{escaped}"

    text = r"{\\{not escaped}}"
    start, end = find_matching_delimiter(text)
    assert text[start:end] == r"{\\{not escaped}}"

    text = r"{\\\{escaped}"
    start, end = find_matching_delimiter(text)
    assert text[start:end] == r"{\\\{escaped}"


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

    # test with commented inner begin/end patterns
    text = r"""
    \begin{table}
    %\end{table}
    MID TABLE
    %\begin{table}
    \end{table}
    POST TABLE
"""
    start, end, content = extract_nested_content_pattern(
        text, r"\\begin{table}", r"\\end{table}"
    )
    assert start == text.index(r"\begin{table}")
    assert text[end:].strip() == "POST TABLE"

    expected = r"""
    %\end{table}
    MID TABLE
    %\begin{table}
""".strip()
    assert content.strip() == expected


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


def test_has_uncommented_percent_before():
    # Basic comment case
    text = r"% comment \begin{test}"
    assert has_comment_on_sameline(text, text.find(r"\begin"))

    # Escaped comment case
    text = r"\% not a comment \begin{test}"
    assert not has_comment_on_sameline(text, text.find(r"\begin"))

    # No comment case
    text = r"normal text \begin{test}"
    assert not has_comment_on_sameline(text, text.find(r"\begin"))

    # Comment after position
    text = r"\begin{test} % comment after"
    assert not has_comment_on_sameline(text, text.find(r"\begin"))

    # Multiple line case
    text = r"line1\n% comment \begin{test}"
    assert has_comment_on_sameline(text, text.find(r"\begin"))

    # Comment on previous line shouldn't affect current line
    text = "% comment\n \\begin{test}"
    assert not has_comment_on_sameline(text, text.find(r"\begin"))

    # Multiple escaped and unescaped comments
    text = r"\% not a comment % this is a comment \begin{test}"
    assert has_comment_on_sameline(text, text.find(r"\begin"))


def test_strip_latex_comments():
    # Test basic single-line comments
    text = r"This is code % with a comment"
    assert strip_latex_comments(text) == "This is code"

    # Test multiline text with various comment types
    text = r"""
    First line% with comment
    Second line with \% escaped percent % and a comment
    % Fully commented line
    No comments here
    Mixed line with \% escaped and % real comment
    """.strip()

    expected = r"""
    First line
    Second line with \% escaped percent

    No comments here
    Mixed line with \% escaped and""".strip()

    assert strip_latex_comments(text) == expected

    # Test empty lines and whitespace handling
    text = r"""
    % Comment only
    
    Text % Comment
      % Indented comment
        Text with space   % Comment
    """.strip()
