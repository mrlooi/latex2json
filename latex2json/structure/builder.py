import logging
from typing import Dict, List
from latex2json.structure.token_factory import TokenFactory
from latex2json.structure.tokens.base import BaseToken
from latex2json.structure.tokens.types import TokenType


import copy


MATH_OPEN_DELIMITER = "<math>"
MATH_CLOSE_DELIMITER = "</math>"


class TokenBuilder:
    """Handles the building and organization of document tokens including numbering and hierarchy.

    Responsible for:
    - Managing section, equation, table, and figure numbering
    - Processing and organizing document structure
    - Converting and concatenating tokens
    """

    # Constants
    _PREV_ENDS_WITH = ("(", "[", "{", "'", '"')
    _NEXT_STARTS_WITH = (":", ";", ")", "]", "}", ",", ".")

    def __init__(self, logger: logging.Logger = None):
        self.logger = logger or logging.getLogger(__name__)

        self.token_factory = TokenFactory()
        self.clear()

    def reset_numbering(self):
        """Reset section numbering state"""
        self.section_numbers = {1: 0, 2: 0, 3: 0}
        self.math_env_number = 0  # resets when section changes
        # equation, table, figure are simple sequential counters
        self.equation_number = 0
        self.table_env_number = 0
        self.figure_env_number = 0

    def clear(self):
        self.reset_numbering()

    @staticmethod
    def _should_add_space(prev_content: str, next_content: str) -> bool:
        return not (
            prev_content.endswith(TokenBuilder._PREV_ENDS_WITH)
            or prev_content.endswith(" ")
            or next_content.startswith(TokenBuilder._NEXT_STARTS_WITH)
            or next_content.startswith(" ")
        )

    def _update_section_numbering(
        self, token, reset_lower_levels=False, in_appendix=False
    ):
        """Handle section numbering logic in a centralized way"""
        if not token.get("numbered", True):
            return

        level = token.get("level", 1)

        # Reset lower level counters if needed
        if reset_lower_levels:
            for l in range(level + 1, max(self.section_numbers.keys()) + 1):
                self.section_numbers[l] = 0

        # Increment current level counter
        self.section_numbers[level] += 1

        # Build section number string
        # First number is a letter if in appendix i.e. 1->A, 2->B, etc.
        first_num = (
            chr(64 + self.section_numbers[1])
            if in_appendix
            else str(self.section_numbers[1])
        )
        number_parts = [first_num] + [
            str(self.section_numbers[l]) for l in range(2, level + 1)
        ]
        token["numbering"] = ".".join(number_parts)

    def _update_equation_numbering(self, token):
        self.equation_number += 1
        token["numbering"] = str(self.equation_number)

    def _update_table_env_numbering(self, token):
        self.table_env_number += 1
        token["numbering"] = str(self.table_env_number)

    def _update_figure_env_numbering(self, token):
        self.figure_env_number += 1
        token["numbering"] = str(self.figure_env_number)

    def _update_math_env_numbering(self, token):
        self.math_env_number += 1
        # Use current section number + sequential counter
        section_prefix = str(self.section_numbers[1])
        token["numbering"] = f"{section_prefix}.{self.math_env_number}"

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
                    "content": f"{MATH_OPEN_DELIMITER}{token['content']}{MATH_CLOSE_DELIMITER}",
                }
                if token.get("styles"):
                    token_copy["styles"] = token.get("styles")
                converted_tokens.append(token_copy)
            else:
                converted_tokens.append(token)
        return converted_tokens

    def _concat_text_with_same_styles(self, tokens):
        concatenated_tokens = []
        current_text_token = None

        for token in tokens:
            if isinstance(token, dict) and token.get("type") == "text":
                if current_text_token is None:
                    current_text_token = token
                else:
                    prev_content = current_text_token["content"]
                    next_content = token["content"]
                    # merge text tokens with same style
                    if current_text_token.get("styles") == token.get("styles"):
                        add_space = self._should_add_space(prev_content, next_content)
                        current_text_token["content"] += (
                            " " + next_content if add_space else next_content
                        )
                    else:
                        concatenated_tokens.append(current_text_token)
                        current_text_token = token
            else:
                if current_text_token is not None:
                    concatenated_tokens.append(current_text_token)
                    current_text_token = None
                concatenated_tokens.append(token)

        if current_text_token is not None:
            concatenated_tokens.append(current_text_token)

        return concatenated_tokens

    def _process_tokens(self, in_tokens: List[Dict]) -> List[Dict]:
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

    def _check_update_numbering(self, token: Dict[str, any]):
        if token.get("numbered"):
            if token["type"] == "equation":
                self._update_equation_numbering(token)
            elif token["type"] == "math_env":
                self._update_math_env_numbering(token)
            elif token["type"] == "table":
                self._update_table_env_numbering(token)
            elif token["type"] == "figure":
                self._update_figure_env_numbering(token)

    def _recursive_organize(self, tokens, in_appendix=False):
        organized = []
        section_stack = []
        paragraph_stack = []
        root = organized  # Default root for content

        def get_current_target():
            if paragraph_stack:
                return paragraph_stack[-1]["content"]
            if section_stack:
                return section_stack[-1]["content"]
            return root

        for token in tokens:
            if not isinstance(token, dict):
                get_current_target().append(token)
                continue

            # Handle appendix declaration
            # if \begin{appendices}, then content is the content inside the appendices env
            if token["type"] == "appendix":
                in_appendix = True
                if not token.get("content"):
                    token["content"] = []
                else:
                    token["content"] = self._recursive_organize(token["content"], True)
                root = token["content"]  # Switch root to appendix content
                section_stack.clear()
                paragraph_stack.clear()
                organized.append(token)
                # reset section numbers since appendix
                self.section_numbers = {1: 0, 2: 0, 3: 0}
                continue

            # Handle token numbering
            self._check_update_numbering(token)

            # Recursively process nested content
            if isinstance(token.get("content"), list):
                token["content"] = self._recursive_organize(
                    token["content"], in_appendix
                )

            # Handle special token types
            if token["type"] == "bibliography":
                section_stack.clear()
                paragraph_stack.clear()
                organized.append(token)
            elif token["type"] == "section":
                paragraph_stack.clear()
                self._update_section_numbering(
                    token, reset_lower_levels=True, in_appendix=in_appendix
                )
                # Reset math environment counter when section changes
                if token.get("level") == 1:
                    self.math_env_number = 0

                self._manage_stack(token, section_stack, root)
            elif token["type"] == "paragraph":
                self._manage_stack(token, paragraph_stack, root, section_stack)
            else:
                get_current_target().append(token)

        return organized

    def organize_content(self, in_tokens: List[Dict]) -> List[Dict]:
        """
        Main public method to organize and process tokens.

        Args:
            in_tokens: Input tokens to process and organize

        Returns:
            List of organized and processed tokens
        """
        self.clear()  # Reset numbering at the start of each document
        tokens = self._process_tokens(in_tokens)
        return self._recursive_organize(tokens)

    def build(self, tokens) -> List[BaseToken]:
        """
        Build the final output from organized tokens.

        Args:
            tokens: Organized tokens to process

        Returns:
            List of processed tokens
        """
        self.logger.debug("Starting token building...")
        # self.logger.debug("Starting token content organization...")
        organized_tokens = self.organize_content(tokens)
        # self.logger.debug("Token content organization complete")
        output = []
        for token in organized_tokens:
            data = self.token_factory.create(token)
            if data:
                output.append(data)
        self.logger.info("Token building complete. %d tokens created" % (len(output)))
        return output


if __name__ == "__main__":
    from latex2json.parser.tex_parser import LatexParser
    from latex2json.utils.logger import setup_logger

    logger = setup_logger(__name__, level=logging.DEBUG, log_file="logs/builder.log")
    logging.getLogger("asyncio").setLevel(logging.WARNING)

    parser = LatexParser(logger)
    token_builder = TokenBuilder(logger=logger)

    # file = "papers/new/arXiv-2005.14165v4/main.tex"
    # tokens = parser.parse_file(file)

    text = r"""
    Hello there $1+1=2$, I have \$3 mr krabs
    """
    tokens = parser.parse(text)

    output = token_builder.build(tokens)
    print(output)
