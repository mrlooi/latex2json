from collections import OrderedDict
from typing import Callable, Dict, List, Optional, Tuple

import re

from latex2json.parser.handlers.base import TokenHandler
from latex2json.parser.patterns import BRACE_CONTENT_PATTERN, OPTIONAL_BRACE_PATTERN
from latex2json.utils.tex_utils import (
    extract_nested_content,
    extract_nested_content_sequence_blocks,
    flatten_all_to_string,
    flatten_group_token,
    strip_latex_newlines,
)


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
    "textsuperscript": "superscript",
    "textsubscript": "subscript",
    "underline": "underline",
    "textstrikeout": "line-through",  # requires ulem package in LaTeX
    "sout": "line-through",  # another strikethrough command
    "textoverline": "overline",
    "natexlab": None,
}

TEXT_COMMANDS = "|".join(FRONTEND_STYLE_MAPPING.keys())
TEXT_PATTERN = re.compile(
    rf"\\({TEXT_COMMANDS})" + r"(?![a-zA-Z])(\s*(\{)|.*)?", re.DOTALL
)

BOX_PATTERN = re.compile(
    r"""
    \\(?:
        [fhv]box\s*{| # \fbox{text} hbox vbox 
        parbox(?:\s*\[[^\]]*\])*\s*{[^}]*}\s*{| # \parbox[pos][height][inner-pos]{width}{text}
        makebox(?:\s*\[[^\]]*\])*\s*{| # \makebox[width][pos]
        framebox(?:\s*\[[^\]]*\])*\s*{| # \framebox[width][pos]
        raisebox\s*{[^}]+}(?:\s*\[[^\]]*\])*\s*{| # \raisebox{raise}[height][depth]
        colorbox\s*{[^}]*}\s*{|           # \colorbox{color}{text}
        fcolorbox\s*{[^}]*}\s*{[^}]*}\s*{|   # \fcolorbox{border}{bg}{text}
        scalebox\s*{[^}]*}\s*{|  # \scalebox{scale}{text}
        mbox\s*{| # \mbox{text}
        hbox\s+to\s*[^{]+\s*{| # \hbox to \hsize{text}
        sbox\b\s*[^{]+\s*{| # \sbox\@tempboxa{text}
        pbox\b\s*{[^}]*}\s*{| # \pbox{x}{text}
        resizebox\s*{[^}]*}\s*{[^}]*}\s*{|  # \resizebox{width}{height}{text}
        adjustbox\s*{   # \adjustbox{max width=\textwidth}{...}
    )
    """,
    re.VERBOSE | re.DOTALL,
)

PATTERNS = {
    "styled": TEXT_PATTERN,
    "frac": re.compile(r"\\(?:frac|nicefrac|textfrac)\s*\{", re.DOTALL),  # \frac{}{}
    "texorpdfstring": re.compile(
        r"\\texorpdfstring\s*\{", re.DOTALL
    ),  # \texorpdfstring{pdf version}{text version}
    "box": BOX_PATTERN,
    # custom fonts (that we want to ignore)
    "fontsize": re.compile(r"\\fontsize" + (r"\s*" + BRACE_CONTENT_PATTERN) * 2),
    "selectfont": re.compile(r"\\selectfont\b"),
    "usefont": re.compile(r"\\usefont" + (r"\s*" + BRACE_CONTENT_PATTERN) * 4),
    "color": re.compile(r"\\textcolor\s*(\[\w+\])?\s*{"),
    "columns": re.compile(r"\\(?:onecolumn\b|twocolumn\s*\[?)"),
    "subfloat": re.compile(r"\\subfloat\s*\["),
    "fancyhead": re.compile(
        r"\\(?:fancyhead|rhead|chead|lhead)\s*%s\s*{" % OPTIONAL_BRACE_PATTERN,
        re.DOTALL,
    ),
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


def is_text_token(token: Dict) -> bool:
    return isinstance(token, dict) and token.get("type") == "text"


def normalize_text_token(token: str | Dict | List) -> Dict:
    if isinstance(token, str):
        return {"type": "text", "content": token}
    elif is_text_token(token):
        return token
    elif isinstance(token, list):
        if len(token) == 1 and is_text_token(token[0]):
            return token[0]
        return {"type": "group", "content": token}
    return token


class TextFormattingHandler(TokenHandler):
    def can_handle(self, content: str) -> bool:
        return any(pattern.match(content) for pattern in PATTERNS.values())

    def _process_content(self, content: str):
        if self.process_content_fn:
            out = self.process_content_fn(content)
            return normalize_text_token(out)
        return normalize_text_token(content)

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
                token["content"] = inner_content
                if isinstance(inner_content, str):
                    return token, total_pos
                token["type"] = "group"

            if not inner_content:
                return None, total_pos

        token = flatten_group_token(token)
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
        token = self._process_content(second)
        return token, end_pos

    def _handle_box(self, content: str, match: re.Match) -> Tuple[str, int]:
        s = match.group(0)
        start_pos = match.end() - 1

        if s.startswith("\\adjustbox"):
            # strip out one brace
            _, end_pos = extract_nested_content(content[start_pos:], "{", "}")
            start_pos += end_pos

        extracted_content, end_pos = extract_nested_content(content[start_pos:])
        # extracted_content = extracted_content + "\n"  # add newline to end of box?

        one_liner = s.startswith("\\mbox")

        if self.process_content_fn:
            extracted_content = self.process_content_fn(extracted_content)

        if one_liner:
            # make everything into one line
            extracted_content = strip_latex_newlines(
                flatten_all_to_string(extracted_content)
            )

        out = normalize_text_token(extracted_content)
        # return as a list if group?
        if isinstance(out, dict) and out.get("type") == "group":
            return out["content"], start_pos + end_pos
        return out, start_pos + end_pos

    def _handle_color(self, content: str, match: re.Match) -> Tuple[str, int]:
        start_pos = match.end() - 1
        blocks, end_pos = extract_nested_content_sequence_blocks(
            content[start_pos:], max_blocks=2
        )
        text = ""
        total_pos = start_pos + end_pos
        styles = []
        if len(blocks) == 2:
            block0 = blocks[0].strip()
            color = "color="
            if match.group(1):
                color += "{%s:%s}" % (match.group(1).strip("[").strip("]"), block0)
            else:
                color += block0
            styles = [color]
            text = blocks[1]

        token = self._process_content(text)
        if styles:
            cur_styles = token.get("styles", [])
            token["styles"] = list(dict.fromkeys(styles + cur_styles))
        return token, total_pos

    def _handle_columns(self, content: str, match: re.Match) -> Tuple[str, int]:
        match_str = match.group(0)

        total_pos = match.end()
        if match_str.endswith("["):
            start_pos = match.end() - 1
            total_pos = start_pos
            extracted_content, end_pos = extract_nested_content(
                content[start_pos:], "[", "]"
            )
            if end_pos > 0:
                total_pos = start_pos + end_pos
                token = self._process_content(extracted_content)
                return token, total_pos

        return None, total_pos

    def _handle_subfloat(self, content: str, match: re.Match) -> Tuple[str, int]:
        start_pos = match.end() - 1
        caption, end_pos = extract_nested_content(content[start_pos:], "[", "]")
        caption = caption.strip()

        total_pos = start_pos + end_pos
        block, end_pos = extract_nested_content(content[total_pos:])
        if block:
            total_pos += end_pos

        caption = self._process_content(caption)
        if not isinstance(caption, list):
            caption = [caption]
        caption_token = {
            "type": "caption",
            "content": caption,
        }
        out_tokens = [caption_token]
        if block:
            block = self._process_content(block)
            if not isinstance(block, list):
                block = [block]
            out_tokens.extend(block)

        return {
            "type": "group",
            "content": out_tokens,
        }, total_pos

    def handle(self, content: str, prev_token: Optional[Dict] = None):

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
            elif name == "box":
                return self._handle_box(content, match)
            elif name == "color":
                return self._handle_color(content, match)
            elif name == "columns":
                return self._handle_columns(content, match)
            elif name == "subfloat":
                return self._handle_subfloat(content, match)
            elif name == "fancyhead":
                # same handling as box
                return self._handle_box(content, match)
            else:
                return None, match.end()

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
\textcolor[HTML]{FF0000}{Haha}
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
