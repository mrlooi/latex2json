import re
from collections import OrderedDict
from typing import Callable, Dict, Optional, Tuple
from src.handlers.base import TokenHandler
from src.tex_utils import extract_nested_content
from src.patterns import SECTION_LEVELS

# ASSUMES ORDERD DICT (PYTHON 3.7+)
RAW_PATTERNS = OrderedDict([
    # 1. Commands that need nested brace handling (simplified patterns)
    ('section', r'\\(?:(?:sub)*section\*?)\s*{'),
    ('paragraph', r'\\(?:(?:sub)*paragraph\*?)\s*{'),
    ('part', r'\\part\*?\s*{'),
    ('chapter', r'\\chapter\*?\s*{'),
    ('footnote', r'\\footnote\s*{'),
    ('caption', r'\\caption\s*{'),
    ('captionof', r'\\captionof\s*{([^}]*?)}\s*{'),
    ('hyperref', r'\\hyperref\s*\[([^]]*)\]\s*{'),
    ('href', r'\\href\s*{([^}]*)}\s*{'),

    # Simple commands
    ('ref', r'\\ref\s*{'),
    ('cref', r'\\cref\s*{'), 
    ('autoref', r'\\autoref\s*{'),
    ('eqref', r'\\eqref\s*{'),
    ('url', r'\\url\s*{'),
    ('includegraphics', r'\\includegraphics\s*(?:\[([^\]]*)\])?\s*{'),
    
    # Citations
    ('citation', r'\\(?:cite|citep|citet)(?:\[([^\]]*)\])?\s*{'),
])

# compile them
PATTERNS = OrderedDict(
    (key, re.compile(pattern, re.DOTALL))
    for key, pattern in RAW_PATTERNS.items()
)

class ContentCommandHandler(TokenHandler):
    def can_handle(self, content: str) -> bool:
        return any(pattern.match(content) for pattern in PATTERNS.values())
    
    def handle(self, content: str) -> Tuple[Optional[Dict], int]:
        # Try each pattern until we find a match
        for pattern_name, pattern in PATTERNS.items():
            match = pattern.match(content)
            if match:
                # Get position after command name
                start_pos = match.end()
                
                # Extract content between braces
                nested_content, end_pos = extract_nested_content(content[start_pos - 1:])
                if nested_content is None:
                    return None, start_pos
                
                # Adjust end position
                end_pos = start_pos + end_pos - 1  # move back one to account for start_pos -1
                
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
        
        if matched_type in ['section', 'paragraph', 'chapter', 'part']:
            level = match.group(0).count('sub') + SECTION_LEVELS[matched_type]
            return {
                "type": 'section',
                "title": content,
                "level": level
            }
        
        elif matched_type == 'caption':
            return {
                "type": "caption",
                "content": content
            }
        
        elif matched_type == 'captionof':
            return {
                "type": "caption",
                "title": match.group(1).strip(),
                "content": content
            }
        
        elif matched_type == 'footnote':
            return {
                "type": "footnote",
                "content": content  # Note: caller should parse this content for environments
            }
        
        elif matched_type == 'hyperref':
            return {
                "type": "ref",
                "title": match.group(1).strip(),
                "content": content
            }
        
        elif matched_type == 'href':
            return {
                "type": "url",
                "title": content,
                "content": match.group(1).strip()
            }
        
        elif matched_type in ['ref', 'eqref', 'cref', 'autoref']:
            return {
                "type": "ref",
                "content": content
            }
        
        elif matched_type == 'citation':
            token = {
                "type": "citation",
                "content": content
            }
            optional_text = match.group(1) if match.group(1) else None
            if optional_text:
                token["title"] = optional_text.strip()
            return token
        
        elif matched_type == 'includegraphics':
            return {
                "type": "includegraphics",
                "content": content
            }
        
        elif matched_type == 'url':
            return {
                "type": "url",
                "content": content
            }
        
        return None

if __name__ == "__main__":
    handler = ContentCommandHandler()
    print(handler.handle(r"\section{{hello world}}"))