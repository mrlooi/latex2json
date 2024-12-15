from dataclasses import dataclass
from typing import Dict, List
import re
from src.tex_utils import extract_nested_content


@dataclass
class BibEntry:
    entry_type: str
    citation_key: str
    fields: Dict[str, str]


class BibParser:
    def __init__(self):
        self.entries: List[BibEntry] = []

    def parse(self, content: str) -> List[BibEntry]:
        """Parse BibTeX content and return list of BibEntry objects"""
        self.entries = []
        pos = 0

        # Find each entry starting with @
        entry_pattern = r"@(\w+)\s*\{"
        for match in re.finditer(entry_pattern, content):
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
            field_pattern = r"(\w+)\s*=\s*"
            pos = 0

            while pos < len(fields_text):
                field_match = re.search(field_pattern, fields_text[pos:])
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
                        fields[field_name] = value
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

            entry = BibEntry(
                entry_type=entry_type, citation_key=citation_key, fields=fields
            )
            self.entries.append(entry)

        return self.entries

    def to_dict(self) -> List[Dict]:
        """Convert entries to list of dictionaries"""
        return [
            {"type": entry.entry_type, "key": entry.citation_key, **entry.fields}
            for entry in self.entries
        ]
