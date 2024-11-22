from src.latex_maps._uni2latexmap import uni2latex
from src.latex_maps._uni2latexmap_xml import uni2latex as uni2latex_xml

latex2unicode = {}

for k, v in uni2latex.items():
    latex2unicode[v] = k

for k, v in uni2latex_xml.items():
    latex2unicode[v] = k

if __name__ == "__main__":
    
    commands = [
        '\\textbackslash',
        '\\textdollar',
        '\\textcent',
        '\\textsterling',
        '\\textcurrency',
        '\\textyen',
        '\\textbrokenbar',
        '\\textsection',
        '\\textasciicircum',
        '\\H{O}'
    ]

    for cmd in commands:
        print(cmd, "->", chr(latex2unicode[cmd]))
