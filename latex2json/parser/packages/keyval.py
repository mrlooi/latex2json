import re
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

from latex2json.parser.handlers.base import TokenHandler
from latex2json.utils.tex_utils import (
    extract_nested_content_sequence_blocks,
    substitute_args,
)


@dataclass
class KeyDefinition:
    family: str
    key: str
    default: Optional[str] = None
    codeblock: Optional[str] = None


# Compile all patterns at module level
PATTERNS = {
    "define_key": re.compile(r"\\define@key\s*"),
    "setkeys": re.compile(r"\\setkeys\s*"),
}

KEY_VALUE_PATTERN = re.compile(r"([^=,\s]+)(?:=([^,]+))?")


class KeyValHandler(TokenHandler):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.key_definitions: Dict[str, Dict[str, KeyDefinition]] = {}

    def can_handle(self, content: str) -> bool:
        return any(pattern.match(content) for pattern in PATTERNS.values())

    def _handle_define_key_match(
        self, match: re.Match, content: str
    ) -> Tuple[Optional[Dict], int]:
        pos = match.end()
        content = content[pos:]

        # Extract family and key together
        blocks, end_pos = extract_nested_content_sequence_blocks(
            content, "{", "}", max_blocks=2
        )
        if len(blocks) < 2:
            return None, 0
        family, key = blocks[0], blocks[1]
        pos += end_pos
        content = content[end_pos:]

        # Extract optional default value
        default = None
        default_blocks, end_pos = extract_nested_content_sequence_blocks(
            content, "[", "]", max_blocks=1
        )
        if default_blocks:
            default = default_blocks[0]
            pos += end_pos
            content = content[end_pos:]

        # Extract handler
        handler_blocks, end_pos = extract_nested_content_sequence_blocks(
            content, "{", "}", max_blocks=1
        )
        if not handler_blocks:
            return None, 0
        codeblock = handler_blocks[0]
        total_pos = pos + end_pos

        # Store the key definition
        if family not in self.key_definitions:
            self.key_definitions[family] = {}

        self.key_definitions[family][key] = KeyDefinition(
            family=family, key=key, default=default, codeblock=codeblock
        )

        return {
            "type": "keyval_definition",
            "name": f"keyval-{family}-{key}",
            "family": family,
            "key": key,
            "default": default,
            "codeblock": codeblock,
        }, total_pos

    def _handle_setkeys_match(
        self, match: re.Match, content: str
    ) -> Tuple[Optional[Dict], int]:
        pos = match.end()
        content = content[pos:]

        # Extract family and key-value pairs together
        blocks, end_pos = extract_nested_content_sequence_blocks(
            content, "{", "}", max_blocks=2
        )
        if len(blocks) < 2:
            return None, 0
        family, key_values_str = blocks[0], blocks[1]
        total_pos = pos + end_pos

        key_values = []
        for key_value_match in KEY_VALUE_PATTERN.finditer(key_values_str):
            key = key_value_match.group(1)
            value = key_value_match.group(2)
            key_values.append({"key": key, "value": value.strip() if value else "true"})

        return {
            "type": "keyval_setting",
            "family": family,
            "key_values": key_values,
        }, total_pos

    def _process_setkeys_token(self, token: Dict):
        codeblocks = {}
        family = token.get("family", "")
        if family in self.key_definitions:
            key_values = token["key_values"]
            for key_value in key_values:
                key = key_value["key"]
                value = key_value["value"]
                if key in self.key_definitions[family]:
                    codeblock = self.key_definitions[family][key].codeblock
                    if codeblock:
                        codeblock = substitute_args(codeblock, [value])
                        codeblocks[key] = codeblock

        return codeblocks

    def _handle(self, content: str) -> Tuple[Optional[Dict], int]:
        """Handle keyval commands and return appropriate token"""
        for pattern_name, pattern in PATTERNS.items():
            match = pattern.match(content)
            if match:
                if pattern_name == "define_key":
                    return self._handle_define_key_match(match, content)
                elif pattern_name == "setkeys":
                    out, pos = self._handle_setkeys_match(match, content)
                    if out:
                        codeblocks = self._process_setkeys_token(out)
                        out["codeblocks"] = codeblocks
                    return out, pos

        return None, 0

    def handle(
        self, content: str, prev_token: Optional[Dict] = None
    ) -> Tuple[Optional[Dict], int]:
        token, pos = self._handle(content)
        return token, pos

    def process_keyval_definition(
        self, family: str, key: str, default: Optional[str], codeblock: Optional[str]
    ):
        """Process a keyval definition by storing it in the key_definitions dictionary."""
        if family not in self.key_definitions:
            self.key_definitions[family] = {}

        self.key_definitions[family][key] = KeyDefinition(
            family=family, key=key, default=default, codeblock=codeblock
        )

    def clear(self):
        self.key_definitions = {}


if __name__ == "__main__":
    # Test the implementation
    handler = KeyValHandler()

    tests = [
        r"\define@key{pubdet}{article}[true]{} POST",
        r"\define@key{pubdet}{note}[true]{\toc@notesetup} POST",
        r"\setkeys{pubdet}{article=false,note} POST",
    ]

    for test in tests:
        token, pos = handler.handle(test)
        print(f"\nInput: {test}")
        print(f"Output: {token}")
        print(test[pos:])
