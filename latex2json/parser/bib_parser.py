from dataclasses import dataclass
from logging import Logger
import logging
from typing import Dict, List, Optional
import re
from latex2json.utils.tex_utils import extract_nested_content, strip_latex_comments
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


class BibTexParser:
    def __init__(self, logger: Logger = None):
        self.logger = logger or logging.getLogger(__name__)

    def parse(self, content: str) -> List[BibEntry]:
        """Parse BibTeX content and return list of BibEntry objects"""
        self.logger.info("Starting BibTeX parsing")
        entries = []
        pos = 0

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

        content = strip_latex_comments(content).strip()

        entries = []

        # Check if content has bibliography environment
        bib_env_pattern = r"\\begin{(\w*bibliography)}(.*?)\\end{\1}"
        bib_env_match = re.search(bib_env_pattern, content, re.DOTALL)

        if bib_env_match:
            self.logger.debug("Parsing bibliography environment content")
            bib_content = bib_env_match.group(2)
            entries.extend(self._parse_bibitems(bib_content))
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
        for match in BibItemPattern.finditer(content):
            item = match.group(3).strip()
            if item:
                # remove newblock
                item = NewblockPattern.sub("", item)

                entry = BibEntry(
                    citation_key=match.group(2).strip(),
                    content=item,
                    title=match.group(1).strip() if match.group(1) else None,
                    entry_type="bibitem",
                    fields={},
                )
                entries.append(entry)
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

        # Case 3: Try main.bbl in the same directory as file_path
        if not bib_content:
            directory = os.path.dirname(file_path)
            main_bbl = os.path.join(directory, "main.bbl")
            if os.path.exists(main_bbl):
                self.logger.info(f"Bib fallback -> Found main.bbl")
                with open(main_bbl, "r") as f:
                    bib_content = f.read()

        if bib_content:
            return self.parse(bib_content)
        else:
            self.logger.warning(f"Bibliography file not found: {file_path}")
            return []


if __name__ == "__main__":
    parser = BibParser()

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

    # For bibitem content
    bibitem_content = r"""
    \begin{thebibliography}{1}
    \bibitem[Title 1]{key1} Some content here
    \bibitem{key2} More content here
    \end{thebibliography}
    """
    entries = parser.parse(bibitem_content)
    print(entries)
