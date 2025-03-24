# LaTeX2JSON Parser

A python package for parsing LaTeX (.tex) files into structured JSON output. Simplifies LaTeX content into basic semantic tokens (sections, equations, tables, etc.) and hierarchy, focusing on content extraction rather than visual formatting (see [sample output](#output-structure) and all [token types](#token-types))

## Table of Contents

- [Features](#features)
- [Installation](#installation)
- [Quick Start](#quick-start)
  - [Read from .tex files/folders/gz](#read-directly-from-tex-filesfoldersgz)
- [Output Structure](#output-structure)
  - [Token Types](#token-types)
- [Tested Papers](#tested-papers)
- [Limitations](#limitations)
- [Contributions](#contributions)
- [MIT License](#license)

Currently supports a wide variety of latex papers on arxiv.

This parser focuses on extracting document content rather than preserving LaTeX's visual format:

- While the semantic structure (sections, equations, etc.) is maintained, layout-specific elements like page formatting, column arrangements, and table styling are not represented in the JSON output.
- Section, figure, table and equation counters etc may deviate from the original latex implementation.
- Text formatting is preserved as much as possible.

## Features

### Core functionality

- Complex nested macro handling:
  - Correct parameter substitution in nested definitions
  - Proper scoping of redefined commands
- Rich table support:
  - Multi-row/multi-column cells
  - Mixed content (text, math, citations)
  - Styling and formatting within cells
- Bibliography features:
  - Citations with titles/notes
  - Multiple citation handling
- Comprehensive math mode support:
  - Complex mathematical constructs
  - Special operators and delimiters
- Text styling and colors:
  - Color definitions and scoping
  - Mixed styling within environments

### Macro and nested environment processing

- Full macro expansion system:
  - Resolves `\newcommand`, `\def`, `\let`, `\renewcommand`, `\csname` and other command definitions
  - Expands all macros recursively across nested content
  - Maintains proper scoping for redefined commands
  - Handles complex parameter substitution (e.g. `##1` in nested definitions)
  - Supports both starred and non-starred command variants
  - Processes command defaults and optional arguments
- Advanced environment handling:
  - Nested environments support
  - Complex table structures i.e. tabular within tabular
  - Mathematical expressions and equations for inline/block/align etc

### Components

- Modular parsing system with specialized components:
  - Bibliography parsing (`bib_parser.py`) # handles .bib and .bbl files
  - Style file parsing (`sty_parser.py`) # handles .sty files
- Clean JSON output generation (`structure/builder.py`)

## Installation

### From GitHub

```bash
pip install git+https://github.com/mrlooi/latex2json.git
```

### Or from Source

1. Clone the repository

```bash
git clone https://github.com/mrlooi/latex2json.git
cd latex2json
```

2. Install requirements

```bash
pip install -r requirements.txt
```

### Requirements

Python 3.7 or higher

### Testing

```bash
pytest tests/
```

## Quick Start

```python
from latex2json import LatexParser

parser = LatexParser()

latex_text = r"""
  % refer to tests/parser/test_parser.py for examples

  \newcommand{\outermacro}[2]{
      Outer parameters: #1 and #2

      \newcommand{\innermacro}[2]{
            Outer-inner parameters: #1 and #2
            Inner parameters: ##1 and ##2
      }
      \innermacro{inner-first}{inner-second}
  }

  \outermacro{outer-first}{outer-second}
"""

tokens = parser.parse(latex_text)


# [Optional]: organize the tokens into hierarchies e.g. \subsection under \section content, add counter numbers and validation
from latex2json import TokenBuilder

token_builder = TokenBuilder()
structured_tokens = token_builder.build(tokens)
```

Refer to [tests/parser/test_parser.py](tests/parser/test_parser.py) for examples

## Output Structure

The parser generates a structured JSON output that preserves the document hierarchy. Here's a simplified example:

```json
[
  {
    "type": "title",
    "title": [{ "type": "text", "content": "My Title" }]
  },
  {
    "type": "document",
    "content": [
      {
        "type": "abstract",
        "content": [{ "type": "text", "content": "This is my abstract" }]
      },
      {
        "type": "section",
        "title": [{ "type": "text", "content": "Introduction" }],
        "level": 1,
        "numbering": "1",
        "content": [
          { "type": "text", "content": "Some text here", "styles": ["bold"] },
          {
            "type": "equation",
            "content": "E = mc^2",
            "display": "block",
            "numbering": "1"
          }
        ]
      }
    ]
  }
]
```

For more detailed examples of the output structure, see the expected test output in [tests/structure/test_builder.py](tests/structure/test_builder.py).

### Token Types

The parser organizes latex tokens into the following token types:

#### Document Structure

- `document` - Root document container
- `title` - Document title
- `section` - Section headers (includes subsections)
- `paragraph` - Text paragraphs
- `abstract` - Document abstract
- `appendix` - Appendix sections

#### Content Elements

- `text` - Plain text content with optional styling
- `quote` - Quoted text content
- `equation` - Mathematical equations (inline or block)
- `figure` - Figure environments
- `table` - Table environments
- `tabular` - Table content structure
- `includegraphics` - Image inclusion commands
- `includepdf` - PDF inclusion commands
- `caption` - Captions for figures and tables
- `list` - Enumerated or itemized lists
- `item` - List items
- `code` - Code blocks
- `algorithm` - Algorithm environments
- `algorithmic` - Algorithmic content

#### Environment Types

- `environment` - Generic LaTeX environments
- `math_env` - Mathematical environments

#### References

- `citation` - Bibliography citations
- `ref` - Cross-references
- `url` - URL links
- `footnote` - Footnote content
- `bibliography` - Bibliography section
- `bibitem` - Bibliography entries

#### Metadata

- `author` - Author information
- `email` - Email addresses
- `affiliation` - Author affiliations
- `keywords` - Document keywords
- `address` - Address information

#### Other

- `command` - Generic LaTeX commands (unsuccessfully parsed)
- `group` - Grouped content

For detailed type definitions, see [latex2json/structure/tokens/types.py](latex2json/structure/tokens/types.py)

## Read directly from .tex files/folders/gz

```python
from latex2json import TexReader

# Initialize the parser
tex_reader = TexReader()

# Process a regular TeX file/folder
result = tex_reader.process("/path/to/folder_or_file")
# Or process a compressed TeX file (supports .gz and .tar.gz)
result, temp_dir = tex_reader.process("path/to/paper.tar.gz")

# Convert to JSON
json_output = tex_reader.to_json(result)
```

## Tested Papers

This parser has been successfully tested on the following arxiv papers, including:

- [1706.03762v7] Attention is all you need (AI/ML, 2017)
- [2303.08774v6] GPT-4 Technical Report (AI/ML, 2023)
- [1509.05363] The Erdos discrepancy problem (Math/combinatorics, 2015)
- [2501.12948] DeepSeek-R1: Incentivizing Reasoning Capability in LLMs via Reinforcement Learning (AI/ML, 2025)
- [hep-th/0603057] Dynamics of dark energy (Physics/High Energy Physics, 2006)
- [2307.09288v2] Llama 2: Open Foundation and Fine-Tuned Chat Models (AI/ML, 2023)
- [1703.06870] Mask R-CNN (Computer Vision, 2017)
- [2301.10945v1] A Fully First-Order Method for Stochastic Bilevel Optimization (Computer Science/Optimization, 2023)
- [1907.11692v1] RoBERTa: A Robustly Optimized BERT Pretraining Approach (AI/ML, 2019)
- [math/0503066] Stable signal recovery from incomplete and inaccurate measurements (Math/Numerical Analysis, 2006)
- [1712.01815v1] Mastering Chess and Shogi by Self-Play with a General Reinforcement Learning Algorithm (AI/ML, 2017) # limitations on /chess related commands
- [2304.02643] Segment Anything (Computer Vision, 2023) # limitations on /pgf... and /draw commands

And many more across math, physics, and computer science.

You may view some of the JSON outputs in [arxiv latex2json samples](https://drive.google.com/drive/u/5/folders/1lZTWIq5q_vjMs5GUScuvdDjnktpXRajV)

## Limitations

At its core, this parser uses regex-based parsing rather than a full TeX engine tokenization approach.
This makes it simpler to implement and faster for processing, but also less robust for handling complex TeX primitives and edge cases.

- Limited support for complex or legacy macro definitions, particularly those using advanced TeX primitives
- Simplified if-else handling: processes only the first conditional branch for most \if commands
- Does not currently support specialized LaTeX drawing commands and environments (e.g., `\draw`, TikZ diagrams, Chess commands et). Treats them as unknown command tokens i.e. type: "command"
- May not handle certain custom or non-standard LaTeX packages fully
- Does not preserve latex visual formatting and counters

## Contributions

Contributions to improve LaTeX2JSON are welcome! Here are some areas where help is needed:

1. **Drawing Package Support**

   - Implementing support for TikZ, PGF, and other drawing packages

2. **cls/sty Processing**

   - Improving handling of `.cls` and `.sty` files
   - Better support for complex `@if` conditionals and LaTeX internals
   - Expanding macro resolution capabilities (e.g. currently \noexpand or \expandafter are ignored)

3. **Additional commands from various packages**

   - If you find a command that is not supported, please feel free to add them!

### How to Contribute

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/some-feature`)
3. Commit your changes (`git commit -m 'Add some feature'`)
4. Push to the branch (`git push origin feature/some-feature`)
5. Open a Pull Request

Please ensure your PR includes:

- A clear description of the changes
- Updated tests where applicable

## License

This project is licensed under the MIT License - see the [LICENSE.txt](LICENSE.txt) file for details.
