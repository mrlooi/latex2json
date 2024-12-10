from src.structure.token_factory import TokenFactory
from src.structure.tokens.types import TokenType


if __name__ == "__main__":
    from src.tex_parser import LatexParser
    import json

    # with open("papers/arXiv-1706.03762v7/parsed_tokens.json", "r") as f:
    #     tokens = json.load(f)

    parser = LatexParser()

    text = r"""
    % nested nested nested
    \begin{itemize}
        \item \begin{itemize}
            \item nested2
            \item $E = mc^2$ \label{eq:1}
        \end{itemize}
        \item nested
    \end{itemize}
    """
    tokens = parser.parse(text)

    token_factory = TokenFactory()

    output = []
    for token in tokens:
        data = token_factory.create(token)
        output.append(data)
