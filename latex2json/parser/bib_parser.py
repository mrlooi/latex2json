from dataclasses import dataclass
from logging import Logger
import logging
from typing import Dict, List, Optional
import re
from latex2json.utils.tex_utils import (
    extract_nested_content,
    strip_latex_comments,
    normalize_whitespace_and_lines,
)
from latex2json.parser.bib.compiled_bibtex import (
    is_compiled_bibtex,
    process_compiled_bibtex_to_bibtex,
)

import os


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
    def from_bibitem(cls, token: Dict) -> "BibEntry":
        """Convert bibitem token to bibliography entry"""
        return cls(
            citation_key=token["cite_key"],
            title=token.get("title"),
            content=token["content"],
            fields={},
        )

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


BibItemPattern = re.compile(
    r"\\bibitem\s*(?:\[(.*?)\])?\{(.*?)\}\s*([\s\S]*?)(?=\\bibitem|$)",
    re.DOTALL,
)
NewblockPattern = re.compile(r"\\newblock\b")


class BibParser:
    def __init__(self, logger: logging.Logger = None):
        # for logging
        self.logger = logger or logging.getLogger(__name__)

        self.bibtex_parser = BibTexParser(logger=self.logger)

    def clear(self):
        pass

    def parse(self, content: str) -> List[BibEntry]:
        """Parse both BibTeX and bibitem entries from the content"""

        content = preprocess(content)

        entries = []

        # Check if content has bibliography environment
        bib_env_pattern = r"\\begin{(\w*bibliography)}(.*?)\\end{\1}"
        bib_env_match = re.search(bib_env_pattern, content, re.DOTALL)

        if bib_env_match:
            self.logger.debug("Parsing bibliography environment content")
            bib_content = bib_env_match.group(2)
            entries.extend(self._parse_bibitems(bib_content))
        elif is_compiled_bibtex(content):
            self.logger.debug("Parsing compiled BibTeX content")
            # first convert to bibtex format
            bibtex_content = process_compiled_bibtex_to_bibtex(content)
            entries.extend(self.bibtex_parser.parse("\n".join(bibtex_content)))
        elif re.search(BibTexPattern, content):
            self.logger.debug("Parsing BibTeX content")
            entries.extend(self.bibtex_parser.parse(content))
        else:
            self.logger.debug("Parsing standalone bibitem content")
            entries.extend(self._parse_bibitems(content))

        self.logger.info(f"BibParser: Found {len(entries)} entries")
        return entries

    def _parse_bibitems(self, content: str) -> List[BibEntry]:
        """Parse bibitem entries from content"""
        entries = []
        previous_content = None
        bysame_pattern = re.compile(r"\\bysame\b")

        for match in BibItemPattern.finditer(content):
            item = match.group(3).strip()
            if item:
                # remove newblock
                item = NewblockPattern.sub("", item)

                # Handle \bysame by replacing it with content from previous entry
                if previous_content and bysame_pattern.search(item):
                    # Extract author part from previous entry (up to first comma)
                    author_part = previous_content.split(",")[0]
                    if author_part:
                        item = bysame_pattern.sub(author_part, item)

                entry = BibEntry(
                    citation_key=match.group(2).strip(),
                    content=item,
                    title=match.group(1).strip() if match.group(1) else None,
                    entry_type="bibitem",
                    fields={},
                )
                entries.append(entry)
                previous_content = item
        return entries

    def parse_file(self, file_path: str) -> List[BibEntry]:
        """Parse a bibliography file and return list of entries.

        Args:
            file_path: Path to the bibliography file (with or without extension)

        Returns:
            List[BibEntry]: List of parsed bibliography entries
        """
        exts = [".bbl", ".bib"]

        # Try to find and read the bib file
        bib_content = None

        # Case 1: File already has correct extension
        if file_path.endswith(tuple(exts)) and os.path.exists(file_path):
            with open(file_path, "r") as f:
                bib_content = f.read()

        # Case 2: Need to try adding extensions
        else:
            for ext in exts:
                full_path = file_path + ext
                if os.path.exists(full_path):
                    with open(full_path, "r") as f:
                        bib_content = f.read()
                    break

        # Case 3: Try main.bbl first, then any .bbl file in the same directory
        if not bib_content:
            directory = os.path.dirname(file_path)
            main_bbl = os.path.join(directory, "main.bbl")

            if os.path.exists(main_bbl):
                self.logger.info("Bib fallback -> Found main.bbl")
                with open(main_bbl, "r") as f:
                    bib_content = f.read()
            else:
                # Look for any .bbl file
                bbl_files = [f for f in os.listdir(directory) if f.endswith(".bbl")]
                if bbl_files:
                    first_bbl = os.path.join(directory, bbl_files[0])
                    self.logger.info(f"Bib fallback -> Found {bbl_files[0]}")
                    with open(first_bbl, "r") as f:
                        bib_content = f.read()

        if bib_content:
            return self.parse(bib_content)
        else:
            self.logger.warning(f"Bibliography file not found: {file_path}")
            return []


if __name__ == "__main__":
    parser = BibParser()

    # # For BibTeX content
    # bibtex_content = """
    # @article{key1,
    # title={Some Title},
    # author={Author Name},
    # year={2023}
    # }
    # """
    # entries = parser.parse(bibtex_content)
    # print(entries)

    # For bibitem content
    bibitem_content = r"""
		\datalist[entry]{none/global//global/global}
  \entry{pinto2016supersizing}{misc}{}
    \name{author}{2}{}{%
      {{hash=PL}{%
         family={Pinto},
         familyi={P\bibinitperiod},
         given={Lerrel},
         giveni={L\bibinitperiod},
      }}%
      {{hash=GA}{%
         family={Gupta},
         familyi={G\bibinitperiod},
         given={Abhinav},
         giveni={A\bibinitperiod},
      }}%
    }
    \strng{namehash}{PLGA1}
    \strng{fullhash}{PLGA1}
    \field{labelnamesource}{author}
    \field{labeltitlesource}{title}
    \verb{eprint}
    \verb 1509.06825
    \endverb
    \field{title}{Supersizing Self-supervision: Learning to Grasp from 50K Tries and 700 Robot Hours}
    \field{eprinttype}{arXiv}
    \field{eprintclass}{cs.LG}
    \field{year}{2015}
  \endentry
  \enddatalist
    """
    entries = parser.parse(bibitem_content)
    print(entries)
