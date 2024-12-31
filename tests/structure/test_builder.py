import pytest
from src.tex_parser import LatexParser
from src.structure.builder import TokenBuilder
from src.handlers.text_formatting import FRONTEND_STYLE_MAPPING


@pytest.fixture
def latex_parser():
    return LatexParser()


@pytest.fixture
def latex_text():
    text = r"""
    \title{My Title}

    \begin{document}

    \abstract{This is my abstract, \texttiny{cool yes?}}

    \paragraph{This is my paragraph}
    YEAAA baby

    \section{Intro} \label{sec:intro}

        Some text here, $1+1=2$:
        \begin{equation}
            E = mc^2
        \end{equation}

        \begin{figure}[h]
            \includegraphics[page=1]{mypdf.pdf}
            \caption{My figure, from \cite{bibkey1}}
        \end{figure}

        \subsection{SubIntro}
        My name is \textbf{John Doe} \textbf{Sss} ahama

        \subsection*{SubIntro2}
        SUBINTRO 2
        \paragraph{Paragraph me}
        Hi there this is paragraph

    \section{Conclusion}
        TLDR: Best paper

        \subsection{mini conclusion}
        Mini conclude
        
        \begin{align*}
            F = ma
        \end{align*}

    \appendix

    \section{Appendix}
        My appendix
    
    \subsubsection{Abt appendix}
    Yea this appendix is nice

    \begin{thebibliography}{99}
    \bibitem[Title]{bibkey1} Some content \tt cool
    \end{thebibliography}

    \end{document}
    """

    return text


@pytest.fixture
def expected_output():
    return [
        {"type": "title", "title": [{"type": "text", "content": "My Title"}]},
        {
            "type": "document",
            "name": "document",
            "content": [
                {
                    "type": "abstract",
                    "content": [
                        {"type": "text", "content": "This is my abstract,"},
                        {
                            "type": "text",
                            "content": "cool yes?",
                            "styles": [FRONTEND_STYLE_MAPPING["texttiny"]],
                        },
                    ],
                },
                {
                    "type": "paragraph",
                    "title": [{"type": "text", "content": "This is my paragraph"}],
                    "level": 1,
                    "content": [{"type": "text", "content": "YEAAA baby"}],
                },
                {
                    "type": "section",
                    "title": [{"type": "text", "content": "Intro"}],
                    "level": 1,
                    "numbering": "1",
                    "numbered": True,
                    "labels": ["sec:intro"],
                    "content": [
                        {"type": "text", "content": "Some text here, $1+1=2$:"},
                        {
                            "type": "equation",
                            "content": "E = mc^2",
                            "display": "block",
                            "numbered": True,
                            "numbering": "1",
                        },
                        {
                            "type": "figure",
                            "name": "figure",
                            "numbered": True,
                            "title": "h",
                            "content": [
                                {
                                    "type": "includegraphics",
                                    "content": "mypdf.pdf",
                                    "page": 1,
                                },
                                {
                                    "type": "caption",
                                    "content": [
                                        {"type": "text", "content": "My figure, from"},
                                        {
                                            "type": "citation",
                                            "content": "bibkey1",
                                        },
                                    ],
                                },
                            ],
                        },
                        {
                            "type": "section",
                            "title": [{"type": "text", "content": "SubIntro"}],
                            "level": 2,
                            "numbering": "1.1",
                            "numbered": True,
                            "content": [
                                {"type": "text", "content": "My name is "},
                                {
                                    "type": "text",
                                    "content": "John Doe Sss",
                                    "styles": [FRONTEND_STYLE_MAPPING["textbf"]],
                                },
                                {"type": "text", "content": "ahama"},
                            ],
                        },
                        {
                            "type": "section",
                            "title": [{"type": "text", "content": "SubIntro2"}],
                            "level": 2,
                            "numbered": False,
                            "content": [
                                {"type": "text", "content": "SUBINTRO 2"},
                                {
                                    "type": "paragraph",
                                    "title": [
                                        {"type": "text", "content": "Paragraph me"}
                                    ],
                                    "level": 1,
                                    "content": [
                                        {
                                            "type": "text",
                                            "content": "Hi there this is paragraph",
                                        }
                                    ],
                                },
                            ],
                        },
                    ],
                },
                {
                    "type": "section",
                    "title": [{"type": "text", "content": "Conclusion"}],
                    "level": 1,
                    "numbering": "2",
                    "numbered": True,
                    "content": [
                        {"type": "text", "content": "TLDR: Best paper"},
                        {
                            "type": "section",
                            "title": [{"type": "text", "content": "mini conclusion"}],
                            "level": 2,
                            "numbering": "2.1",
                            "numbered": True,
                            "content": [
                                {"type": "text", "content": "Mini conclude"},
                                {
                                    "type": "equation",
                                    "content": "F = ma",
                                    "display": "block",
                                    "align": True,
                                },
                            ],
                        },
                    ],
                },
                {"type": "appendix"},
                {
                    "type": "section",
                    "title": [{"type": "text", "content": "Appendix"}],
                    "level": 1,
                    "numbering": "3",
                    "numbered": True,
                    "content": [
                        {"type": "text", "content": "My appendix"},
                        {
                            "type": "section",
                            "title": [{"type": "text", "content": "Abt appendix"}],
                            "level": 3,
                            "numbering": "3.0.1",
                            "numbered": True,
                            "content": [
                                {"type": "text", "content": "Yea this appendix is nice"}
                            ],
                        },
                    ],
                },
                {
                    "type": "bibliography",
                    "name": "thebibliography",
                    "args": ["99"],
                    "content": [
                        {
                            "type": "bibitem",
                            "content": [
                                {"type": "text", "content": "Some content "},
                                {
                                    "type": "text",
                                    "content": "cool",
                                    "styles": [FRONTEND_STYLE_MAPPING["texttt"]],
                                },
                            ],
                            "cite_key": "bibkey1",
                            "title": "Title",
                        }
                    ],
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
    token_builder = TokenBuilder()
    organized_tokens = token_builder.organize_content(tokens)

    # Normalize both the organized tokens and expected output
    normalized_organized = strip_content_str(organized_tokens)
    normalized_expected = strip_content_str(expected_output)

    assert normalized_organized == normalized_expected
