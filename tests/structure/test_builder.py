import pytest
from latex2json.parser.tex_parser import LatexParser
from latex2json.structure.builder import TokenBuilder
from latex2json.parser import FRONTEND_STYLE_MAPPING


@pytest.fixture
def latex_parser():
    return LatexParser()


@pytest.fixture
def latex_text():
    text = r"""
    \title{My Title}

    \author{
        Mr X \somecmd \\
        University of XYZ \\
    }

    \begin{document}

    \abstract{This is my abstract, \texttiny{cool yes?}}

    \paragraph{This is my paragraph}
    YEAAA baby

    \section{Intro $1+1$} \label{sec:intro}

        Some text here, $1+1=2$:
        \begin{equation}
            E = mc^2 \\ x = 1
        \end{equation}

        \begin{figure}[h]
            \includegraphics[page=1]{mypdf.pdf}
            \caption{My figure, from \cite{bibkey1}}
        \end{figure}

        \subsection{SubIntro}
        My name is \textbf{John Doe} \textbf{Sss} ahama \verb|my code|

        \begin{theorem}[$T=1$]
            Theorem 1
        \end{theorem}

        \subsection*{SubIntro2}
        SUBINTRO 2
        \paragraph{Paragraph me}
        Hi there this is paragraph

        \begin{theorem*}
            Theorem 2
        \end{theorem*}

        \subsection{Last sub section}

            \subsubsection{S3}
            \subsubsection{S4}

    \section{Conclusion}
        TLDR: Best paper

        \subsection{mini conclusion}
        Mini conclude
        
        \begin{align*}
            F = ma
        \end{align*}

        \begin{theorem}
            Theorem 3
        \end{theorem}

        \begin{algorithm}
            \caption{Binary Search}
        \end{algorithm}        

        \begin{tabular}{|c|c|}
            \hline
            Cell 1 & \textbf{Cell 2} & 3 \\
            \hline
            \multicolumn{2}{|c|}{Spanning Cell} &  \\
            & H1 \& H2 & 
            \hline
        \end{tabular}

        \begin{description}
        \item[\textbf{Hello}] World
        \item[Hello] % nested env
            \paragraph{This nested env inside}
                \begin{enumerate}
                \item 1
                \item 2
                \end{enumerate}
            World
        \end{description}

    \appendix

    \section{My Appendix Section}
        Here goes my appendix...
    
        \subsection{Sub appendix 1}
        Yea this appendix is nice

        \subsection{Sub appendix 2}

    \begin{thebibliography}{99}
    \bibitem[Title]{bibkey1} Some content \tt cool
    \end{thebibliography}

    \end{document}
    """

    return text


@pytest.fixture
def expected_organizer_output():
    return [
        {
            "type": "title",
            "title": [
                {"type": "text", "content": "My Title"},
            ],
        },
        {
            "type": "author",
            "content": [
                [
                    {"type": "text", "content": "Mr X "},
                    {"type": "command", "command": "\\somecmd"},
                    {"type": "text", "content": "University of XYZ"},
                ]
            ],
        },
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
                    "title": [
                        {"type": "text", "content": "Intro"},
                        {"type": "equation", "content": "1+1"},
                    ],
                    "level": 1,
                    "numbering": "1",
                    "numbered": True,
                    "labels": ["sec:intro"],
                    "content": [
                        {
                            "type": "text",
                            "content": "Some text here, ",
                        },
                        {"type": "equation", "content": "1+1=2"},
                        {
                            "type": "text",
                            "content": ":",
                        },
                        {
                            "type": "equation",
                            "content": "E = mc^2 \\\\ x = 1",
                            "display": "block",
                            "numbered": True,
                            "numbering": "1",
                        },
                        {
                            "type": "figure",
                            "name": "figure",
                            "numbered": True,
                            "numbering": "1",
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
                                {"type": "text", "content": "ahama "},
                                {
                                    "type": "code",
                                    "content": "my code",
                                    "display": "inline",
                                },
                                {
                                    "type": "math_env",
                                    "name": "theorem",
                                    "content": [
                                        {"type": "text", "content": "Theorem 1"}
                                    ],
                                    "title": [{"type": "equation", "content": "T=1"}],
                                    "numbering": "1.1",
                                    "numbered": True,
                                },
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
                                        },
                                        {
                                            "type": "math_env",
                                            "name": "theorem",
                                            "content": [
                                                {
                                                    "content": "Theorem 2",
                                                    "type": "text",
                                                },
                                            ],
                                        },
                                    ],
                                },
                            ],
                        },
                        {
                            "type": "section",
                            "title": [{"type": "text", "content": "Last sub section"}],
                            "level": 2,
                            "numbered": True,
                            "numbering": "1.2",
                            "content": [
                                {
                                    "type": "section",
                                    "title": [{"type": "text", "content": "S3"}],
                                    "level": 3,
                                    "numbered": True,
                                    "numbering": "1.2.1",
                                    "content": [],
                                },
                                {
                                    "type": "section",
                                    "title": [{"type": "text", "content": "S4"}],
                                    "level": 3,
                                    "numbered": True,
                                    "numbering": "1.2.2",
                                    "content": [],
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
                                {
                                    "type": "math_env",
                                    "name": "theorem",
                                    "content": [
                                        {"type": "text", "content": "Theorem 3"}
                                    ],
                                    "numbering": "2.1",
                                    "numbered": True,
                                },
                                {
                                    "type": "algorithm",
                                    "name": "algorithm",
                                    "content": [
                                        {
                                            "type": "caption",
                                            "content": [
                                                {
                                                    "type": "text",
                                                    "content": "Binary Search",
                                                }
                                            ],
                                        },
                                    ],
                                    "numbering": "1",
                                    "numbered": True,
                                },
                                {
                                    "type": "tabular",
                                    "environment": "tabular",
                                    "column_spec": "|c|c|",
                                    "content": [
                                        [
                                            "Cell 1",
                                            [
                                                {
                                                    "type": "text",
                                                    "content": "Cell 2",
                                                    "styles": [
                                                        FRONTEND_STYLE_MAPPING["textbf"]
                                                    ],
                                                }
                                            ],
                                            "3",
                                        ],
                                        [
                                            {
                                                "content": "Spanning Cell",
                                                "colspan": 2,
                                                "rowspan": 1,
                                            },
                                            None,
                                        ],
                                        [
                                            None,
                                            "H1 & H2",
                                            None,
                                        ],
                                    ],
                                },
                                {
                                    "type": "list",
                                    "name": "description",
                                    "depth": 1,
                                    "content": [
                                        {
                                            "type": "item",
                                            "title": [
                                                {
                                                    "type": "text",
                                                    "content": "Hello",
                                                    "styles": [
                                                        FRONTEND_STYLE_MAPPING["textbf"]
                                                    ],
                                                }
                                            ],
                                            "content": [
                                                {"type": "text", "content": "World"}
                                            ],
                                        },
                                        {
                                            "type": "item",
                                            "title": [
                                                {"type": "text", "content": "Hello"}
                                            ],
                                            "content": [
                                                {
                                                    "type": "paragraph",
                                                    "level": 1,
                                                    "title": [
                                                        {
                                                            "type": "text",
                                                            "content": "This nested env inside",
                                                        }
                                                    ],
                                                    "content": [
                                                        {
                                                            "type": "list",
                                                            "name": "enumerate",
                                                            "depth": 2,
                                                            "content": [
                                                                {
                                                                    "type": "item",
                                                                    "content": [
                                                                        {
                                                                            "type": "text",
                                                                            "content": "1",
                                                                        }
                                                                    ],
                                                                },
                                                                {
                                                                    "type": "item",
                                                                    "content": [
                                                                        {
                                                                            "type": "text",
                                                                            "content": "2",
                                                                        }
                                                                    ],
                                                                },
                                                            ],
                                                        },
                                                        {
                                                            "type": "text",
                                                            "content": "World",
                                                        },
                                                    ],
                                                },
                                            ],
                                        },
                                    ],
                                },
                            ],
                        },
                    ],
                },
                {
                    "type": "appendix",
                    "content": [
                        {
                            "type": "section",
                            "title": [
                                {"type": "text", "content": "My Appendix Section"}
                            ],
                            "level": 1,
                            "numbering": "A",
                            "numbered": True,
                            "content": [
                                {"type": "text", "content": "Here goes my appendix..."},
                                {
                                    "type": "section",
                                    "title": [
                                        {"type": "text", "content": "Sub appendix 1"}
                                    ],
                                    "level": 2,
                                    "numbering": "A.1",
                                    "numbered": True,
                                    "content": [
                                        {
                                            "type": "text",
                                            "content": "Yea this appendix is nice",
                                        }
                                    ],
                                },
                                {
                                    "type": "section",
                                    "title": [
                                        {"type": "text", "content": "Sub appendix 2"}
                                    ],
                                    "level": 2,
                                    "numbering": "A.2",
                                    "numbered": True,
                                    "content": [],
                                },
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


def strip_content_str(content, omit_fields=[]):
    """Helper function to remove newline characters from the content."""
    if isinstance(content, list):
        return [strip_content_str(item, omit_fields) for item in content]
    elif isinstance(content, dict):
        return {
            k: strip_content_str(v, omit_fields)
            for k, v in content.items()
            if k not in omit_fields
        }
    elif isinstance(content, str):
        return content.replace("\n", "").strip()
    return content


def test_organize_content(latex_parser, latex_text, expected_organizer_output):
    tokens = latex_parser.parse(latex_text)
    token_builder = TokenBuilder()
    organized_tokens = token_builder.organize_content(tokens)

    # Normalize both the organized tokens and expected output
    normalized_organized = strip_content_str(organized_tokens)
    normalized_expected = strip_content_str(expected_organizer_output)

    assert normalized_organized == normalized_expected


def test_equation_placeholders(latex_parser):
    latex_text = r"""
    \begin{equation*}
    \eqref{eq:sum}
    \sum_{i=1}^{n} i = \frac{n(n+1)}{2}
    \includegraphics[width=0.5\textwidth]{example-image}
    \end{equation*}
    """

    expected_eq_output = r"""
    ___PLACEHOLDER_0___
    \sum_{i=1}^{n} i = \frac{n(n+1)}{2}
    ___PLACEHOLDER_1___
    """

    expected = [
        {
            "type": "equation",
            "content": expected_eq_output,
            "display": "block",
            "placeholders": {
                "___PLACEHOLDER_0___": {"type": "ref", "content": "eq:sum"},
                "___PLACEHOLDER_1___": {
                    "type": "includegraphics",
                    "content": "example-image",
                },
            },
        }
    ]
    tokens = latex_parser.parse(latex_text)
    token_builder = TokenBuilder()
    organized_tokens = token_builder.organize_content(tokens)

    normalized_organized = strip_content_str(organized_tokens)
    normalized_expected = strip_content_str(expected)

    assert normalized_organized == normalized_expected


def test_organize_appendix(latex_parser):
    latex_text = r"""
    \section{Intro $1+1$}

    \begin{appendices}
    \section{Appendix}
        Here goes my appendix...
        \subsection{Sub appendix 1}
        \subsection{Sub appendix 2}
        \subsubsection{Sub sub appendix 3}
        \subsubsection*{Sub sub appendix 4}
    \end{appendices}
    """

    expected = [
        {
            "type": "section",
            "title": [
                {"type": "text", "content": "Intro"},
                {"type": "equation", "content": "1+1"},
            ],
            "level": 1,
            "numbering": "1",
            "numbered": True,
            "content": [],
        },
        {
            "type": "appendix",
            "content": [
                {
                    "type": "section",
                    "title": [{"type": "text", "content": "Appendix"}],
                    "level": 1,
                    "numbering": "A",
                    "numbered": True,
                    "content": [
                        {"type": "text", "content": "Here goes my appendix..."},
                        {
                            "type": "section",
                            "title": [{"type": "text", "content": "Sub appendix 1"}],
                            "level": 2,
                            "numbering": "A.1",
                            "numbered": True,
                            "content": [],
                        },
                        {
                            "type": "section",
                            "title": [{"type": "text", "content": "Sub appendix 2"}],
                            "level": 2,
                            "numbering": "A.2",
                            "numbered": True,
                            "content": [
                                {
                                    "type": "section",
                                    "title": [
                                        {
                                            "type": "text",
                                            "content": "Sub sub appendix 3",
                                        }
                                    ],
                                    "level": 3,
                                    "numbering": "A.2.1",
                                    "numbered": True,
                                    "content": [],
                                },
                                {
                                    "type": "section",
                                    "title": [
                                        {
                                            "type": "text",
                                            "content": "Sub sub appendix 4",
                                        }
                                    ],
                                    "level": 3,
                                    "numbered": False,
                                    "content": [],
                                },
                            ],
                        },
                    ],
                }
            ],
        },
    ]

    tokens = latex_parser.parse(latex_text)
    token_builder = TokenBuilder()
    organized_tokens = token_builder.organize_content(tokens)

    normalized_organized = strip_content_str(organized_tokens, omit_fields=["name"])
    normalized_expected = strip_content_str(expected)

    assert normalized_organized == normalized_expected


def test_builder_output_json(latex_parser, latex_text, expected_organizer_output):
    import json
    import warnings

    # Suppress pydanticserialization warnings
    warnings.filterwarnings("ignore")

    tokens = latex_parser.parse(latex_text)
    token_builder = TokenBuilder()

    output = token_builder.build(tokens)

    # test json output
    json_output = [t.model_dump(mode="json", exclude_none=True) for t in output]
    json_output = strip_content_str(json_output)
    normalized_expected = strip_content_str(expected_organizer_output)

    # Recursively remove specified fields from the expected output
    def remove_fields(data, fields_to_remove=["numbered", "column_spec"]):
        if isinstance(data, dict):
            for field in fields_to_remove:
                data.pop(field, None)
            # Special handling for bibliography and document types
            if data.get("type") in ["bibliography", "document"]:
                data.pop("name", None)
                data.pop("args", None)
            elif data.get("type") == "tabular":
                data.pop("environment", None)
            return {k: remove_fields(v, fields_to_remove) for k, v in data.items()}
        elif isinstance(data, list):
            return [remove_fields(item, fields_to_remove) for item in data]
        return data

    normalized_expected = remove_fields(
        normalized_expected, fields_to_remove=["numbered", "column_spec"]
    )

    # use dumps then loads for round trip test
    json_output = json.dumps(json_output)
    json_output = json.loads(json_output)

    assert json_output == normalized_expected
