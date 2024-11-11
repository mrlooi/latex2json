from pylatexenc.latexwalker import LatexWalker
from pylatexenc.latex2text import LatexNodes2Text

text =  """
    \\begin{lemma}\\label{tb} With probability $1-O(\\eps)$, one has 
    \\begin{equation}\\label{t-bound}
    \\t = O_{\\eps}(X^\\delta).
    \\end{equation}
    \\end{lemma}
"""
w = LatexWalker(text)
(nodelist, pos, len_) = w.get_latex_nodes(pos=0)
# print(nodelist)

x = LatexNodes2Text().latex_to_text(text)