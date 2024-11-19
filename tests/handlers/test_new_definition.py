import pytest
from src.handlers.new_definition import NewDefinitionHandler

@pytest.fixture
def handler():
    return NewDefinitionHandler()

def test_can_handle_definitions(handler):
    assert handler.can_handle(r"\newcommand{\cmd}{definition}")
    assert handler.can_handle(r"\renewcommand\cmd{definition}")
    assert handler.can_handle(r"\newenvironment{env}{begin}{end}")
    assert handler.can_handle(r"\newtheorem{thm}{Theorem}")
    assert not handler.can_handle("regular text")

def test_handle_newcommand(handler):
    # Test basic newcommand
    content = r"\newcommand{\cmd}{some definition}"
    token, pos = handler.handle(content)
    assert token["type"] == "newcommand"
    assert token["name"] == "cmd"
    assert token["content"] == "some definition"
    
    # Test with number of arguments
    content = r"\newcommand{\cmd}[2]{arg1=#1, arg2=#2}"
    token, pos = handler.handle(content)
    assert token["type"] == "newcommand"
    assert token["name"] == "cmd"
    assert token["num_args"] == 2
    assert token["content"] == "arg1=#1, arg2=#2"
    
    # Test with default values
    content = r"\newcommand{\cmd}[2][default]{arg1=#1, arg2=#2}"
    token, pos = handler.handle(content)
    assert token == {
        "type": "newcommand",
        "name": "cmd",
        "num_args": 2,
        "defaults": ["default"],
        "content": "arg1=#1, arg2=#2"
    }

def test_handle_renewcommand(handler):
    content = r"\renewcommand{\cmd}{new definition}"
    token, pos = handler.handle(content)

    assert token["type"] == "newcommand"
    assert token["name"] == "cmd"
    assert token["content"] == "new definition"

def test_handle_newenvironment(handler):
    # Test basic newenvironment
    content = r"\newenvironment{test}{begin def}{end def}"
    token, pos = handler.handle(content)
    assert token == {
        "type": "newenvironment",
        "name": "test",
        "args": [],
        "optional_args": [],
        "begin_def": "begin def",
        "end_def": "end def"
    }
    
    # Test with arguments
    content = r"\newenvironment{test}[2]{begin #1 #2}{end #2}"
    token, pos = handler.handle(content)
    assert token == {
        "type": "newenvironment",
        "name": "test",
        "args": ["#1", "#2"],
        "optional_args": [],
        "begin_def": "begin #1 #2",
        "end_def": "end #2"
    }
    
    # Test with optional arguments
    content = r"\newenvironment{test}[2][default]{begin #1 #2}{end}"
    token, pos = handler.handle(content)
    assert token == {
        "type": "newenvironment",
        "name": "test",
        "args": ["#1", "#2"],
        "optional_args": ["default"],
        "begin_def": "begin #1 #2",
        "end_def": "end"
    }

def test_handle_newtheorem(handler):
    # Test basic newtheorem
    content = r"\newtheorem{theorem}{Theorem}"
    token, pos = handler.handle(content)
    assert token == {
        "type": "theorem",
        "name": "theorem",
        "title": "Theorem"
    }
    
    # Test with counter specification
    content = r"\newtheorem{lemma}[theorem]{Lemma}"
    token, pos = handler.handle(content)
    assert token == {
        "type": "theorem",
        "name": "lemma",
        "counter": "theorem",
        "title": "Lemma"
    }
    
    # Test with numbering within
    content = r"\newtheorem{proposition}{Proposition}[section]"
    token, pos = handler.handle(content)
    assert token == {
        "type": "theorem",
        "name": "proposition",
        "title": "Proposition",
        "within": "section"
    }

def test_handle_invalid_input(handler):
    # Test with non-command content
    token, pos = handler.handle("regular text")
    assert token is None
    assert pos == 0
    
    # Test with malformed commands
    assert not handler.can_handle(r"\newcommand{\cmd")
    
    token, pos = handler.handle(r"\newenvironment{env}{begin")
    assert token is None
    assert pos > 0

def test_handle_complex_definitions(handler):
    # Test newcommand with nested braces
    content = r"\newcommand{\complex}[2]{outer{nested{#1}}{#2}}"
    token, pos = handler.handle(content)

    assert token["type"] == "newcommand"
    assert token["name"] == "complex"
    assert token["num_args"] == 2
    assert token["content"] == "outer{nested{#1}}{#2}"
    
    # Test newenvironment with complex begin/end definitions
    content = r"\newenvironment{complex}{\begin{center}\begin{tabular}}{end{tabular}\end{center}}"
    token, pos = handler.handle(content)
    assert token == {
        "type": "newenvironment",
        "name": "complex",
        "args": [],
        "optional_args": [],
        "begin_def": r"\begin{center}\begin{tabular}",
        "end_def": r"end{tabular}\end{center}"
    }

if __name__ == "__main__":
    pytest.main([__file__]) 