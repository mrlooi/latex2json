import re
from collections import OrderedDict
from typing import Callable, Dict, Optional, Tuple
from latex2json.parser.handlers.base import TokenHandler
from latex2json.utils.tex_utils import extract_nested_content

SECTION_LEVELS = {
    "part": 0,
    "chapter": 1,
    "section": 1,
    "subsection": 2,
    "subsubsection": 3,
}

PARAGRAPH_LEVELS = {
    "paragraph": 1,
    "subparagraph": 2,
}

OPTIONAL_BRACE_PATTERN = r"(?:\[([^\]]*)\])?"

RAW_PATTERNS = OrderedDict(
    [
        # 1. Commands that need nested brace handling (simplified patterns)
        ("abstract", r"\\abstract\s*{"),
        ("section", r"\\(?:(?:sub)*section\*?)\s*{"),
        ("part", r"\\part\*?\s*{"),
        ("chapter", r"\\chapter\*?\s*{"),
        ("paragraph", r"\\(?:(?:sub)*paragraph\*?)\s*{"),
        ("footnote", r"\\footnote\*?\s*{"),
        ("caption", r"\\caption\*?\s*%s\s*{" % OPTIONAL_BRACE_PATTERN),
        ("captionof", r"\\captionof\*?\s*{([^}]*?)}\s*{"),
        # input
        ("input_file", r"\\(?:input|include)\s*{"),
        # REFs
        ("ref", r"\\(?:auto|eq|page)?ref\*?\s*{"),
        ("cref", r"\\[cC]ref\*?\s*{"),
        ("hyperref", r"\\hyperref\s*%s\s*{" % OPTIONAL_BRACE_PATTERN),
        ("href", r"\\href\s*{([^}]*)}\s*{"),
        # bookmarks
        ("bookmark", r"\\bookmark\s*%s\s*{" % OPTIONAL_BRACE_PATTERN),
        (
            "pdfbookmark",
            r"\\(?:below|current)?pdfbookmark\s*%s\s*{([^}]*)}\s*{"
            % OPTIONAL_BRACE_PATTERN,
        ),
        # footnotes
        ("footnotemark", r"\\footnotemark%s" % OPTIONAL_BRACE_PATTERN),
        ("footnotetext", r"\\footnotetext%s\s*{" % OPTIONAL_BRACE_PATTERN),
        # URLs
        ("url", r"\\(?:url|path)\s*{"),
        ("doi", r"\\doi\s*{"),
        # Graphics
        ("includegraphics", r"\\includegraphics\s*%s\s*{" % OPTIONAL_BRACE_PATTERN),
        ("includepdf", r"\\includepdf\s*%s\s*{" % OPTIONAL_BRACE_PATTERN),
        ("graphicspath", r"\\graphicspath\s*{"),  # ignore?
        # Citations
        (
            "citation",
            r"\\(?:cite|citep|citet|cites|citealt|citealp|citeauthor|citenum|citeyear|citeyearpar|citefullauthor)\s*%s%s\s*{"
            % (OPTIONAL_BRACE_PATTERN, OPTIONAL_BRACE_PATTERN),
        ),
        # ("citetext", r"\\citetext\s*{"), # remove citetext since it is just like regular latex -> handled by text_formatting
        # Cite alias
        ("defcitealias", r"\\defcitealias\s*{([^}]*)}\s*{"),
        ("citealias", r"\\cite[tp]alias\s*{"),
        # Title
        ("title", r"\\title\s*%s\s*{" % OPTIONAL_BRACE_PATTERN),
        # appendix
        ("appendix", r"\\(?:appendix|appendices)\b"),
        # keywords
        ("keywords", r"\\keywords\s*{"),
        # bibliography
        ("bibliography_file", r"\\(?:bibliography|addbibresource)\s*{"),
    ]
)

# compile them
PATTERNS = OrderedDict(
    (key, re.compile(pattern, re.DOTALL | re.IGNORECASE))
    for key, pattern in RAW_PATTERNS.items()
)

GENERIC_COMMAND_PATTERN = re.compile(r"\\[a-zA-Z]+\b")


class ContentCommandHandler(TokenHandler):
    citealias = {}  # key, alias/title

    def clear(self):
        self.citealias = {}

    def can_handle(self, content: str) -> bool:
        return any(pattern.match(content) for pattern in PATTERNS.values())

    def handle(
        self, content: str, prev_token: Optional[Dict] = None
    ) -> Tuple[Optional[Dict], int]:
        # Try each pattern until we find a match
        for pattern_name, pattern in PATTERNS.items():
            match = pattern.match(content)
            if match:
                if pattern_name == "footnotemark":
                    return {
                        "type": "footnote",
                        "content": match.group(1).strip() if match.group(1) else "*",
                    }, match.end()
                elif pattern_name == "appendix":
                    return {"type": "appendix"}, match.end()
                else:
                    # Get position after command name
                    start_pos = match.end()

                    # Extract content between braces
                    nested_content, end_pos = extract_nested_content(
                        content[start_pos - 1 :]
                    )
                    if nested_content is None:
                        return None, start_pos

                    # Adjust end position
                    end_pos = (
                        start_pos + end_pos - 1
                    )  # move back one to account for start_pos -1

                    # Expand any nested commands in the content
                    if self.process_content_fn:
                        nested_content = self.process_content_fn(nested_content)

                    # Create token based on command type
                    token = self._create_token(pattern_name, match, nested_content)

                    return token, end_pos

        return None, 0

    def _create_token(self, matched_type: str, match, content: str) -> Optional[Dict]:
        """Create appropriate token based on command type"""

        content = content.strip()

        if matched_type == "paragraph":
            level = match.group(0).count("sub") + PARAGRAPH_LEVELS["paragraph"]
            return {
                "type": "paragraph",
                "title": content,
                "level": level,
            }
        elif matched_type in ["section", "chapter", "part"]:
            level = match.group(0).count("sub") + SECTION_LEVELS[matched_type]
            numbered = (matched_type + "*") not in match.group(0)
            return {
                "type": "section",
                "title": content,
                "level": level,
                "numbered": numbered,
            }

        elif matched_type == "title":
            return {"type": "title", "content": content}

        elif matched_type == "captionof":
            return {
                "type": "caption",
                "title": match.group(1).strip(),
                "content": content,
            }

        elif matched_type == "footnote" or matched_type == "footnotetext":
            return {
                "type": "footnote",
                "content": content,  # Note: caller should parse this content for environments
            }

        # REFs
        elif matched_type == "ref":
            return {"type": "ref", "content": [content.strip()]}
        elif matched_type == "cref":
            return {"type": "ref", "content": [c.strip() for c in content.split(",")]}
        elif matched_type == "hyperref":
            return {
                "type": "ref",
                "title": content,
                "content": [match.group(1).strip()],
            }

        # URLs
        elif matched_type == "href":
            return {"type": "url", "title": content, "content": match.group(1).strip()}

        elif matched_type == "url":
            return {"type": "url", "content": content}

        elif matched_type == "doi":
            return {"type": "url", "content": "https://doi.org/" + content}

        # Citations
        elif matched_type == "citation":
            token = {
                "type": "citation",
                "content": [c.strip() for c in content.split(",")],
            }
            # Combine prenote and postnote into title if either exists
            prenote = match.group(1).strip() if match.group(1) else ""
            postnote = match.group(2).strip() if match.group(2) else ""
            if prenote or postnote:
                combined_note = ", ".join(filter(None, [prenote, postnote]))
                token["title"] = combined_note
            return token

        elif matched_type == "defcitealias":
            cite_key = match.group(1).strip()
            self.citealias[cite_key] = content
            return None

        elif matched_type == "citealias":
            cite_keys = [c.strip() for c in content.split(",")]
            tokens = []
            for cite_key in cite_keys:
                token = {
                    "type": "citation",
                    "content": [cite_key],
                }
                title = self.citealias.get(cite_key)
                if title:
                    token["title"] = title
                tokens.append(token)
            if len(tokens) == 1:
                return tokens[0]
            return tokens

        # GRAPHICS
        elif matched_type == "includegraphics":
            # Extract page number from the optional parameters if present
            options = match.group(1)
            page_number = None
            if options:
                page_match = re.search(r"page=(\d+)", options)
                page_number = int(page_match.group(1)) if page_match else None
                if page_number is not None:
                    return {
                        "type": "includegraphics",
                        "content": content,
                        "page": page_number,
                    }

            return {"type": "includegraphics", "content": content}
        elif matched_type == "includepdf":
            # Extract page range from the optional parameters if present
            options = match.group(1)
            pages = None
            if options:
                # Match both pages=1-3 and pages={1-3} formats
                pages_match = re.search(r"pages=(?:{([0-9-,]+)}|([0-9-,]+))", options)
                # Use first non-None group (either braced or unbraced match)
                pages = (
                    next((g for g in pages_match.groups() if g is not None), None)
                    if pages_match
                    else None
                )
                if pages:
                    return {
                        "type": "includepdf",
                        "content": content,
                        "pages": pages,
                    }

            return {"type": "includepdf", "content": content}

        elif matched_type == "graphicspath":
            return None

        # bookmarks
        elif matched_type == "pdfbookmark":
            return None
        elif matched_type == "bookmark":
            return None

        return {"type": matched_type, "content": content}

    def search(self, content: str):
        pos = 0
        while pos < len(content):
            search = re.search(GENERIC_COMMAND_PATTERN, content[pos:])
            if not search:
                return None

            current_pos = pos + search.start()
            for pattern_name, pattern in PATTERNS.items():
                if pattern.match(content[current_pos:]):
                    return current_pos

            pos += search.end()


if __name__ == "__main__":
    handler = ContentCommandHandler()
    print(handler.handle(r"\includepdf[pages={1-3}]{mypdf.pdf}"))
    print(handler.handle(r"\includepdf[pages=2]{mypdf.pdf}"))
    print(handler.handle(r"\includepdf{mypdf.pdf}"))
