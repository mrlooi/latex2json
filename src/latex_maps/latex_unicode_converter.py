import re
from collections import OrderedDict
from src.latex_maps._uni2latexmap import uni2latex
from src.latex_maps._uni2latexmap_xml import uni2latex as uni2latex_xml

class LatexUnicodeConverter:
    def __init__(self):
        self.latex2unicode = self._create_latex_to_unicode_map()
        self.patterns = self._create_categorized_regex_patterns()

    def _create_latex_to_unicode_map(self):
        latex2unicode = OrderedDict()
        
        for k, v in uni2latex_xml.items():
            latex2unicode[v] = k
        
        for k, v in uni2latex.items():
            if v in latex2unicode:
                continue
            # ignore ensuremath
            if not v.startswith('\\ensuremath'):
                latex2unicode[v] = k
            
        return latex2unicode

    def _create_categorized_regex_patterns(self):
        patterns = {
            'ensuremath': [],
            'text': [],
            'math': [],
            'font': [],
            'other': []
        }
        
        # Categorize each command
        for cmd in self.latex2unicode.keys():
            if not cmd.startswith('\\') and not cmd.startswith('{'):
                continue
            
            # Add word boundary after the command to prevent partial matches
            escaped = re.escape(cmd)
            if not escaped.endswith('}'):
                escaped += r'(?![a-zA-Z])'
            if cmd.startswith('\\ensuremath'):
                patterns['ensuremath'].append(escaped)
            elif cmd.startswith('\\text'):
                patterns['text'].append(escaped)
            elif cmd.startswith('\\math'):
                patterns['math'].append(escaped)
            elif 'font' in cmd:
                patterns['font'].append(escaped)
            else:
                patterns['other'].append(escaped)
        
        # Compile patterns for each category
        compiled_patterns = {}
        for category, pattern_list in patterns.items():
            if pattern_list:  # Only compile if we have patterns
                compiled_patterns[category] = re.compile('|'.join(pattern_list))
        
        return compiled_patterns

    def convert(self, text: str) -> str:
        result = text
        
        # Process in specific order: longer commands first
        for pattern in self.patterns.values():
            result = pattern.sub(
                lambda m: chr(self.latex2unicode[m.group(0)]), 
                result
            )
        
        return result


# Example usage
if __name__ == "__main__":
    converter = LatexUnicodeConverter()
    
    test_strings = [
        r"This is a test \textbackslash with Erd\H{o}s some commands",
        r"Multiple \textdollar \textyen symbols",
        r"\ensuremath{\succnsim}\oe\# ` \'{}A",
        "\\mathtt{0}\\mathbb{E}f",
        "{\\fontencoding{LELA}\\selectfont\\char40}",
        r'\v{l} \l \ij \o \O \L \Lerer',
        r'\H{o}'
    ]
    
    print()
    for text in test_strings:
        result = converter.convert(text)
        print(f"Original: {text}")
        print(f"Converted: {result}\n")