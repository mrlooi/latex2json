from typing import Dict, Optional, Set, Tuple
import logging
import re

from latex2json.parser.handlers.base import TokenHandler
from latex2json.parser.patterns import WHITELISTED_COMMANDS
from latex2json.parser.handlers.command_processor import CommandProcessor
from latex2json.parser.handlers.new_definition import NewDefinitionHandler
from latex2json.parser.packages.keyval import KeyValHandler


class CommandManager(TokenHandler):
    def __init__(
        self,
        command_types: Optional[Set[str]] = None,
        logger=None,
        process_content_fn=None,
    ):
        self.process_content_fn = process_content_fn

        self.logger = logger or logging.getLogger(__name__)
        self.command_types = command_types

        # Existing handlers
        self.definition_handler = NewDefinitionHandler()
        self.processor = CommandProcessor()

        # Add KeyValHandler as a member
        self.keyval_handler = KeyValHandler()

        # Track unknown commands like tex_parser does
        self._unknown_commands = {}

    def clear(self):
        """Clear all handlers"""
        self.definition_handler.clear()
        self.processor.clear()
        self.keyval_handler.clear()
        self._unknown_commands = {}

    def process_definition(
        self, content: str, register: bool = True
    ) -> Tuple[Optional[Dict], int]:
        """Handle command definitions and register them"""
        # First try the definition handler
        if self.definition_handler.can_handle(content):
            token, end_pos = self.definition_handler.handle(content)
            if register and token:
                self.register_command(token)
            return token, end_pos

        # Then try the keyval handler
        if self.keyval_handler.can_handle(content):
            token, end_pos = self.keyval_handler.handle(content)
            # Keyval handler might return None for token when it successfully
            # processes but wants to suppress token generation
            return token, end_pos

        return None, 0

    def _should_handle_command_type(self, cmd_type: str) -> bool:
        return not self.command_types or cmd_type in self.command_types

    def register_command(self, token: Dict) -> None:
        """Register commands based on their type"""
        if not token or "name" not in token:
            return

        cmd_name = token.get("name", "")
        if not cmd_name or cmd_name in WHITELISTED_COMMANDS:
            return

        if not self._should_handle_command_type(token["type"]):
            return

        # Consolidate command registration logic from sty_parser/tex_parser/tex_preprocessor
        if token["type"] == "newcommand":
            # Check for recursion like tex_parser does
            if re.search(token["usage_pattern"], token["content"]):
                self.logger.warning(
                    f"Potential recursion detected for newcommand: \\{cmd_name}, skipping..."
                )
                return
            self.processor.process_newcommand(
                cmd_name,
                token["content"],
                token["num_args"],
                token["defaults"],
                token["usage_pattern"],
            )
        elif token["type"] == "def":
            self.processor.process_newdef(
                cmd_name,
                token["content"],
                token["num_args"],
                token["usage_pattern"],
                token["is_edef"],
            )
        elif token["type"] == "newif":
            self.processor.process_newif(cmd_name)
        elif token["type"] == "newcounter":
            self.processor.process_newcounter(cmd_name)
        elif token["type"] == "newlength":
            self.processor.process_newlength(cmd_name)
        elif token["type"] == "newtoks":
            self.processor.process_newtoks(cmd_name)
        elif token["type"] == "paired_delimiter":
            self.processor.process_paired_delimiter(
                cmd_name, token["left_delim"], token["right_delim"]
            )
        elif token["type"] in ["newother", "newfam", "font"]:
            self.processor.process_newX(cmd_name)
        elif token["type"] == "keyval_definition":
            self.keyval_handler.process_keyval_definition(
                token["family"], token["key"], token["default"], token["codeblock"]
            )
        # elif token["type"] == "keyval_setting":
        #     self.processor.process_keyval_setting(token["family"], token["key_values"])

    def expand_commands(
        self, content: str, ignore_unicode: bool = False, math_mode: bool = False
    ) -> Tuple[str, int]:
        """Expand commands in content"""
        return self.processor.expand_commands(content, ignore_unicode, math_mode)

    def handle(self, content: str) -> Tuple[str, int]:
        """Handle commands with appropriate handlers"""
        # First try the keyval handler
        if self.keyval_handler.can_handle(content):
            token, end_pos = self.keyval_handler.handle(content)
            if end_pos > 0:
                if token.get("codeblocks"):
                    out_str = ""
                    for key, codeblock in token["codeblocks"].items():
                        out_str += codeblock + "\n"
                    return out_str, end_pos
                # If KeyValHandler processed it, pass through the result
                return "", end_pos

        # If not handled by keyval, use the command processor
        return self.processor.handle(content)

    def can_handle(self, content: str) -> bool:
        """Check if content can be handled by any of our handlers"""
        return (
            self.definition_handler.can_handle(content)
            or self.processor.can_handle(content)
            or self.keyval_handler.can_handle(content)
        )

    @property
    def commands(self):
        """Access to registered commands"""
        return self.processor.commands
