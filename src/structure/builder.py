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


no_space_after = tuple([",", ".", ":", ";", ")", "]", "}", "'", '"'])
no_space_before = tuple(["(", "[", "{", "'", '"', ",", "."])


def should_add_space(prev_content: str, next_content: str) -> bool:
    """
    Determine if a space should be added between two text contents.

    Args:
        prev_content: The preceding text content
        next_content: The following text content

    Returns:
        bool: True if space should be added, False otherwise
    """

    return not (
        prev_content.endswith(no_space_after)
        or prev_content.endswith(" ")
        or next_content.startswith(no_space_before)
        or next_content.startswith(" ")
    )


def concat_text_with_same_styles(tokens):
    concatenated_tokens = []
    current_text = None

    for token in tokens:
        if isinstance(token, dict) and token.get("type") == "text":
            if current_text is None:
                current_text = token
            elif current_text.get("styles") == token.get("styles"):
                prev_content = current_text["content"]
                next_content = token["content"]

                current_text["content"] += (
                    " " + next_content
                    if should_add_space(prev_content, next_content)
                    else next_content
                )
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
    def recursive_organize(tokens):
        organized = []
        section_stack = []

        for token in tokens:
            # Recursively organize content if token has nested content
            if isinstance(token, dict) and isinstance(token.get("content"), list):
                token = token.copy()  # Create a copy to avoid modifying original
                token["content"] = recursive_organize(token["content"])

            if isinstance(token, dict):
                if token["type"] == "appendix":
                    section_stack.clear()
                    organized.append(token)
                elif token["type"] == "section":
                    while (
                        section_stack and section_stack[-1]["level"] >= token["level"]
                    ):
                        section_stack.pop()

                    if section_stack:
                        section_stack[-1]["content"].append(token)
                    else:
                        organized.append(token)

                    token["content"] = []
                    section_stack.append(token)
                else:
                    if section_stack:
                        section_stack[-1]["content"].append(token)
                    else:
                        organized.append(token)
            else:
                if section_stack:
                    section_stack[-1]["content"].append(token)
                else:
                    organized.append(token)

        return organized

    # First merge inline equations with text
    tokens = process_tokens(in_tokens)

    # Then organize sections recursively
    return recursive_organize(tokens)


if __name__ == "__main__":
    from src.tex_parser import LatexParser
    import json

    with open("papers/arXiv-1706.03762v7/parsed_tokens.json", "r") as f:
        tokens = json.load(f)

    # parser = LatexParser()

    # text = r"""
    # \title{My Title}

    # \begin{document}

    # \abstract{This is my abstract}

    # \section{Intro} \label{sec:intro}

    # Some text here, $1+1=2$:
    # \begin{equation}
    #     E = mc^2
    # \end{equation}

    # \subsection{SubIntro}
    # My name is \textbf{John Doe} \textbf{Sss} ahama

    # \subsection{SubIntro2}
    # SUBINTRO 2

    # \section{Conclusion}
    # TLDR: Best paper

    # \subsection{mini conclusion}
    # Mini conclude

    # \appendix

    # \section{Appendix}
    # My appendix

    # \end{document}
    # """

    # tokens = parser.parse(text)

    organized_tokens = organize_content(tokens)
    # print(organized_tokens)

    token_factory = TokenFactory()

    output = []
    for token in organized_tokens:
        data = token_factory.create(token)
        output.append(data)
