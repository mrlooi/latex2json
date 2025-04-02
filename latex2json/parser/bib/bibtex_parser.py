from dataclasses import dataclass
from logging import Logger
import logging
import re
from typing import Dict, List, Optional
from latex2json.utils.tex_utils import (
    extract_nested_content,
    strip_latex_comments,
    normalize_whitespace_and_lines,
)


@dataclass
class BibEntry:
    """Unified bibliography entry model for both BibTeX and bibitem"""

    citation_key: str
    content: str
    title: Optional[str]
    # BibTeX related below
    entry_type: Optional[
        str
    ]  # 'article', 'book', etc. for BibTeX; 'bibitem' for LaTeX bibitem
    fields: Optional[Dict[str, str]]

    @classmethod
    def from_bibtex(
        cls, entry_type: str, citation_key: str, fields: Dict[str, str]
    ) -> "BibEntry":
        """Convert BibTeX entry to bibliography entry"""
        # Format content as string representation of fields
        content = ", ".join(f"{k}={v}" for k, v in fields.items())

        return cls(
            entry_type=entry_type,
            citation_key=citation_key,
            title=fields.get("title"),
            content=content,
            fields=fields,
        )


BibTexPattern = re.compile(r"@(\w+)\s*\{")
BibTexFieldPattern = re.compile(r"(\w+)\s*=\s*")


def preprocess(content: str) -> str:
    """Preprocess content to remove comments and normalize whitespace"""
    content = strip_latex_comments(content)
    content = normalize_whitespace_and_lines(content)
    return content.strip()


class BibTexParser:
    def __init__(self, logger: Logger = None):
        self.logger = logger or logging.getLogger(__name__)

    @staticmethod
    def is_bibtex(content: str) -> bool:
        """Check if the content is in BibTeX format.

        Args:
            content: The content to check

        Returns:
            bool: True if content is in BibTeX format, False otherwise
        """
        return bool(BibTexPattern.search(content))

    def parse(self, content: str) -> List[BibEntry]:
        """Parse BibTeX content and return list of BibEntry objects"""
        self.logger.info("Starting BibTeX parsing")
        entries = []
        pos = 0

        content = preprocess(content)

        # Find each entry starting with @
        for match in re.finditer(BibTexPattern, content):
            entry_type = match.group(1).lower()
            start_pos = match.end() - 1  # Position of the opening brace

            # Get everything inside the braces
            entry_content, next_pos = extract_nested_content(content[start_pos:])
            if entry_content is None:
                continue

            # Split into citation key and fields
            key_end = entry_content.find(",")
            if key_end == -1:
                continue

            citation_key = entry_content[:key_end].strip()
            fields_text = entry_content[key_end + 1 :].strip()

            # Parse fields
            fields = {}
            pos = 0

            while pos < len(fields_text):
                field_match = re.search(BibTexFieldPattern, fields_text[pos:])
                if not field_match:
                    break

                field_name = field_match.group(1).lower()
                field_start = pos + field_match.end()

                # Get value - either in braces or quotes
                if fields_text[field_start:].lstrip().startswith("{"):
                    # Skip whitespace to actual brace
                    while (
                        field_start < len(fields_text)
                        and fields_text[field_start].isspace()
                    ):
                        field_start += 1
                    value, value_end = extract_nested_content(fields_text[field_start:])
                    if value is not None:
                        fields[field_name] = value.strip()
                        pos = field_start + value_end
                else:
                    # Handle quoted values
                    quote_match = re.match(r'\s*"([^"]*)"', fields_text[field_start:])
                    if quote_match:
                        fields[field_name] = quote_match.group(1)
                        pos = field_start + quote_match.end()
                    else:
                        pos = field_start + 1

                # Skip trailing comma and whitespace
                while pos < len(fields_text) and (
                    fields_text[pos].isspace() or fields_text[pos] == ","
                ):
                    pos += 1

            entry = BibEntry.from_bibtex(
                entry_type=entry_type, citation_key=citation_key, fields=fields
            )
            entries.append(entry)

        return entries


if __name__ == "__main__":
    parser = BibTexParser()
    # For BibTeX content
    bibtex_content = """
    @article{key1,
    title={Some Title},
    author={Author Name},
    year={2023}
    }
    """
    entries = parser.parse(bibtex_content)
    print(entries)
