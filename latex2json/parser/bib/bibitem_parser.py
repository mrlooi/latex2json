import re
from typing import List
import logging
from latex2json.parser.bib.bibtex_parser import BibTexEntry


class BibItemParser:
    BibItemPattern = re.compile(
        r"\\bibitem\s*(?:\[(.*?)\])?\s*\{(.*?)\}\s*([\s\S]*?)(?=\\bibitem|$)",
        re.DOTALL,
    )
    NewblockPattern = re.compile(r"\\newblock\b")

    def __init__(self, logger: logging.Logger = None):
        self.logger = logger or logging.getLogger(__name__)

    def can_handle(self, content: str) -> bool:
        # Check for bibliography environment
        if re.search(r"\\begin{(\w*bibliography)}.*?\\end{\1}", content, re.DOTALL):
            return True
        # Check for standalone bibitems (existing logic)
        return bool(re.search(r"\\bibitem", content))

    def parse(self, content: str) -> List[BibTexEntry]:
        # If content is in bibliography environment, extract the content
        bib_match = re.search(
            r"\\begin{(\w*bibliography)}(.*?)\\end{\1}", content, re.DOTALL
        )
        if bib_match:
            content = bib_match.group(2)

        entries = []
        previous_content = None
        bysame_pattern = re.compile(r"\\bysame\b")

        for match in self.BibItemPattern.finditer(content):
            item = match.group(3).strip()
            if item:
                # remove newblock
                item = self.NewblockPattern.sub("", item)

                # Handle \bysame by replacing it with content from previous entry
                if previous_content and bysame_pattern.search(item):
                    # Extract author part from previous entry (up to first comma)
                    author_part = previous_content.split(",")[0]
                    if author_part:
                        item = bysame_pattern.sub(author_part, item)

                entry = BibTexEntry(
                    citation_key=match.group(2).strip(),
                    content=item,
                    label=match.group(1).strip() if match.group(1) else None,
                    entry_type="bibitem",
                    format="bibitem",
                    fields={},
                )
                entries.append(entry)
                previous_content = item
        return entries
