from src.structure.token_factory import TokenFactory
from src.structure.tokens.types import TokenType


import copy


def convert_inline_equations_to_text(tokens):
    converted_tokens = []
    for token in tokens:
        if (
            isinstance(token, dict)
            and token.get("type") == "equation"
            and token.get("display") == "inline"
        ):
            # Convert inline equation to text token
            token_copy = {
                "type": "text",
                "content": f"${token['content']}$",
            }
            if token.get("styles"):
                token_copy["styles"] = token.get("styles")
            converted_tokens.append(token_copy)
        else:
            converted_tokens.append(token)
    return converted_tokens


def concat_text_with_same_styles(tokens):
    concatenated_tokens = []
    current_text = None

    for token in tokens:
        if isinstance(token, dict) and token.get("type") == "text":
            if current_text is None:
                current_text = token
            elif current_text.get("styles") == token.get("styles"):
                # Add space only if both sides don't already have it
                if not (
                    current_text["content"].endswith(" ")
                    or token["content"].startswith(" ")
                ):
                    current_text["content"] += " " + token["content"]
                else:
                    current_text["content"] += token["content"]
            else:
                concatenated_tokens.append(current_text)
                current_text = token
        else:
            if current_text is not None:
                concatenated_tokens.append(current_text)
                current_text = None
            concatenated_tokens.append(token)

    if current_text is not None:
        concatenated_tokens.append(current_text)

    return concatenated_tokens


def process_tokens(in_tokens):
    def recursive_process(tokens, should_concat=True):
        processed_tokens = []
        for token in tokens:
            if isinstance(token, dict):
                if token.get("type") == "tabular":
                    # Process table rows but don't concatenate their cells
                    token["content"] = [
                        recursive_process(row, should_concat=False)
                        for row in token["content"]
                    ]
                    processed_tokens.append(token)
                elif isinstance(token.get("content"), list):
                    token["content"] = recursive_process(token["content"])
                    processed_tokens.append(token)
                else:
                    processed_tokens.append(token)
            elif isinstance(token, list):
                token = recursive_process(token)
                processed_tokens.append(token)
            else:
                processed_tokens.append(token)

        processed_tokens = convert_inline_equations_to_text(processed_tokens)
        if should_concat:
            processed_tokens = concat_text_with_same_styles(processed_tokens)
        return processed_tokens

    return recursive_process(copy.deepcopy(in_tokens))


def organize_content(in_tokens):
    # First merge inline equations with text
    tokens = process_tokens(in_tokens)

    # Then organize sections as before
    organized_tokens = []
    section_stack = []

    for token in tokens:
        if token["type"] == "section":
            while section_stack and section_stack[-1]["level"] >= token["level"]:
                section_stack.pop()

            if section_stack:
                section_stack[-1]["content"].append(token)
            else:
                organized_tokens.append(token)

            token["content"] = []
            section_stack.append(token)
        else:
            if section_stack:
                section_stack[-1]["content"].append(token)
            else:
                # Add tokens directly to organized_tokens if no sections exist
                organized_tokens.append(token)

    return organized_tokens


if __name__ == "__main__":
    from src.tex_parser import LatexParser
    import json

    # with open("papers/arXiv-1706.03762v7/parsed_tokens.json", "r") as f:
    #     tokens = json.load(f)

    parser = LatexParser()

    text = r"""
    \section{Intro} \label{sec:intro}

    Some text here, $1+1=2$:
    \begin{equation}
        E = mc^2
    \end{equation}

    \subsection{SubIntro}
    My name is \textbf{John Doe} \textbf{Sss} ahama

    \begin{table}
        \begin{tabular}{c|c}
            $E = mc^2$  & HELLO $E = mc^2$ \\
            c & d \\
            \begin{tabular}{c|c}
                SUB 1 & SUB 2 $F=ma$
            \end{tabular} & OUTEND
        \end{tabular}
    \end{table}

    \subsection{SubIntro2}
    SUBINTRO 2

    \section{Conclusion}
    This is ma conclusion
    """

    tokens = parser.parse(text)
    organized_tokens = organize_content(tokens)
    # print(organized_tokens)

    token_factory = TokenFactory()

    output = []
    for token in organized_tokens:
        data = token_factory.create(token)
        output.append(data)
