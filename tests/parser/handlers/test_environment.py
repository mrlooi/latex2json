import pytest
from latex2json.parser.handlers.environment import (
    EnvironmentHandler,
    convert_any_env_pairs_to_begin_end,
)
from latex2json.parser.handlers.new_definition import NewDefinitionHandler


@pytest.fixture
def handler():
    return EnvironmentHandler()


@pytest.fixture
def newdef_handler():
    return NewDefinitionHandler()


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
    handler.process_newenvironment("test", r"\begin{center} #1 #2", r"\end{center}", 2)

    content = r"""
    \begin{test}{yolo}{swag}  MY TEXT\end{test}
    """.strip()
    token, pos = handler.handle(content)

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


def test_comment_env(handler):
    content = r"\begin{comment} stuff \end{comment} post"
    token, pos = handler.handle(content)
    assert token is None
    assert content[pos:] == " post"


def test_newenvironment(handler, newdef_handler):
    content = r"\newenvironment{proof}[1][default]{begin proof: #1}{end proof}"
    token, pos = newdef_handler.handle(content)
    assert token["name"] == "proof"
    assert token["type"] == "newenvironment"
    assert token["num_args"] == 1
    assert token["optional_args"] == ["default"]

    handler.process_newenvironment(
        token["name"],
        token["begin_def"],
        token["end_def"],
        token["num_args"],
        token["optional_args"],
    )

    content = r"\begin{proof}[Proof 1]stuff\end{proof} post"
    token, pos = handler.handle(content)
    assert token["name"] == "proof"
    assert (
        token["type"] == "math_env"
    )  # retains environment type even if newenvironment
    assert token["content"].strip() == "begin proof: Proof 1\nstuff\nend proof"
    assert content[pos:] == " post"


if __name__ == "__main__":
    pytest.main([__file__])
