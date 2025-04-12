from logging import Logger
import logging
import os
from typing import List

from latex2json.parser.bib.bibtex_parser import (
    BibTexEntry,
    BibTexParser,
)
from latex2json.parser.bib.bibdiv_parser import BibDivParser
from latex2json.parser.bib.bibitem_parser import BibItemParser
from latex2json.utils.tex_utils import (
    strip_latex_comments,
    normalize_whitespace_and_lines,
)


def preprocess(content: str) -> str:
    """Preprocess content to remove comments and normalize whitespace"""
    content = strip_latex_comments(content)
    content = normalize_whitespace_and_lines(content)
    return content.strip()


class BibParser:

    # _parsed_files = set()

    def __init__(self, logger: logging.Logger = None):
        # for logging
        self.logger = logger or logging.getLogger(__name__)

        self.bibtex_parser = BibTexParser(logger=self.logger)
        self.bibdiv_parser = BibDivParser(logger=self.logger)
        self.bibitem_parser = BibItemParser(logger=self.logger)

    def clear(self):
        pass
        # self._parsed_files = set()

    def parse(self, content: str) -> List[BibTexEntry]:
        """Parse both BibTeX, bibitem, and bibdiv entries from the content"""

        content = preprocess(content)

        entries = []

        # Check for bibdiv environment first
        if self.bibdiv_parser.can_handle(content):
            self.logger.debug("Parsing bibdiv environment content")
            entries.extend(self.bibdiv_parser.parse(content))
        # Use the can_handle method for BibTeX
        elif self.bibtex_parser.can_handle(content):
            entries.extend(self.bibtex_parser.parse(content))
        # Use the can_handle method for BibItem (now includes bibliography environment check)
        elif self.bibitem_parser.can_handle(content):
            self.logger.debug("Parsing bibitem content")
            entries.extend(self.bibitem_parser.parse(content))
        else:
            self.logger.warning("No suitable parser found for the content")
            return []

        return entries

    def _open_file(self, file_path: str) -> str | None:
        # if file_path in self._parsed_files:
        #     self.logger.warning(f"BibParser: Already parsed {file_path}")
        #     return None
        # self._parsed_files.add(file_path)
        with open(file_path, "r") as f:
            return f.read()

    def parse_file(self, file_path: str) -> List[BibTexEntry]:
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
            bib_content = self._open_file(file_path)

        # Case 2: Need to try adding extensions
        else:
            for ext in exts:
                full_path = file_path + ext
                if os.path.exists(full_path):
                    bib_content = self._open_file(full_path)
                    break

        # Case 3: Try main.bbl first, then any .bbl file in the same directory
        if not bib_content:
            directory = os.path.dirname(file_path)
            main_bbl = os.path.join(directory, "main.bbl")

            if os.path.exists(main_bbl):
                self.logger.info("Bib fallback -> Found main.bbl")
                bib_content = self._open_file(main_bbl)
            else:
                # Look for any .bbl file
                bbl_files = [f for f in os.listdir(directory) if f.endswith(".bbl")]
                if bbl_files:
                    first_bbl = os.path.join(directory, bbl_files[0])
                    self.logger.info(f"Bib fallback -> Found {bbl_files[0]}")
                    bib_content = self._open_file(first_bbl)

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
