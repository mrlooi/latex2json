import re
from collections import OrderedDict
from typing import Callable, Dict, Optional, Tuple
from src.handlers.base import TokenHandler
from src.tex_utils import extract_nested_content
from src.patterns import SECTION_LEVELS

RAW_PATTERNS = OrderedDict(
    [
        # 1. Commands that need nested brace handling (simplified patterns)
        ("abstract", r"\\[Aa]bstract\s*{"),
        ("section", r"\\(?:(?:sub)*section\*?)\s*{"),
        ("paragraph", r"\\(?:(?:sub)*paragraph\*?)\s*{"),
        ("part", r"\\part\*?\s*{"),
        ("chapter", r"\\chapter\*?\s*{"),
        ("footnote", r"\\footnote\s*{"),
        ("caption", r"\\caption\s*{"),
        ("captionof", r"\\captionof\s*{([^}]*?)}\s*{"),
        # input
        ("input", r"\\(?:input|include)\s*{"),
        # REFs
        ("ref", r"\\(?:[Cc]|[Aa]uto|eq|page)?[Rr]ef\*?\s*{"),
        ("hyperref", r"\\hyperref\s*\[([^]]*)\]\s*{"),
        ("href", r"\\href\s*{([^}]*)}\s*{"),
        # bookmarks (similar to refs?)
        ("bookmark", r"\\bookmark\s*(?:\[([^\]]*)\])?\s*{"),
        (
            "pdfbookmark",
            r"\\(?:below|current)?pdfbookmark\s*(?:\[([^\]]*)\])?\s*{([^}]*)}\s*{",
        ),
        ("footnotemark", r"\\footnotemark(?:\[([^\]]*)\])?"),
        # URLs
        ("url", r"\\url\s*{"),
        # Graphics
        ("includegraphics", r"\\includegraphics\s*(?:\[([^\]]*)\])?\s*{"),
        ("graphicspath", r"\\graphicspath\s*{"),  # ignore?
        # Citations
        (
            "citation",
            r"\\(?:(?:[Cc])(?:ite|itep|itet|itealt|itealp|iteauthor))(?:\[([^\]]*)\])?\s*{",
        ),
        # Citations with just braces
        ("citetext", r"\\(?:citetext|citenum)\s*{"),
        # Citations with two braces
        ("defcitealias", r"\\defcitealias\s*{([^}]*)}\s*{"),
        # Citations with optional brackets (year/author specific)
        ("citeyear", r"\\(?:citeyear|citeyearpar|citefullauthor)(?:\[([^\]]*)\])?\s*{"),
        # Title
        ("title", r"\\title\s*{"),
        # appendix
        ("appendix", r"\\appendix\b"),
        # keywords
        ("keywords", r"\\keywords\s*{"),
        # bibliography
        ("bibliography", r"\\bibliography\s*{"),
    ]
)

# compile them
PATTERNS = OrderedDict(
    (key, re.compile(pattern, re.DOTALL)) for key, pattern in RAW_PATTERNS.items()
)


class ContentCommandHandler(TokenHandler):
    def can_handle(self, content: str) -> bool:
        return any(pattern.match(content) for pattern in PATTERNS.values())

    def handle(self, content: str) -> Tuple[Optional[Dict], int]:
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

        if matched_type in ["section", "paragraph", "chapter", "part"]:
            level = match.group(0).count("sub") + SECTION_LEVELS[matched_type]
            numbered = (matched_type + "*") not in match.group(0)
            return {
                "type": "section",
                "title": content,
                "level": level,
                "numbered": numbered,
            }
        elif matched_type == "input":
            return {"type": "input", "content": content}

        elif matched_type == "title":
            return {"type": "title", "title": content}

        elif matched_type == "caption":
            return {"type": "caption", "content": content}

        elif matched_type == "captionof":
            return {
                "type": "caption",
                "title": match.group(1).strip(),
                "content": content,
            }

        elif matched_type == "footnote":
            return {
                "type": "footnote",
                "content": content,  # Note: caller should parse this content for environments
            }

        elif matched_type == "hyperref":
            return {"type": "ref", "title": match.group(1).strip(), "content": content}

        elif matched_type == "href":
            return {"type": "url", "title": content, "content": match.group(1).strip()}

        elif matched_type in ["ref", "bookmark"]:
            return {"type": "ref", "content": content}

        # Citations
        elif matched_type == "citation":
            token = {"type": "citation", "content": content}
            optional_text = match.group(1) if match.group(1) else None
            if optional_text:
                token["title"] = optional_text.strip()
            return token

        elif matched_type == "citetext":
            return {"type": "citation", "content": content}

        elif matched_type == "defcitealias":
            return {
                "type": "citation",
                "content": match.group(1).strip(),
                "alias": content,
            }

        elif matched_type == "citeyear":
            token = {"type": "citation", "subtype": "year", "content": content}
            optional_text = match.group(1) if match.group(1) else None
            if optional_text:
                token["title"] = optional_text.strip()
            return token

        elif matched_type == "includegraphics":
            return {"type": "includegraphics", "content": content}

        elif matched_type == "url":
            return {"type": "url", "content": content}

        elif matched_type == "pdfbookmark":
            return {
                "type": "ref",
                "title": match.group(2).strip(),  # The display text
                "content": content,  # The internal reference label
            }

        elif matched_type == "graphicspath":
            return None

        return {"type": matched_type, "content": content}


if __name__ == "__main__":
    handler = ContentCommandHandler()
    print(handler.handle(r"\section{{hello world}}"))
