from collections import OrderedDict
from typing import Callable, Dict, List, Optional, Tuple

import re

from src.handlers.base import TokenHandler
from src.tex_utils import extract_nested_content, flatten, strip_latex_newlines


# Add this new mapping for frontend styles
FRONTEND_STYLE_MAPPING: Dict[str, str] = {
    "textbf": "bold",
    "textit": "italic",
    "textsl": "italic",  # slanted is typically rendered as italic
    "textsc": "small-caps",
    "textsf": "sans-serif",
    "texttt": "monospace",
    "textrm": "normal",
    "textup": "normal",
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
    "frac": re.compile(r"\\(?:frac|nicefrac|textfrac)\s*\{", re.DOTALL),  # \frac{}{}
    "texorpdfstring": re.compile(
        r"\\texorpdfstring\s*\{", re.DOTALL
    ),  # \texorpdfstring{pdf version}{text version}
}


# Method 2: Using str.lstrip() with len comparison
def find_first_nonspace(s):
    return len(s) - len(s.lstrip())


def parse_dual_braces_content(content: str, first_brace_start: int) -> Tuple[str, int]:
    first, first_brace_end = extract_nested_content(content[first_brace_start:])
    if not first:
        return None, 0
    first_brace_end = first_brace_start + first_brace_end
    has_second_brace = content[first_brace_end:].strip()[0] == "{"
    if not has_second_brace:
        return None, 0
    second_brace_start = first_brace_end + content[first_brace_end:].find("{")
    second, second_brace_end = extract_nested_content(content[second_brace_start:])
    if not second:
        return None, 0

    end_pos = second_brace_start + second_brace_end
    return first, second, end_pos


def flatten_all_to_string(tokens: List[Dict | str | List]) -> str:
    def flatten_token(token):
        if isinstance(token, str):
            return token
        elif isinstance(token, list):
            return flatten_all_to_string(token)
        elif isinstance(token, dict) and isinstance(token.get("content"), list):
            return flatten_all_to_string(token["content"])
        else:
            return token["content"]

    return " ".join(flatten_token(token) for token in tokens)


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

        token = {"type": "text", "content": content_to_format}
        if style is not None:
            token["styles"] = [style]

        if self.process_content_fn:
            inner_content = self.process_content_fn(content_to_format)

            # if inner content is just a single token, we can merge styles and flatten this token
            if len(inner_content) == 1 and isinstance(inner_content[0], dict):
                new_token = inner_content[0]
                new_token_styles = new_token.get("styles", [])
                if "styles" in token:
                    # Prepend parent styles before child styles
                    new_token_styles = token["styles"] + new_token_styles
                # remove duplicates
                new_token["styles"] = list(OrderedDict.fromkeys(new_token_styles))
                return new_token, total_pos
            else:
                # if "styles" in token:
                token["type"] = "styled"
                token["content"] = inner_content

        return token, total_pos

    def _handle_frac(self, content: str, match: re.Match) -> Tuple[str, int]:
        out = parse_dual_braces_content(content, match.end(0) - 1)
        if out[0] is None:
            return None, 0

        first, second, end_pos = out

        if self.process_content_fn:
            first = flatten_all_to_string(self.process_content_fn(first))
            second = flatten_all_to_string(self.process_content_fn(second))

        # Replace newlines and collapse multiple spaces into single spaces
        first = strip_latex_newlines(first)
        second = strip_latex_newlines(second)

        return {
            "type": "text",
            "content": "%s / %s" % (first, second),
        }, end_pos

    def _handle_texorpdfstring(self, content: str, match: re.Match) -> Tuple[str, int]:
        out = parse_dual_braces_content(content, match.end(0) - 1)
        if out[0] is None:
            return None, 0
        first, second, end_pos = out

        # choose 2nd one in texorpdfstring
        if self.process_content_fn:
            return {
                "type": "layout",
                "content": self.process_content_fn(second),
            }, end_pos
        return {
            "type": "text",
            "content": second,
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
            elif name == "texorpdfstring":
                return self._handle_texorpdfstring(content, match)

        return None, 0


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
