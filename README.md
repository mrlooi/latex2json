# LaTeX Document Parser

A Python-based tool for parsing and converting TeX files into structured token representations and JSON output.

## Features

- Parse regular `.tex` files and compressed archives containing TeX documents
- Convert LaTeX documents into structured token representations
- Export parsing results to JSON format
- Support for various LaTeX components through specialized parsers:
  - Bibliography parsing (`bib_parser.py`)
  - Style parsing (`sty_parser.py`)
  - Pattern matching (`patterns.py`)

## Installation

pip install -r requirements.txt

## Usage

```python
from latex_parser.tex_reader import TexReader

# Initialize the parser
tex_reader = TexReader()

# Process a compressed TeX file (supports .gz and .tar.gz)
result, temp_dir = tex_reader.process_compressed("path/to/paper.tar.gz")

# Convert to JSON
json_output = tex_reader.to_json(result)

# Or save directly to file
tex_reader.save_to_json(result, "output.json")
```

## License

This project is licensed under the MIT License - see the [LICENSE.txt](LICENSE.txt) file for details.
