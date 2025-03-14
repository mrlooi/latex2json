# LaTeX2JSON Parser

A python package for parsing LaTeX (.tex) files into structured JSON output.

Currently supports a wide variety of latex papers on arxiv.

This parser focuses on extracting document content rather than preserving LaTeX's visual format:

- While the semantic structure (sections, equations, etc.) is maintained, layout-specific elements like page formatting, column arrangements, and table styling are not represented in the JSON output.
- Section, figure, table and equation counters etc may deviate from the original latex implementation.
- Text formatting is preserved as much as possible.

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

### Testing

```bash
pytest tests/
```

## Quick Start

```python
from latex2json.tex_reader import TexReader

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
