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
    "text": None,
}

TEXT_COMMANDS = "|".join(FRONTEND_STYLE_MAPPING.keys())
TEXT_PATTERN = re.compile(
    rf"\\({TEXT_COMMANDS})" + r"(?![a-zA-Z])(\s*(\{)|.*)?", re.DOTALL
)

PATTERNS = {
    "styled": TEXT_PATTERN,
    "frac": re.compile(
        r"\\(?:frac|nicefrac|textfrac)\s*\{", re.DOTALL
    ),  # Updated to match both sets of braces
}


# Method 2: Using str.lstrip() with len comparison
def find_first_nonspace(s):
    return len(s) - len(s.lstrip())


class TextFormattingHandler(TokenHandler):
    def can_handle(self, content: str) -> bool:
        return any(pattern.match(content) for pattern in PATTERNS.values())

    def _handle_styled(self, content: str, match: re.Match) -> Tuple[str, int]:
        command = match.group(1)
        style = FRONTEND_STYLE_MAPPING.get(command)

        content_to_format = ""
        next_content = match.group(2)
        if next_content:
            if next_content.endswith("{"):
                next_pos = match.end(2)
                text, end_pos = extract_nested_content("{" + content[next_pos:])
                if text is None:
                    # should not happen if there is proper closing brace
                    content_to_format = "{"
                    total_pos = next_pos
                elif text.strip() == "":
                    # ignore empty \text{} i.e. return None since there's nothing to format
                    return None, next_pos + end_pos - 1
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

        if style is None:
            return {"type": "text", "content": content_to_format}, total_pos

        return {
            "type": "styled",
            "style": style,
            "content": content_to_format,
        }, total_pos

    def _handle_frac(self, content: str, match: re.Match) -> Tuple[str, int]:
        first_brace_start = match.end(0) - 1
        first, first_brace_end = extract_nested_content(content[first_brace_start:])
        first_brace_end = first_brace_start + first_brace_end
        if not first:
            return None, 0
        has_second_brace = content[first_brace_end:].strip()[0] == "{"
        if not has_second_brace:
            return None, 0
        second_brace_start = first_brace_end + content[first_brace_end:].find("{")
        second, second_brace_end = extract_nested_content(content[second_brace_start:])
        if not second:
            return None, 0

        end_pos = second_brace_start + second_brace_end

        # Replace newlines and collapse multiple spaces into single spaces
        first = " ".join(first.replace("\n", " ").split()).strip()
        second = " ".join(second.replace("\n", " ").split()).strip()

        return {
            "type": "text",
            "content": "%s / %s" % (first, second),
        }, end_pos

    def handle(self, content: str) -> Tuple[str, int]:
        for name, pattern in PATTERNS.items():
            match = pattern.match(content)
            if not match:
                continue
            if name == "styled":
                return self._handle_styled(content, match)
            elif name == "frac":
                return self._handle_frac(content, match)

        return None, 0

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

            # remove duplicates via dict
            processed_token["styles"] = list(
                OrderedDict.fromkeys(current_styles)
            )  # Pre-3.7 compatible

            # Recursively process content if it's a list
            if "content" in processed_token and isinstance(
                processed_token["content"], list
            ):
                processed_content = TextFormattingHandler.process_style_in_tokens(
                    processed_token["content"], processed_token["styles"]
                )

                # If this is a styled token, flatten it by extending new_tokens with processed_content
                if processed_token.get("type") in ["styled", "text"]:
                    new_tokens.extend(processed_content)
                    continue

                processed_token["content"] = processed_content

            if len(processed_token["styles"]) == 0:
                del processed_token["styles"]
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

    text = r"""
    \nicefrac{
        FIRST    
        BLOCK
    } {
        SECOND
        BLOCK
    }
    after frac
""".strip()
    print(handler.handle(text))

    # tokens = [
    #     {
    #         "type": "styled",
    #         "style": "normal",
    #         "content": [
    #             {"type": "text", "content": "sss\n    "},
    #             {
    #                 "type": "styled",
    #                 "style": "bold",
    #                 "content": [{"type": "text", "content": "Hii"}],
    #             },
    #             {"type": "text", "content": "bro"},
    #         ],
    #     }
    # ]

    # out = TextFormattingHandler.process_style_in_tokens(tokens)
    # print(out)
