import pytest
from src.handlers.environment import (
    EnvironmentHandler,
    convert_any_env_pairs_to_begin_end,
)


@pytest.fixture
def handler():
    return EnvironmentHandler()


def test_can_handle_newenvironments(handler):
    assert handler.can_handle(r"\newenvironment{test}{begin def}{end def}")
    assert not handler.can_handle("regular text")


def test_handle_newenvironment(handler):
    # Test basic newenvironment
    content = r"\newenvironment{test}{begin def}{end def}"
    token, pos = handler.handle(content)

    assert "test" in handler.environments
    assert handler.environments["test"] == {
        "name": "test",
        "args": {"num_args": 0, "optional_args": []},
        "begin_def": "begin def",
        "end_def": "end def",
    }

    # Test with arguments
    content = r"\newenvironment{test2}[2]{begin #1 #2}{end #2}"
    token, pos = handler.handle(content)
    assert "test2" in handler.environments
    assert handler.environments["test2"] == {
        "name": "test2",
        "args": {"num_args": 2, "optional_args": []},
        "begin_def": "begin #1 #2",
        "end_def": "end #2",
    }

    # Test with optional arguments
    content = r"\newenvironment{test3}[2][default]{begin #1 #2}{end}"
    token, pos = handler.handle(content)
    assert "test3" in handler.environments
    assert handler.environments["test3"] == {
        "name": "test3",
        "args": {"num_args": 2, "optional_args": ["default"]},
        "begin_def": "begin #1 #2",
        "end_def": "end",
    }

    # Test newenvironment with complex begin/end definitions
    content = r"\newenvironment{complex}{\begin{center}\begin{tabular}}{end{tabular}\end{center}}"
    token, pos = handler.handle(content)
    assert "complex" in handler.environments
    assert handler.environments["complex"] == {
        "name": "complex",
        "args": {"num_args": 0, "optional_args": []},
        "begin_def": r"\begin{center}\begin{tabular}",
        "end_def": r"end{tabular}\end{center}",
    }

    handler.clear()


def test_can_handle_environment(handler):
    assert handler.can_handle(r"\begin{test}HSHSHS\end{test}")
    assert not handler.can_handle("regular text")
    assert not handler.can_handle(r"\begin{test")


def test_handle_environment(handler):
    content = r"\begin{test}HSHSHS\end{test}"
    token, pos = handler.handle(content)
    assert token == {"type": "environment", "name": "test", "content": "HSHSHS"}

    # appendix
    content = r"\begin{appendices}HSHSHS\end{appendices} POST APPENDIX"
    token, pos = handler.handle(content)
    assert token["type"] == "appendix"
    assert token["content"] == "HSHSHS"
    assert token["name"] == "appendices"
    assert content[pos:] == " POST APPENDIX"


def test_handle_environment_with_asterisk(handler):
    content = r"\begin{table*}[h]HSHSHS\end{table*} muhaha"
    token, pos = handler.handle(content)
    assert token["type"] == "table"
    assert token["content"] == "HSHSHS"

    assert content[pos:].strip() == "muhaha"


def test_env_with_newenvironment(handler):
    content = r"""
    \newenvironment{test}[2]{\begin{center} #1 #2}{\end{center}}
    \begin{test}{yolo}{swag}  MY TEXT\end{test}
    """.strip()
    token, pos = handler.handle(content)
    assert token is None

    next_content = content[pos:].strip()
    token, pos = handler.handle(next_content)

    assert token["type"] == "environment"
    assert token["name"] == "test"
    assert (
        token["content"].replace(" ", "").replace("\n", "")
        == r"\begin{center}yoloswagMYTEXT\end{center}"
    )


def test_begingroup(handler):
    content = r"\bgroup\begin{center}Center\end{center}\egroup hahaha"
    token, pos = handler.handle(content)
    assert token["content"] == r"\begin{center}Center\end{center}"
    assert content[pos:] == " hahaha"

    # test nested groups
    content = (
        r"\begingroup\bgroup\begin{center}Center\end{center}\egroup\endgroup hahaha"
    )
    token, pos = handler.handle(content)
    assert token["content"] == r"\bgroup\begin{center}Center\end{center}\egroup"
    assert content[pos:] == " hahaha"


def test_nested_identical_environments(handler):
    content = r"""
    \begin{block}
    BLOCK 1 PRE
    \begin{block}
    BLOCK 2
    \end{block}
    BLOCK 1 POST
    \end{block}

    AFTER END
    """.strip()

    token, pos = handler.handle(content)
    assert token is not None

    c = token["content"].strip()
    assert c.endswith("BLOCK 1 POST")

    assert content[pos:].strip() == "AFTER END"


def test_env_pairs_without_begin(handler):
    content = r"\list{}{} \item[] \endlist post"
    token, pos = handler.handle(content)
    assert token is not None
    assert token["name"] == "list"
    assert token["content"].strip() == r"\item[]"
    assert content[pos:] == " post"

    # nested
    content = r"\xxx stuff \xxx nested \endxxx postnested \endxxx post"
    token, pos = handler.handle(content)
    assert token["name"] == "xxx"
    assert token["content"] == r" stuff \xxx nested \endxxx postnested "
    assert content[pos:] == " post"


def test_convert_any_env_pairs_to_begin_end(handler):
    content = r"\xxx stuff \endxxx aaa"
    assert (
        convert_any_env_pairs_to_begin_end(content)
        == r"\begin{xxx} stuff \end{xxx} aaa"
    )

    content = r"\xxx stuff \endxxx aaa \xxx stuff \endxxx bbb"
    assert (
        convert_any_env_pairs_to_begin_end(content)
        == r"\begin{xxx} stuff \end{xxx} aaa \begin{xxx} stuff \end{xxx} bbb"
    )

    content = r"""
    \xxx stuff 
        \yyy stuff
        \endyyy 
        ccc
    \endxxx aaa
"""

    expect = r"""
    \begin{xxx} stuff 
        \begin{yyy} stuff
        \end{yyy} 
        ccc
    \end{xxx} aaa
"""
    assert convert_any_env_pairs_to_begin_end(content) == expect


def test_with_float_env(handler):
    content = r"\@float{table}[b] stuff \end@float post"
    token, pos = handler.handle(content)
    assert token["name"] == "table"
    assert token["type"] == "table"
    assert token["content"] == " stuff "
    assert content[pos:] == " post"


def test_process_newtheorem(handler):
    handler.process_newtheorem("mytheoremmm", "theorem")
    content = r"\begin{mytheoremmm} stuff \end{mytheoremmm} post"
    token, pos = handler.handle(content)
    assert token["name"] == "theorem"
    assert token["type"] == "math_env"
    assert token["content"].strip() == "stuff"
    assert content[pos:] == " post"


def test_commenting_inside_env(handler):
    text = r"""
    \begin{table}
    PRE 

    %\end{table}
    %\begin{table}

    POST
    \end{table}
    """.strip()

    token, pos = handler.handle(text)
    assert token["name"] == "table"
    assert token["type"] == "table"

    expected = r"""
    PRE 

    %\end{table}
    %\begin{table}

    POST
"""
    assert token["content"].strip() == expected.strip()


if __name__ == "__main__":
    pytest.main([__file__])
