# LaTeX2JSON Parser

A python package for parsing LaTeX files into structured token representations and JSON output.

This parser focuses on extracting document content rather than preserving LaTeX's visual formatting.

- While the semantic structure (sections, equations, etc.) is maintained, layout-specific elements like page formatting, column arrangements, and table styling are not represented in the JSON output.
- Section, figure, table and equation counters etc may deviate from the original latex implementation.
- Text formatting is preserved as much as possible.

Currently supports a wide variety of latex papers on arxiv.

## Features

### Core Functionality

- Parse and process LaTeX documents from:
  - Single `.tex` files
  - Directory structures with multiple TeX files (automatically locates the main tex file)
  - Compressed archives (`.gz`, `.tar.gz`)

### Macro and nested environment processing

- Full macro expansion system:
  - Resolves `\newcommand`, `\def`, `\let` commands etc and rolls out all macros across nested content
- Advanced environment handling:
  - Nested environments support
  - Complex table structures i.e. tabular within tabular
  - Mathematical expressions and equations for inline/block/align etc

### Components

- Modular parsing system with specialized components:
  - Bibliography parsing (`bib_parser.py`) # handles .bib and .bbl files
  - Style file parsing (`sty_parser.py`) # handles .sty files
- Clean JSON output generation

## Installation

### Requirements

Python 3.7 or higher

```bash
pip install -r requirements.txt
```

## Quick Start

```python
from latex2json.tex_reader import TexReader

# Initialize the parser
tex_reader = TexReader()

# Process a regular TeX file/folder
result = tex_reader.process_folder("/path/to/folder")
# Or process a compressed TeX file (supports .gz and .tar.gz)
result, temp_dir = tex_reader.process_compressed("path/to/paper.tar.gz")

# Convert to JSON
json_output = tex_reader.to_json(result)
```

## Tested Papers

This parser has been successfully tested on the following arxiv papers, including:

- [math/0503066] Stable signal recovery from incomplete and inaccurate measurements (Math/Numerical Analysis, 2006)
- [1509.05363] The Erdos discrepancy problem (Math/combinatorics, 2015)
- [hep-th/0603057] Dynamics of dark energy (Physics/High Energy Physics, 2006)
- [1706.03762v7] Attention is all you need (AI/ML, 2017)
- [2303.08774v6] GPT-4 Technical Report (AI/ML, 2023)
- [2301.10945v1] A Fully First-Order Method for Stochastic Bilevel Optimization (Computer Science/Optimization, 2023)
- [1907.11692v1] RoBERTa: A Robustly Optimized BERT Pretraining Approach (AI/ML, 2019)
- [1712.01815v1] Mastering Chess and Shogi by Self-Play with a General Reinforcement Learning Algorithm (AI/ML, 2017) # limitations on /chess related commands
- [2304.02643] Segment Anything (Computer Vision, 2023) # limitations on /pgf... and /draw commands

And many more across math, physics, and computer science.

You may view some of the JSON outputs in [arxiv latex2json samples](https://drive.google.com/drive/u/5/folders/1lZTWIq5q_vjMs5GUScuvdDjnktpXRajV)

## Limitations

- Does not currently support specialized LaTeX drawing commands and environments (e.g., `\draw`, TikZ diagrams, Chess commands et). Treats them as unknown command tokens i.e. type: "command"
- May not handle certain custom or non-standard LaTeX packages fully
- Does not preserve latex visual formatting and counters

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

For more detailed examples of the output structure, see the expected test output in `tests/structure/test_builder.py`.

## License

This project is licensed under the MIT License - see the [LICENSE.txt](LICENSE.txt) file for details.
