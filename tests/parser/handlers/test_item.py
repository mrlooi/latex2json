import pytest
from src.parser.handlers.item import ItemHandler


@pytest.fixture
def handler():
    return ItemHandler()


def test_can_handle_item(handler):
    assert handler.can_handle(r"\item First item")
    assert handler.can_handle(r"\item[1.] First item")
    assert not handler.can_handle("regular text")


def test_basic_item(handler):
    content = r"\item First item"
    token, pos = handler.handle(content)

    assert token["type"] == "item"
    assert token["content"] == "First item"

    # Test with title
    content = r"\item[1.] First item"
    token, pos = handler.handle(content)

    assert token["type"] == "item"
    assert token["content"] == "First item"
    assert token["title"] == "1."


def test_multiple_items(handler):
    content = r"""
    \item First
    \item [] Second
    \item Third
    """.strip()

    # Test first item
    token, pos = handler.handle(content)
    assert token["content"] == "First"

    # Test second item
    remaining = content[pos:].strip()
    token, pos = handler.handle(remaining)
    assert token["content"] == "Second"

    # Test third item
    remaining = remaining[pos:].strip()
    token, pos = handler.handle(remaining)
    assert token["content"] == "Third"


def test_nested_environments(handler):
    content = r"""
    \item First item with nested list
    \begin{itemize}
    \item Nested item 1
    \item Nested item 2
    \end{itemize}
    \item Second item
    """.strip()

    token, pos = handler.handle(content)
    assert token["type"] == "item"
    assert "begin{itemize}" in token["content"]
    assert "Nested item 1" in token["content"]
    assert "Nested item 2" in token["content"]
    assert "end{itemize}" in token["content"]

    # Check that we can handle the next item
    remaining = content[pos:].strip()
    assert remaining.startswith(r"\item Second item")


def test_deeply_nested_environments(handler):
    content = r"""
    \item Top level

    \begin{enumerate}
    \item Level 1
    \begin{itemize}
    \item Level 2
    \end{itemize}
    \end{enumerate}

    The final straw
    \item Next top level
    """.strip()

    token, pos = handler.handle(content)
    assert token["type"] == "item"

    c = token["content"].strip()
    assert c.startswith("Top level")
    assert "begin{enumerate}" in c
    assert r"\item Level 1" in c
    assert "begin{itemize}" in c
    assert r"\item Level 2" in c
    assert "end{itemize}" in c
    assert "end{enumerate}" in c
    assert c.endswith("The final straw")

    remaining = content[pos:].strip()
    assert remaining.startswith(r"\item Next top level")


def test_realworld_case(handler):
    text = r"""
\item (The $\crt$ regions, for $R$ values sufficiently small relative to $T$) This is essentially \cref{Sob.emb}: apply the Sobolev embedding estimate \eqref{in-R-Sob} to $\phi_J$
\begin{align*}
\!  \| \p_J\|_{L^\infty(\crt)} 
  &\ls \sum_{i\le 1,j\le 2}
\f1{(R^3T)^{1/2}} \|S^i \xO^j \p_J\|_{L^2(\ti C^R_T)} 
   + 
\f1{R^{1/2} T^{1/2}} \|\pa_r S^i \xO^j  \p_J\|_{L^2(\ti C^R_T)} \\
&\ls \f1{T^{1/2}} \|\phi_{|J|\le\cdot\le|J|+k}\|_{LE^1[T,2T]},
\end{align*}
and take the supremum over, say, $R< 3T/8$. The second inequality comes from commuting $S^i\xO^j$ with $Z^J$ in a way that will put it in the form \cref{vf defn}. 
This is where the integer $k$ arises. 

\item (The $C^T_R$ regions)
 \eqref{R-Sob} implies
\begin{align*}
\| \phi_J \|_{L^\infty(C^T_R)} &\ls
\frac{1}{R^{1/2}} \sum_{i\le1, j \leq 2}
    \|R^{-3/2}S^i \xO^j \phi_J\|_{L^2(\ti C^T_R)} +\|R^{-1/2}\pat S^i \Omega^j  \phi_J\|_{L^2(\ti C^T_R)}\\
&\ls \f1{R^{1/2}} \sum_{i\le1,j\le2} \|S^i\xO^j \phi_J\|_{LE^1[T,2T]} \\
&\ls \f1{R^{1/2}} \|\p_{|J|\le\cdot\le|J|+k}\|_{LE^1[T,2T]}.
\end{align*}
Then we take the supremum over the relevant $R$ values. In $C^T_R$, we have $v\sim r$ and $u\sim r$.%
""".strip()

    token, pos = handler.handle(text)
    assert token["type"] == "item"
    c = token["content"].strip()
    assert c.startswith(r"(The $\crt$ regions")
    assert c.endswith("This is where the integer $k$ arises.")

    assert text[pos:].strip().startswith(r"\item (The $C^T_R$ regions)")

    text = text[pos:].strip()
    token, pos = handler.handle(text)
    assert token["type"] == "item"
    c = token["content"].strip()
    assert c.startswith(r"(The $C^T_R$ regions)")
    assert c.endswith(r"In $C^T_R$, we have $v\sim r$ and $u\sim r$.%")


if __name__ == "__main__":
    pytest.main([__file__])
