from typing import Dict, List, Tuple, Optional
import re

from latex2json.parser.handlers.base import TokenHandler
from latex2json.parser.handlers.new_definition import command_with_opt_brace_pattern
from latex2json.parser.patterns import OPTIONAL_BRACE_PATTERN
from latex2json.utils.tex_utils import (
    extract_nested_content,
    extract_delimited_args,
    strip_latex_newlines,
    flatten_all_to_string,
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
    "pbox": "{{",  # \pbox{x}{text}
    "resizebox": "{{{",  # \resizebox{width}{height}{text}
    "rotatebox": "{{",  # \rotatebox{angle}{text}
    "adjustbox": "{{",  # \adjustbox{max width=\textwidth}{text}
}

BOX_PATTERN = re.compile(
    r"\\(%s)\s*[\[\{]" % "|".join(BOX_DELIMITERS.keys()), re.VERBOSE | re.DOTALL
)

# Add fancyhead pattern
FANCYHEAD_PATTERN = re.compile(
    r"\\(fancyhead|fancyheadoffset|rhead|chead|lhead)\s*%s\s*{"
    % OPTIONAL_BRACE_PATTERN,
    re.DOTALL,
)

# Add new pattern after BOX_PATTERN
SAVED_BOX_PATTERN = re.compile(
    r"\\(usebox|sbox|savebox|newsavebox|newbox)\s*(%s)"
    % command_with_opt_brace_pattern,
    re.VERBOSE | re.DOTALL,
)

# add ADDITIONAL pattern for setbox
SETBOX_PATTERN = re.compile(
    r"\\setbox\s*(\d+|%s)\s*=\s*" % command_with_opt_brace_pattern,
    re.VERBOSE | re.DOTALL,
)


def parse_varname_from_brace_or_backslash(var_name: str) -> Tuple[Optional[str], int]:
    if var_name.startswith("{"):
        _var_name, _ = extract_nested_content(var_name)
        if _var_name:
            var_name = _var_name.strip()
    if var_name.startswith("\\"):
        var_name = var_name[1:]
    if "{" in var_name:
        var_name = var_name[: var_name.find("{")].strip()
    return var_name


class BoxHandler(TokenHandler):
    saved_boxes = {}
    numbered_boxes = {}  # Add storage for numbered boxes

    def can_handle(self, content: str) -> bool:
        return bool(
            BOX_PATTERN.match(content)
            or FANCYHEAD_PATTERN.match(content)
            or SAVED_BOX_PATTERN.match(content)
            or SETBOX_PATTERN.match(content)  # Add setbox pattern
        )

    def clear(self):
        self.saved_boxes = {}
        self.numbered_boxes = {}  # Clear numbered boxes too

    def handle(
        self, content: str, prev_token: Dict = None
    ) -> Tuple[Dict | List[Dict], int]:
        # Try to match setbox first
        setbox_match = SETBOX_PATTERN.match(content)
        if setbox_match:
            return self._handle_setbox(content, setbox_match)

        # Try to match saved box commands first
        saved_match = SAVED_BOX_PATTERN.match(content)
        if saved_match:
            return self._handle_saved_box(content, saved_match)

        match = BOX_PATTERN.match(content) or FANCYHEAD_PATTERN.match(content)
        if not match:
            return None, 0

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

        if isinstance(extracted_content, str):
            return {"type": "text", "content": extracted_content}, end_pos
        elif isinstance(extracted_content, dict):
            if extracted_content.get("type") == "group":
                return extracted_content["content"], end_pos
            return extracted_content, end_pos
        return extracted_content, end_pos

    def _handle_saved_box(
        self, content: str, match: re.Match
    ) -> Tuple[Optional[Dict], int]:
        command = match.group(1)
        box_name = match.group(2)

        # Strip braces from box name if present
        box_name = parse_varname_from_brace_or_backslash(box_name)

        if command.startswith("new"):
            # Just register the box name
            self.saved_boxes[box_name] = None
            return None, match.end()

        elif command in ("sbox", "savebox"):
            # Extract the box content
            start_pos = match.end()
            extracted_args, end_pos = extract_delimited_args(content[start_pos:], "{")
            if extracted_args:
                box_content = extracted_args[0]
                if self.process_content_fn:
                    box_content = self.process_content_fn(box_content)
                # Store content in a consistent format
                if isinstance(box_content, str):
                    self.saved_boxes[box_name] = {
                        "type": "text",
                        "content": box_content,
                    }
                else:
                    self.saved_boxes[box_name] = box_content
                return None, start_pos + end_pos
            return None, start_pos

        elif command == "usebox":
            # Return the saved box content if it exists
            if box_name in self.saved_boxes and self.saved_boxes[box_name] is not None:
                return self.saved_boxes[box_name], match.end()

        return None, match.end()

    def _handle_setbox(
        self, content: str, match: re.Match
    ) -> Tuple[Optional[Dict], int]:

        box_name = match.group(1).strip()

        # check if box_name is a number or \command
        save_box_dict = self.saved_boxes
        is_digit = box_name.isdigit()
        if is_digit:
            box_name = int(box_name)
            save_box_dict = self.numbered_boxes
        else:
            box_name = parse_varname_from_brace_or_backslash(box_name)

        start_pos = match.end()

        # Skip any whitespace after the =
        while start_pos < len(content) and content[start_pos].isspace():
            start_pos += 1

        # Check if the content after = matches any box pattern
        remaining_content = content[start_pos:]
        box_match = BOX_PATTERN.match(remaining_content)

        if box_match:
            # Use the existing box handling logic
            box_result, end_pos = self.handle(remaining_content)
            if box_result:
                save_box_dict[box_name] = box_result
                return None, start_pos + end_pos

        # Fallback to direct content extraction if no box pattern matches
        extracted_args, end_pos = extract_delimited_args(remaining_content, "{")
        if extracted_args:
            box_content = extracted_args[0]
            if self.process_content_fn:
                box_content = self.process_content_fn(box_content)
            # Store content in a consistent format
            if isinstance(box_content, str):
                save_box_dict[box_name] = {
                    "type": "text",
                    "content": box_content,
                }
            else:
                save_box_dict[box_name] = box_content
            return None, start_pos + end_pos

        return None, start_pos


if __name__ == "__main__":
    # Example usage of box handling
    handler = BoxHandler()

    # command1 = r"\newsavebox{\mybox} POST"
    # result1, pos1 = handler.handle(command1)
    # assert command1[pos1:] == " POST"
    # assert result1 is None  # newsavebox just registers, returns nothing
    # assert "mybox" in handler.saved_boxes
    # assert handler.saved_boxes["mybox"] is None

    # # Test sbox storing content
    # command2 = r"\sbox\mybox{Stored content} POST"
    # result2, pos2 = handler.handle(command2)
    # assert command2[pos2:] == " POST"
    # assert result2 is None  # sbox stores but returns nothing

    command1 = r"\setbox0=\hbox{Hello} POST"
    result1, pos1 = handler.handle(command1)
    print(result1)
    print(command1[pos1:])
