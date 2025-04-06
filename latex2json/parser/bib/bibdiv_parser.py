from dataclasses import dataclass
from logging import Logger
import logging
import re
from typing import Dict, List, Optional
from latex2json.utils.tex_utils import (
    extract_nested_content,
)
from latex2json.parser.bib.bibtex_parser import BibTexEntry

BibDivPattern = re.compile(r"\\begin\s*{bibdiv}")
BibPattern = re.compile(r"\\bib\s*\{([^}]+)\}\s*\{([^}]+)\}")


class BibDivParser:
    def __init__(self, logger: Logger = None):
        self.logger = logger or logging.getLogger(__name__)

    @staticmethod
    def can_handle(content: str) -> bool:
        """Check if this parser can handle the given content.

        Args:
            content: The content to check

        Returns:
            bool: True if content can be handled by this parser
        """
        return BibDivParser.is_bibdiv(content)

    @staticmethod
    def is_bibdiv(content: str) -> bool:
        """Check if the content is in bibdiv format.

        Args:
            content: The content to check

        Returns:
            bool: True if content is in bibdiv format, False otherwise
        """
        return bool(BibDivPattern.search(content))

    def parse(self, content: str) -> List[BibTexEntry]:
        """Parse bibdiv content and return list of BibEntry objects"""
        self.logger.info("Starting BibDiv parsing")
        entries = []

        # # Find bibdiv environment
        # bibdiv_match = BibDivPattern.search(content)
        # if not bibdiv_match:
        #     return entries

        # # Extract content inside bibdiv
        # bibdiv_content, _ = extract_nested_content(content[bibdiv_match.start() :])
        # if not bibdiv_content:
        #     return entries

        bibdiv_content = content

        # Find each \bib entry
        for match in re.finditer(BibPattern, bibdiv_content):
            citation_key = match.group(1)
            entry_type = match.group(2)

            # Get everything inside the braces after the entry type
            entry_content, _ = extract_nested_content(bibdiv_content[match.end() :])
            if not entry_content:
                continue

            # Parse fields
            fields = {}
            pos = 0
            while pos < len(entry_content):
                # Find field name
                field_match = re.match(r"\s*(\w+)\s*=\s*", entry_content[pos:])
                if not field_match:
                    pos += 1
                    continue

                field_name = field_match.group(1).lower()
                field_start = pos + field_match.end()

                # Get value - either in braces or until comma
                if entry_content[field_start:].lstrip().startswith("{"):
                    # Skip whitespace to actual brace
                    while (
                        field_start < len(entry_content)
                        and entry_content[field_start].isspace()
                    ):
                        field_start += 1
                    value, value_end = extract_nested_content(
                        entry_content[field_start:]
                    )
                    if value is not None:
                        # Strip any remaining braces from the value
                        value = re.sub(r"\{([^}]*)\}", r"\1", value)
                        value = value.strip()
                        # Handle multiple instances of the same field
                        if field_name in fields:
                            fields[field_name] = f"{fields[field_name]} and {value}"
                        else:
                            fields[field_name] = value
                        pos = field_start + value_end
                else:
                    # Handle values until comma
                    comma_pos = entry_content.find(",", field_start)
                    if comma_pos == -1:
                        comma_pos = len(entry_content)
                    value = entry_content[field_start:comma_pos].strip()
                    # Strip any remaining braces from the value
                    value = re.sub(r"\{([^}]*)\}", r"\1", value)
                    # Handle multiple instances of the same field
                    if field_name in fields:
                        fields[field_name] = f"{fields[field_name]} and {value}"
                    else:
                        fields[field_name] = value
                    pos = comma_pos + 1

                # Skip trailing whitespace
                while pos < len(entry_content) and entry_content[pos].isspace():
                    pos += 1

            entry = BibTexEntry.from_bibtex(
                entry_type=entry_type, citation_key=citation_key, fields=fields
            )
            entries.append(entry)

        return entries


if __name__ == "__main__":
    parser = BibDivParser()

    text = r"""
\begin{bibdiv}
\begin{biblist}

\bib{CZN23strip}{article}{
      author={{Coti Zelati}, Michele},
      author={{Nualart}, Marc},
       title={{Explicit solutions and linear inviscid damping in the
  Euler-Boussinesq equation near a stratified Couette flow in the periodic
  strip}},
        date={2023-09},
     journal={arXiv e-prints},
      eprint={2309.08419},
}

\end{biblist}
\end{bibdiv}
"""
    entries = parser.parse(text)
    print(entries)
