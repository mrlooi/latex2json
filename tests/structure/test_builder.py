import pytest
from src.tex_parser import LatexParser
from src.structure.builder import organize_content


@pytest.fixture
def latex_parser():
    return LatexParser()


@pytest.fixture
def latex_text():
    text = r"""
    \title{My Title}

    \begin{document}

    \abstract{This is my abstract}

    \paragraph{This is my paragraph}
    YEAAA baby

    \section{Intro} \label{sec:intro}

        Some text here, $1+1=2$:
        \begin{equation}
            E = mc^2
        \end{equation}

        \subsection{SubIntro}
        My name is \textbf{John Doe} \textbf{Sss} ahama

        \subsection*{SubIntro2}
        SUBINTRO 2
        \paragraph{Paragraph me}
        Hi there this is paragrpah

    \section{Conclusion}
        TLDR: Best paper

        \subsection{mini conclusion}
        Mini conclude

    \appendix

    \section{Appendix}
        My appendix

    \end{document}
    """

    return text


@pytest.fixture
def expected_output():
    return [
        {"type": "title", "title": "My Title"},
        {
            "type": "document",
            "name": "document",
            "content": [
                {"type": "abstract", "content": "This is my abstract"},
                {
                    "type": "paragraph",
                    "title": "This is my paragraph",
                    "level": 1,
                    "content": [{"type": "text", "content": "YEAAA baby"}],
                },
                {
                    "type": "section",
                    "title": "Intro",
                    "level": 1,
                    "numbered": True,
                    "labels": ["sec:intro"],
                    "content": [
                        {"type": "text", "content": "Some text here, $1+1=2$:"},
                        {
                            "type": "equation",
                            "content": "E = mc^2",
                            "display": "block",
                            "numbered": True,
                        },
                        {
                            "type": "section",
                            "title": "SubIntro",
                            "level": 2,
                            "numbered": True,
                            "content": [
                                {"type": "text", "content": "My name is "},
                                {
                                    "type": "text",
                                    "content": "John Doe Sss",
                                    "styles": ["bold"],
                                },
                                {"type": "text", "content": "ahama"},
                            ],
                        },
                        {
                            "type": "section",
                            "title": "SubIntro2",
                            "level": 2,
                            "numbered": False,
                            "content": [
                                {"type": "text", "content": "SUBINTRO 2"},
                                {
                                    "type": "paragraph",
                                    "title": "Paragraph me",
                                    "level": 1,
                                    "content": [
                                        {
                                            "type": "text",
                                            "content": "Hi there this is paragrpah",
                                        }
                                    ],
                                },
                            ],
                        },
                    ],
                },
                {
                    "type": "section",
                    "title": "Conclusion",
                    "level": 1,
                    "numbered": True,
                    "content": [
                        {"type": "text", "content": "TLDR: Best paper"},
                        {
                            "type": "section",
                            "title": "mini conclusion",
                            "level": 2,
                            "numbered": True,
                            "content": [{"type": "text", "content": "Mini conclude"}],
                        },
                    ],
                },
                {"type": "appendix"},
                {
                    "type": "section",
                    "title": "Appendix",
                    "level": 1,
                    "numbered": True,
                    "content": [{"type": "text", "content": "My appendix"}],
                },
            ],
        },
    ]


def strip_content_str(content):
    """Helper function to remove newline characters from the content."""
    if isinstance(content, list):
        return [strip_content_str(item) for item in content]
    if isinstance(content, dict):
        return {k: strip_content_str(v) for k, v in content.items()}
    if isinstance(content, str):
        return content.replace("\n", "").strip()
    return content


def test_organize_content(latex_parser, latex_text, expected_output):
    tokens = latex_parser.parse(latex_text)
    organized_tokens = organize_content(tokens)

    # Normalize both the organized tokens and expected output
    normalized_organized = strip_content_str(organized_tokens)
    normalized_expected = strip_content_str(expected_output)

    assert normalized_organized == normalized_expected
