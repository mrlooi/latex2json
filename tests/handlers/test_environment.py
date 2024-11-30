import pytest
from src.handlers.environment import EnvironmentHandler


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
    assert not handler.can_handle(r"\begin{testHSHSHS\end{}")
    assert not handler.can_handle("regular text")


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
    assert token == {
        "type": "table",
        "name": "table*",
        "content": "HSHSHS",
        "title": "h",
    }

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
        token["content"].replace(" ", "") == r"\begin{center}yoloswagMYTEXT\end{center}"
    )


def test_begingroup(handler):
    content = r"\begingroup\begin{center}Center\end{center}\endgroup hahaha"
    token, pos = handler.handle(content)
    assert token is not None
    assert content[pos:].strip() == "hahaha"

    # test nested groups
    content = r"\begingroup\begingroup\begin{center}Center\end{center}\endgroup\endgroup hahaha"
    token, pos = handler.handle(content)
    assert token is not None
    assert content[pos:].strip() == "hahaha"


if __name__ == "__main__":
    pytest.main([__file__])
