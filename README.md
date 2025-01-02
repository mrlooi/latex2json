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
