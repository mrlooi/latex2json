from collections import OrderedDict
from typing import Callable, Dict, List, Optional, Tuple

import re

from latex2json.parser.handlers.base import TokenHandler
from latex2json.parser.patterns import BRACE_CONTENT_PATTERN, OPTIONAL_BRACE_PATTERN
from latex2json.utils.conversions import int_to_roman
from latex2json.utils.tex_utils import (
    extract_delimited_args,
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
    "overline": "overline",
    "textoverline": "overline",
    "textstrikeout": "line-through",  # requires ulem package in LaTeX
    "sout": "line-through",  # another strikethrough command
    "natexlab": None,
    "uppercase": "uppercase",
    "lowercase": "lowercase",
}

TEXT_COMMANDS = "|".join(FRONTEND_STYLE_MAPPING.keys())
TEXT_PATTERN = re.compile(
    rf"\\({TEXT_COMMANDS})" + r"(?![a-zA-Z])(?:\\expandafter)?(\s*(\{)|.*)?", re.DOTALL
)

BOX_DELIMITERS = {
    r"[fhv]box": "{",  # \fbox{text} hbox vbox
    "parbox": "[[[{{",  # \parbox[pos][height][inner-pos]{width}{text}
    "makebox": "[[{",  # \makebox[width]{text}
    "framebox": "[[{",  # \framebox[width][pos]{text}
    "raisebox": "{[[{",  # \raisebox{distance}[extend-above][extend-below]{text}
    "colorbox": "{{",  # \colorbox{color}{text}
    "fcolorbox": "{{{",  # \fcolorbox{border}{bg}{text}
    "scalebox": "{{",  # \scalebox{scale}{text}
    "mbox": "{",  # \mbox{text}
    r"hbox\s+to\s*[^{]+": "{",  # \hbox to \hsize{text}
    r"sbox\b\s*[^{]+": "{",  # \sbox\@tempboxa{text}
    "pbox": "{{",  # \pbox{x}{text}
    "resizebox": "{{{",  # \resizebox{width}{height}{text}
    "rotatebox": "{{",  # \rotatebox{angle}{text}
    "adjustbox": "{{",  # \adjustbox{max width=\textwidth}{text}
}

BOX_PATTERN = re.compile(
    r"\\(%s)\s*[\[\{]" % "|".join(BOX_DELIMITERS.keys()), re.VERBOSE | re.DOTALL
)

FONT_PATTERN = {
    "fontsize": (r"\\fontsize" + (r"\s*" + BRACE_CONTENT_PATTERN) * 2),
    "selectfont": (r"\\selectfont\b"),
    "usefont": (r"\\usefont" + (r"\s*" + BRACE_CONTENT_PATTERN) * 4),
}

PATTERNS = {
    "styled": TEXT_PATTERN,
    "box": BOX_PATTERN,
    "citetext": re.compile(r"\\citetext\s*\{"),
    # custom fonts (that we want to ignore)
    "fonts": re.compile("|".join(FONT_PATTERN.values())),
    "frac": re.compile(r"\\(?:frac|nicefrac|textfrac)\s*\{", re.DOTALL),  # \frac{}{}
    "texorpdfstring": re.compile(
        r"\\texorpdfstring\s*\{", re.DOTALL
    ),  # \texorpdfstring{pdf version}{text version}
    "color": re.compile(r"\\textcolor\s*(\[\w+\])?\s*{"),
    "columns": re.compile(r"\\(?:onecolumn\b|twocolumn\s*\[?)"),
    "subfloat": re.compile(r"\\subfloat\s*\["),
    "fancyhead": re.compile(
        r"\\(fancyhead|rhead|chead|lhead)\s*%s\s*{" % OPTIONAL_BRACE_PATTERN,
        re.DOTALL,
    ),
    "roman_numerals": re.compile(r"\\romannumeral\s+(\d+)"),
}


# Method 2: Using str.lstrip() with len comparison
def find_first_nonspace(s):
    return len(s) - len(s.lstrip())


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

    def _handle_styled(
        self, content: str, match: re.Match
    ) -> Tuple[Dict | List[Dict], int]:
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

    def _handle_citetext(self, content: str, match: re.Match) -> Tuple[str, int]:
        start_pos = match.end() - 1
        blocks, end_pos = extract_nested_content_sequence_blocks(
            content[start_pos:], "{", "}", max_blocks=1
        )
        if len(blocks) != 1:
            return None, start_pos
        block = blocks[0]
        if self.process_content_fn:
            block = self.process_content_fn(block)
        return block, start_pos + end_pos

    def _handle_frac(self, content: str, match: re.Match) -> Tuple[str, int]:
        start_pos = match.end() - 1
        blocks, end_pos = extract_nested_content_sequence_blocks(
            content[start_pos:], "{", "}", max_blocks=2
        )
        end_pos = start_pos + end_pos

        if len(blocks) != 2:
            return None, start_pos
        first, second = blocks

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
        start_pos = match.end() - 1
        blocks, end_pos = extract_nested_content_sequence_blocks(
            content[start_pos:], "{", "}", max_blocks=2
        )
        end_pos = start_pos + end_pos

        if len(blocks) != 2:
            return None, start_pos
        first, second = blocks

        # choose 2nd one in texorpdfstring
        token = self._process_content(second)
        return token, end_pos

    def _handle_box(
        self, content: str, match: re.Match
    ) -> Tuple[Dict | List[Dict], int]:
        s = match.group(0)
        start_pos = match.end() - 1

        start_char = s[-1]
        delimiter_str = BOX_DELIMITERS.get(match.group(1), start_char)
        N = len(delimiter_str)
        extracted_args, end_pos = extract_delimited_args(
            content[start_pos:], delimiter_str
        )
        end_pos += start_pos

        extracted_content = None
        if len(extracted_args) == N:
            extracted_content = extracted_args[-1]

        if not extracted_content:
            return None, end_pos

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
            return out["content"], end_pos
        return out, end_pos

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

    def _handle_roman_numerals(self, content: str, match: re.Match) -> Tuple[str, int]:
        numeral = int(match.group(1))

        roman_numeral = int_to_roman(numeral)
        return {"type": "text", "content": roman_numeral}, match.end()

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
            elif name == "citetext":
                return self._handle_citetext(content, match)
            elif name == "roman_numerals":
                return self._handle_roman_numerals(content, match)
            else:
                return None, match.end()

        return None, 0


if __name__ == "__main__":
    handler = TextFormattingHandler()

    test_cases = [
        (r"\makebox{Simple text}", "Simple text"),
        (r"\framebox{Simple text}", "Simple text"),
        (r"\raisebox{2pt}{Raised text}", "Raised text"),
        (r"\makebox[3cm]{Fixed width}", "Fixed width"),
        (r"\framebox[3cm][l]{Left in frame}", "Left in frame"),
        (r"\parbox{5cm}{Simple parbox text}", "Simple parbox text"),
        (r"\parbox[t][3cm][s]{5cm}{Stretched vertically}", "Stretched vertically"),
        (r"\fbox{Framed text}", "Framed text"),
        (r"\colorbox{yellow}{Colored box}", "Colored box"),
        (
            r"\parbox[c][3cm]{5cm}{Center aligned with fixed height}",
            "Center aligned with fixed height",
        ),
        (
            r"""\mbox{
            All
            One line ajajaja
            }""",
            "All One line ajajaja",
        ),
        (r"\hbox to 3in{Some text}", "Some text"),
        (r"\sbox\@tempboxa{Some text}", "Some text"),
        (r"\pbox{3cm}{Some text}", "Some text"),
        (r"\adjustbox{max width=\textwidth}{Some text}", "Some text"),
        (r"\rotatebox{90}{Some text}", "Some text"),
    ]

    for command, expected_text in test_cases:
        token, pos = handler.handle(command)
        print(command)
        assert token and token["content"].strip() == expected_text
