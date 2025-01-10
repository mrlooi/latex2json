from collections import OrderedDict
import re
from latex2json.latex_maps._uni2latexmap import uni2latex
from latex2json.latex_maps._uni2latexmap_xml import uni2latex as uni2latex_xml


if __name__ == "__main__":
    latex2unicode = OrderedDict()

    for k, v in uni2latex.items():
        v = v.strip()
        # strip out \\ensuremath{}
        if v.startswith("\\ensuremath{"):
            v = v[len("\\ensuremath{") : -1].strip()

        if v in latex2unicode:
            continue

        latex2unicode[v] = k

    for k, v in uni2latex_xml.items():
        if v in latex2unicode:
            continue
        latex2unicode[v] = k

    # # sort keys based on value
    # latex2unicode = OrderedDict(sorted(latex2unicode.items(), key=lambda x: x[1]))

    # Write the latex2unicode dictionary to a Python file
    with open("src/latex_maps/_latex2unicode_map.py", "w", encoding="utf-8") as f:
        f.write("# Generated mapping of LaTeX commands to Unicode code points\n\n")
        f.write("latex2unicode = {\n")
        for latex, unicode_char in latex2unicode.items():
            # ignore
            if not latex.startswith("\\") and not latex.startswith("{"):
                continue

            # hex_value = f"0x{unicode_char:04x}"
            # f.write(f"    {repr(latex)}: {hex_value},\n")
            f.write(f"    {repr(latex)}: {unicode_char},\n")
        f.write("}\n")
