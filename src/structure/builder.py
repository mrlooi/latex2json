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


# dont add space if any of these
prev_ends_with = tuple(["(", "[", "{", "'", '"'])
next_starts_with = tuple([":", ";", ")", "]", "}", ",", "."])


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
        prev_content.endswith(prev_ends_with)
        or prev_content.endswith(" ")
        or next_content.startswith(next_starts_with)
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
    def manage_stack(token, stack, organized, parent_stack=None):
        """Helper function to manage stack operations for sections and paragraphs"""
        # Clear lower stacks if needed
        while stack and stack[-1]["level"] >= token["level"]:
            stack.pop()

        # Determine where to add the token
        target = (
            parent_stack[-1]["content"]
            if parent_stack
            else (stack[-1]["content"] if stack else organized)
        )
        target.append(token)

        token["content"] = []
        stack.append(token)

    def recursive_organize(tokens):
        organized = []
        section_stack = []
        paragraph_stack = []

        for token in tokens:
            # Recursively organize content if token has nested content
            if isinstance(token, dict) and isinstance(token.get("content"), list):
                token = token.copy()
                token["content"] = recursive_organize(token["content"])

            if isinstance(token, dict):
                if token["type"] == "appendix":
                    section_stack.clear()
                    paragraph_stack.clear()
                    organized.append(token)
                elif token["type"] == "section":
                    paragraph_stack.clear()  # Clear paragraph stack for new section
                    manage_stack(token, section_stack, organized)
                elif token["type"] == "paragraph":
                    manage_stack(token, paragraph_stack, organized, section_stack)
                else:
                    # Add other tokens to the deepest stack
                    target = (
                        paragraph_stack[-1]["content"]
                        if paragraph_stack
                        else (
                            section_stack[-1]["content"] if section_stack else organized
                        )
                    )
                    target.append(token)
            else:
                # Handle non-dict tokens
                target = (
                    paragraph_stack[-1]["content"]
                    if paragraph_stack
                    else (section_stack[-1]["content"] if section_stack else organized)
                )
                target.append(token)

        return organized

    tokens = process_tokens(in_tokens)
    return recursive_organize(tokens)


if __name__ == "__main__":
    from src.tex_parser import LatexParser
    import json

    DEBUG = True

    if not DEBUG:
        with open("papers/arXiv-1706.03762v7/parsed_tokens.json", "r") as f:
            tokens = json.load(f)
    else:
        parser = LatexParser()

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

        \subsection{SubIntro2}
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

        tokens = parser.parse(text)

    organized_tokens = organize_content(tokens)
    # print(organized_tokens)

    token_factory = TokenFactory()

    output = []
    for token in organized_tokens:
        data = token_factory.create(token)
        output.append(data)
