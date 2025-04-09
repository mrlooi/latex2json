import pytest
from latex2json.utils.tex_utils import (
    extract_nested_content_sequence_blocks,
    extract_nested_content_pattern,
    find_matching_env_block,
    has_comment_on_sameline,
    find_matching_delimiter,
    normalize_whitespace_and_lines,
    strip_latex_comments,
    find_delimiter_end,
    extract_equation_content,
    substitute_args,
)
from latex2json.utils.conversions import int_to_roman
import re


def test_int_to_roman():
    assert int_to_roman(1) == "i"
    assert int_to_roman(123) == "cxxiii"
    assert int_to_roman(1234) == "mccxxxiv"


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


def test_normalize_whitespace_and_lines():
    input_text = "Hello\nworld"
    expected = "Hello world"
    assert normalize_whitespace_and_lines(input_text) == expected

    input_text = "Hello\n\nworld"
    expected = "Hello\nworld"
    assert normalize_whitespace_and_lines(input_text) == expected

    input_text = "Line one.\nLine two.\n\nLine three.\n  \n  Line four."
    expected = "Line one. Line two.\nLine three.\nLine four."
    assert normalize_whitespace_and_lines(input_text) == expected

    input_text = "Hello    world"
    expected = "Hello world"
    assert normalize_whitespace_and_lines(input_text) == expected

    input_text = "A  \n   B"
    expected = "A B"
    assert normalize_whitespace_and_lines(input_text) == expected

    input_text = "   Hello world   "
    expected = "Hello world"
    assert normalize_whitespace_and_lines(input_text) == expected


def test_find_delimiter_end():
    # Basic test with single character delimiter
    text = "Hello $equation$ end"
    end_pos = find_delimiter_end(text, 8, "$")
    assert end_pos == len("Hello $equation$")

    # Test with multi-character delimiter
    text = "Start $$display math$$ end"
    end_pos = find_delimiter_end(text, 8, "$$")
    assert end_pos == len("Start $$display math$$")

    # Test with escaped delimiters
    text = r"$\$ not end $ real end$"
    end_pos = find_delimiter_end(text, 2, "$")
    assert end_pos == len(r"$\$ not end $")

    # Test with no matching delimiter
    text = "$unclosed equation"
    end_pos = find_delimiter_end(text, 1, "$")
    assert end_pos == -1


def test_strip_latex_comments_advanced():
    # Test with multiple escaped percents
    text = r"Line with \% and \% and % real comment"
    assert strip_latex_comments(text) == r"Line with \% and \% and"

    # Test with multiple consecutive comments
    text = "First % comment 1\n% comment 2\n% comment 3\nValid line"
    assert strip_latex_comments(text) == "First\n\n\nValid line"

    # Test with mixed spaces and tabs
    text = "Text\t% comment\n  % indented comment  \n\tCode"
    assert strip_latex_comments(text) == "Text\n\n\tCode"

    # Test with empty lines between comments
    text = "% comment 1\n\n% comment 2\n\nValid line"
    assert strip_latex_comments(text) == "\n\n\n\nValid line"

    # Test with escaped backslashes before percent
    text = r"Text with \\% not a comment and % real comment"
    assert strip_latex_comments(text) == r"Text with \\% not a comment and"


def test_find_matching_delimiter_edge_cases():
    # Test with empty input
    assert find_matching_delimiter("") == (-1, -1)

    # Test with only whitespace
    assert find_matching_delimiter("   \n\t  ") == (-1, -1)

    # Test with escaped delimiters at string boundaries
    text = r"\{content\}"
    assert find_matching_delimiter(text) == (-1, -1)

    # Test with nested comments
    text = "{outer % {comment} \n inner}"
    start, end = find_matching_delimiter(text)
    assert text[start:end] == "{outer % {comment} \n inner}"

    # Test with multiple escaped delimiters
    text = r"{\{ \} \{ \}}"
    start, end = find_matching_delimiter(text)
    assert text[start:end] == r"{\{ \} \{ \}}"

    # Test with mixed escaping
    text = r"{not \} escaped but \{ is}"
    start, end = find_matching_delimiter(text)
    assert text[start:end] == r"{not \} escaped but \{ is}"


def test_substitute_args():
    # Basic single argument substitution
    assert substitute_args("#1", ["arg1"]) == "arg1"

    # Multiple arguments
    assert substitute_args("#1 #2", ["first", "second"]) == "first second"

    # Double hash notation
    assert substitute_args("##1", ["arg1"]) == "arg1"

    # Triple hash notation (should not substitute)
    assert substitute_args("###1 #1", ["arg1"]) == "###1 arg1"

    # Missing arguments (should keep original)
    assert substitute_args("#1 #2", ["only_one"]) == "only_one #2"

    # No arguments
    assert substitute_args("no args here", []) == "no args here"

    # None arguments should be removed
    assert substitute_args("#1 middle #2", ["start", None]) == "start middle "

    # Complex pattern with mixed hashes
    assert substitute_args("##1 ###2 #1", ["arg"]) == "##1 ###2 arg"

    # Numbers without hashes should be preserved
    assert substitute_args("1 #1 1", ["arg"]) == "1 arg 1"

    # Test with escaped hashes
    assert substitute_args("\\#1 #1", ["arg"]) == "\\#1 arg"

    # Test with escaped hashes in the middle
    assert substitute_args("hi # #1 \\#1 ##1", ["arg"]) == "hi # arg \\#1 ##1"

    # Test with escaped hashes in the middle
    assert substitute_args("\\##1 ##1", ["arg"]) == "\\#arg ##1"

    assert substitute_args("\\####1 \\##1 ##1", ["arg"]) == "\\####1 \\#arg ##1"

    assert (
        substitute_args("\\#\\####1 \\#1 ##1 \\###2", ["arg", "arg2"])
        == "\\#\\####1 \\#1 arg \\#arg2"
    )
