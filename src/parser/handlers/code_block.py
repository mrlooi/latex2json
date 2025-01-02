import re
from typing import Callable, Dict, Optional, Tuple
from src.parser.handlers.base import TokenHandler

# Compile patterns for code blocks
PATTERNS = {
    "verbatim_env": re.compile(
        r"\\begin\s*\{verbatim\}(.*?)\\end\s*\{verbatim\}", re.DOTALL
    ),
    "lstlisting": re.compile(
        r"\\begin\s*\{lstlisting\}(?:\[([^\]]*)\])?(.*?)\\end\s*\{lstlisting\}",
        re.DOTALL,
    ),
    "verb_command": re.compile(
        r"\\verb\*?([^a-zA-Z])(.*?)\1"
    ),  # \verb|code| or \verb*|code|
}


class CodeBlockHandler(TokenHandler):
    def can_handle(self, content: str) -> bool:
        """Check if the content contains any code block commands"""
        return any(pattern.match(content) for pattern in PATTERNS.values())

    def handle(
        self, content: str, prev_token: Optional[Dict] = None
    ) -> Tuple[Optional[Dict], int]:
        """Handle code block commands and return appropriate token"""
        for pattern_name, pattern in PATTERNS.items():
            match = pattern.match(content)
            if match:
                if pattern_name == "verbatim_env":
                    return {
                        "type": "code",
                        "content": match.group(1).strip(),
                    }, match.end()

                elif pattern_name == "verb_command":
                    return {
                        "type": "code",
                        "content": match.group(2).strip(),
                    }, match.end()

                elif pattern_name == "lstlisting":
                    token = {
                        "type": "code",
                        "content": match.group(2).strip(),
                    }
                    if match.group(1):  # Optional title/parameters
                        token["title"] = match.group(1).strip()
                    return token, match.end()

        return None, 0
