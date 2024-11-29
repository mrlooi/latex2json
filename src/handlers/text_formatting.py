from collections import OrderedDict
from typing import Callable, Dict, List, Optional, Tuple

import re

from src.handlers.base import TokenHandler
from src.tex_utils import extract_nested_content


# Add this new mapping for frontend styles
FRONTEND_STYLE_MAPPING: Dict[str, str] = {
    "textbf": "bold",
    "textit": "italic",
    "textsl": "italic",  # slanted is typically rendered as italic
    "textsc": "small-caps",
    "textsf": "sans-serif",
    "texttt": "monospace",
    "textrm": "normal",
    "emph": "italic",
    # Size mappings
    "texttiny": "xx-small",
    "textscriptsize": "x-small",
    "textfootnotesize": "small",
    "textsmall": "small",
    "textnormal": "medium",
    "textlarge": "large",
    "texthuge": "xx-large",
}

TEXT_COMMANDS = "|".join(FRONTEND_STYLE_MAPPING.keys())
TEXT_PATTERN = re.compile(
    rf"\\({TEXT_COMMANDS})" + r"(?![a-zA-Z])(\s*(\{)|.*)?", re.DOTALL
)


# Method 2: Using str.lstrip() with len comparison
def find_first_nonspace(s):
    return len(s) - len(s.lstrip())


class TextFormattingHandler(TokenHandler):
    def can_handle(self, content: str) -> bool:
        return TEXT_PATTERN.match(content) is not None

    def handle(self, content: str) -> Tuple[str, int]:
        match = TEXT_PATTERN.match(content)
        if not match:
            return None, 0

        command = match.group(1)
        style = FRONTEND_STYLE_MAPPING.get(command, command)

        content_to_format = ""
        next_content = match.group(2)
        if next_content:
            if next_content.endswith("{"):
                next_pos = match.end(2)
                text, end_pos = extract_nested_content("{" + content[next_pos:])
                if not text:
                    # should not happen if there is proper closing brace
                    content_to_format = "{"
                    total_pos = next_pos
                else:
                    content_to_format = text
                    total_pos = next_pos + end_pos - 1
            else:
                # get first character that is not space
                index = find_first_nonspace(next_content)
                content_to_format = next_content[index]
                if content_to_format == "\\":
                    # if command, no content
                    content_to_format = ""
                    total_pos = match.start(2)
                else:
                    total_pos = match.start(2) + index + 1
        else:
            total_pos = match.end(0)

        if self.process_content_fn:
            content_to_format = self.process_content_fn(content_to_format)

        return {
            "type": "styled",
            "style": style,
            "content": content_to_format,
        }, total_pos

    @staticmethod
    def process_style_in_tokens(tokens: List[Dict], parent_styles: List[str] = []):
        new_tokens = []
        for i, token in enumerate(tokens):
            if isinstance(token, str):
                new_tokens.append(token)
                continue

            # Create a copy of the token to modify
            processed_token = token.copy()

            # Handle style inheritance
            current_styles = parent_styles.copy()
            if "style" in token:
                current_styles.append(token["style"])
            elif "styles" in token:
                current_styles.extend(token["styles"])
            processed_token["styles"] = current_styles

            # Recursively process content if it's a list
            if "content" in processed_token and isinstance(
                processed_token["content"], list
            ):
                processed_content = TextFormattingHandler.process_style_in_tokens(
                    processed_token["content"], processed_token["styles"]
                )

                # If this is a styled token, flatten it by extending new_tokens with processed_content
                if processed_token.get("type") == "styled":
                    new_tokens.extend(processed_content)
                    continue

                processed_token["content"] = processed_content

            new_tokens.append(processed_token)

        return new_tokens


if __name__ == "__main__":
    handler = TextFormattingHandler()

    # def check(text):
    #     out, end_pos = handler.handle(text)
    #     print(text, "->", out)
    #     print("rem", text[end_pos:])
    #     print()

    # text_blocks = [
    #     r"\textbf \textsc sss",
    # ]
    # for text in text_blocks:
    #     check(text)

    tokens = [
        {
            "type": "styled",
            "style": "normal",
            "content": [
                {"type": "text", "content": "sss\n    "},
                {
                    "type": "styled",
                    "style": "bold",
                    "content": [{"type": "text", "content": "Hii"}],
                },
                {"type": "text", "content": "bro"},
            ],
        }
    ]

    out = TextFormattingHandler.process_style_in_tokens(tokens)
    print(out)
