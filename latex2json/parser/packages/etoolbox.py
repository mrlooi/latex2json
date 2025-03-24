import re
from typing import Dict, Optional, Tuple
from latex2json.parser.handlers.base import TokenHandler
from latex2json.utils.tex_utils import extract_nested_content_sequence_blocks

# Compile patterns at module level
PATTERNS = {
    "ifnotbool": re.compile(r"\\(?:if|not)bool\s*{([^}]*)}"),
    "newbool": re.compile(r"\\newbool\s*{([^}]*)}"),
    "providebool": re.compile(r"\\providebool\s*{([^}]*)}"),
    "setbool": re.compile(r"\\setbool\s*{([^}]*)}"),
    "booltrue": re.compile(r"\\booltrue\s*{([^}]*)}"),
    "boolfalse": re.compile(r"\\boolfalse\s*{([^}]*)}"),
}


class EtoolboxHandler(TokenHandler):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.bool_definitions: Dict[str, bool] = {}

    def clear(self):
        self.bool_definitions = {}

    def can_handle(self, content: str) -> bool:
        return any(pattern.match(content) for pattern in PATTERNS.values())

    def handle(
        self, content: str, prev_token: Optional[Dict] = None
    ) -> Tuple[Optional[Dict], int]:
        """Handle etoolbox boolean commands"""
        for pattern_name, pattern in PATTERNS.items():
            match = pattern.match(content)
            if match:
                if pattern_name == "ifnotbool":
                    return self._handle_ifnotbool(content, match)
                elif pattern_name == "newbool":
                    return self._handle_newbool(match)
                elif pattern_name == "providebool":
                    return self._handle_providebool(match)
                elif pattern_name == "setbool":
                    return self._handle_setbool(content, match)
                elif pattern_name in ["booltrue", "boolfalse"]:
                    return self._handle_bool_value(match, pattern_name == "booltrue")

        return None, 0

    def _handle_ifnotbool(self, content: str, match) -> Tuple[Optional[Dict], int]:
        r"""Handle \ifnotbool and \notbool commands"""
        bool_name = match.group(1)
        is_not = content.startswith(r"\notbool")
        start_pos = match.end()

        # Extract true and false code blocks
        blocks, end_pos = extract_nested_content_sequence_blocks(
            content[start_pos:], "{", "}", max_blocks=2
        )
        if len(blocks) != 2:
            return None, start_pos

        true_code = blocks[0] if not is_not else blocks[1]
        false_code = blocks[1] if not is_not else blocks[0]

        token = {
            "type": "bool_conditional",
            "name": bool_name,
            "true_code": true_code,
            "false_code": false_code,
            "is_not": is_not,
        }

        return token, start_pos + end_pos

    def _handle_newbool(self, match) -> Tuple[Optional[Dict], int]:
        """Handle \newbool command"""
        bool_name = match.group(1)
        self.bool_definitions[bool_name] = False

        token = {
            "type": "bool_definition",
            "name": bool_name,
            "definition_type": "newbool",
        }

        return token, match.end()

    def _handle_providebool(self, match) -> Tuple[Optional[Dict], int]:
        r"""Handle \providebool command"""
        bool_name = match.group(1)
        if bool_name not in self.bool_definitions:
            self.bool_definitions[bool_name] = False

        token = {
            "type": "bool_definition",
            "name": bool_name,
            "definition_type": "providebool",
        }

        return token, match.end()

    def _handle_setbool(self, content: str, match) -> Tuple[Optional[Dict], int]:
        r"""Handle \setbool command"""
        bool_name = match.group(1)
        start_pos = match.end()

        # Extract value
        blocks, end_pos = extract_nested_content_sequence_blocks(
            content[start_pos:], "{", "}", max_blocks=1
        )
        if not blocks:
            return None, start_pos

        value = blocks[0].lower() == "true"
        if bool_name in self.bool_definitions:
            self.bool_definitions[bool_name] = value

        token = {
            "type": "bool_set",
            "name": bool_name,
            "value": value,
        }

        return token, start_pos + end_pos

    def _handle_bool_value(self, match, value: bool) -> Tuple[Optional[Dict], int]:
        r"""Handle \booltrue and \boolfalse commands"""
        bool_name = match.group(1)
        if bool_name in self.bool_definitions:
            self.bool_definitions[bool_name] = value

        token = {
            "type": "bool_set",
            "name": bool_name,
            "value": value,
        }

        return token, match.end()
