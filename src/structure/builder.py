from src.structure.token_factory import TokenFactory
from src.structure.tokens.types import TokenType


import copy


class TokenBuilder:
    # Constants
    _PREV_ENDS_WITH = ("(", "[", "{", "'", '"')
    _NEXT_STARTS_WITH = (":", ";", ")", "]", "}", ",", ".")

    def __init__(self):
        self.token_factory = TokenFactory()
        self.reset_numbering()

    def reset_numbering(self):
        """Reset section numbering state"""
        self.section_numbers = {1: 0, 2: 0, 3: 0}
        self.equation_number = 0  # Add equation counter

    @staticmethod
    def _should_add_space(prev_content: str, next_content: str) -> bool:
        return not (
            prev_content.endswith(TokenBuilder._PREV_ENDS_WITH)
            or prev_content.endswith(" ")
            or next_content.startswith(TokenBuilder._NEXT_STARTS_WITH)
            or next_content.startswith(" ")
        )

    def _update_section_numbering(self, token, reset_lower_levels=False):
        """Handle section numbering logic in a centralized way"""
        if not token.get("numbered", True):
            return

        level = token.get("level", 1)

        # Reset lower level counters if needed
        if reset_lower_levels:
            for l in range(2, max(self.section_numbers.keys()) + 1):
                self.section_numbers[l] = 0

        # Increment current level counter
        self.section_numbers[level] += 1

        # Build section number string
        number_parts = [str(self.section_numbers[l]) for l in range(1, level + 1)]
        token["numbering"] = ".".join(number_parts)

    def _update_equation_numbering(self, token):
        """Handle equation numbering logic"""
        if not token.get("numbered", True):
            return

        self.equation_number += 1
        token["numbering"] = str(self.equation_number)

    def _convert_inline_equations_to_text(self, tokens):
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

    def _concat_text_with_same_styles(self, tokens):
        concatenated_tokens = []
        current_text = None

        for token in tokens:
            if isinstance(token, dict) and token.get("type") == "text":
                if current_text is None:
                    current_text = token
                else:
                    prev_content = current_text["content"]
                    next_content = token["content"]
                    add_space = self._should_add_space(prev_content, next_content)
                    # merge text tokens with same style
                    if current_text.get("styles") == token.get("styles"):

                        current_text["content"] += (
                            " " + next_content if add_space else next_content
                        )
                    else:
                        concatenated_tokens.append(current_text)
                        current_text = token
                        if add_space:
                            token["content"] = " " + token["content"]
            else:
                if current_text is not None:
                    concatenated_tokens.append(current_text)
                    current_text = None
                concatenated_tokens.append(token)

        if current_text is not None:
            concatenated_tokens.append(current_text)

        return concatenated_tokens

    def _process_tokens(self, in_tokens):
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

            processed_tokens = self._convert_inline_equations_to_text(processed_tokens)
            if should_concat:
                processed_tokens = self._concat_text_with_same_styles(processed_tokens)
            return processed_tokens

        return recursive_process(copy.deepcopy(in_tokens))

    def _manage_stack(self, token, stack, organized, parent_stack=None):
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

    def _recursive_organize(self, tokens):
        organized = []
        section_stack = []
        paragraph_stack = []

        for token in tokens:
            if isinstance(token, dict) and isinstance(token.get("content"), list):
                token = token.copy()
                token["content"] = self._recursive_organize(token["content"])

            if isinstance(token, dict):
                if token["type"] == "equation" and token.get("numbered"):
                    self._update_equation_numbering(token)

                if token["type"] == "appendix" or token["type"] == "bibliography":
                    section_stack.clear()
                    paragraph_stack.clear()
                    organized.append(token)
                elif token["type"] == "section":
                    paragraph_stack.clear()
                    self._update_section_numbering(token, reset_lower_levels=True)
                    self._manage_stack(token, section_stack, organized)
                elif token["type"] == "paragraph":
                    self._manage_stack(token, paragraph_stack, organized, section_stack)
                else:
                    target = (
                        paragraph_stack[-1]["content"]
                        if paragraph_stack
                        else (
                            section_stack[-1]["content"] if section_stack else organized
                        )
                    )
                    target.append(token)
            else:
                target = (
                    paragraph_stack[-1]["content"]
                    if paragraph_stack
                    else (section_stack[-1]["content"] if section_stack else organized)
                )
                target.append(token)

        return organized

    def organize_content(self, in_tokens):
        """
        Main public method to organize and process tokens.

        Args:
            in_tokens: Input tokens to process and organize

        Returns:
            List of organized and processed tokens
        """
        self.reset_numbering()  # Reset numbering at the start of each document
        tokens = self._process_tokens(in_tokens)
        return self._recursive_organize(tokens)

    def build(self, tokens):
        """
        Build the final output from organized tokens.

        Args:
            tokens: Organized tokens to process

        Returns:
            List of processed tokens
        """
        organized_tokens = self.organize_content(tokens)
        output = []
        for token in organized_tokens:
            data = self.token_factory.create(token)
            if data:
                output.append(data)
        return output


if __name__ == "__main__":
    from src.parser.tex_parser import LatexParser
    import json

    DEBUG = False

    parser = LatexParser()

    # text = r"""
    # \begin{thebibliography}{99}
    # \bibitem[Title]{key} Some content \tt cool
    # \end{thebibliography}
    # """
    # tokens = parser.parse(text)

    file = "papers/new/arXiv-2010.11929v2/main.tex"
    tokens = parser.parse_file(file)

    token_builder = TokenBuilder()

    # organized_tokens = token_builder.organize_content(tokens)

    output = token_builder.build(tokens)
