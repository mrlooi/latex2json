from logging import Logger
import logging
import re
import os
from typing import List

from latex2json.parser.bib.compiled_bibtex import (
    is_compiled_bibtex,
    process_compiled_bibtex_to_bibtex,
)
from latex2json.parser.bib.bibtex_parser import (
    BibEntry,
    BibTexParser,
    preprocess,
    BibTexPattern,
)
from latex2json.parser.bib.bibdiv_parser import BibDivParser, BibDivPattern

BibItemPattern = re.compile(
    r"\\bibitem\s*(?:\[(.*?)\])?\s*\{(.*?)\}\s*([\s\S]*?)(?=\\bibitem|$)",
    re.DOTALL,
)
NewblockPattern = re.compile(r"\\newblock\b")


class BibParser:
    def __init__(self, logger: logging.Logger = None):
        # for logging
        self.logger = logger or logging.getLogger(__name__)

        self.bibtex_parser = BibTexParser(logger=self.logger)
        self.bibdiv_parser = BibDivParser(logger=self.logger)

    def clear(self):
        pass

    def parse(self, content: str) -> List[BibEntry]:
        """Parse both BibTeX, bibitem, and bibdiv entries from the content"""

        content = preprocess(content)

        entries = []

        # Check for bibdiv environment first
        if BibDivParser.is_bibdiv(content):
            self.logger.debug("Parsing bibdiv environment content")
            entries.extend(self.bibdiv_parser.parse(content))
        # Check if content has bibliography environment
        elif re.search(r"\\begin{(\w*bibliography)}(.*?)\\end{\1}", content, re.DOTALL):
            self.logger.debug("Parsing bibliography environment content")
            bib_content = re.search(
                r"\\begin{(\w*bibliography)}(.*?)\\end{\1}", content, re.DOTALL
            ).group(2)
            entries.extend(self._parse_bibitems(bib_content))
        elif is_compiled_bibtex(content):
            self.logger.debug("Parsing compiled BibTeX content")
            # first convert to bibtex format
            bibtex_content = process_compiled_bibtex_to_bibtex(content)
            entries.extend(self.bibtex_parser.parse("\n".join(bibtex_content)))
        elif BibTexParser.is_bibtex(content):
            entries.extend(self.bibtex_parser.parse(content))
        else:
            self.logger.debug("Parsing standalone bibitem content")
            entries.extend(self._parse_bibitems(content))

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
            self.logger.info(f"BibParser: Parsing {file_path}")
            entries = self.parse(bib_content)
            if len(entries) == 0:
                self.logger.warning(f"BibParser: No entries found in {file_path}")
            else:
                self.logger.info(
                    f"Finished BibParser: {file_path} -> Found {len(entries)} entries"
                )
            return entries
        else:
            self.logger.warning(f"Bibliography file not found: {file_path}")
            return []


if __name__ == "__main__":
    parser = BibParser()

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
