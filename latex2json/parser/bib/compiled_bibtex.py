import re
import argparse
import sys

from latex2json.utils.tex_utils import (
    find_matching_env_block,
    extract_nested_content_sequence_blocks,
    extract_nested_content,
)

PATTERNS_TO_REPLACE = {
    r"\\bibinitperiod\b": ".",
    r"\\bibrangedash\s*\b": "--",
}


def apply_pattern_replacements(text):
    """
    Apply all the pattern replacements defined in PATTERNS_TO_REPLACE to the input text.
    """
    result = text
    for pattern, replacement in PATTERNS_TO_REPLACE.items():
        result = re.sub(pattern, replacement, result)
    return result


def parse_compiled_bibtex_entry(entry_text):
    r"""
    Parses a single compiled BibTeX entry into a dictionary.
    Returns a dictionary with keys:
      - key: citation key (from \entry{...})
      - type: entry type (e.g., misc, article, etc.)
      - author: formatted author string (if available)
      - other fields: title, year, eprint, eprinttype, eprintclass, etc.
    """
    # Apply pattern replacements to the entry text first
    entry_text = apply_pattern_replacements(entry_text)

    entry = {}

    # Extract the entry header: \entry{<key>}{<type>}{...}
    header_match = re.search(r"\\entry\{([^}]+)\}\{([^}]+)\}\{[^}]*\}", entry_text)
    if header_match:
        entry_key = header_match.group(1).strip()
        entry_type = header_match.group(2).strip()
        entry["key"] = entry_key
        entry["type"] = entry_type
    else:
        raise ValueError("Could not parse entry header")

    # First find the \name{author} block
    author_pattern = r"\\name\{author\}"
    author_match = re.search(author_pattern, entry_text)
    if author_match:
        start_pos = author_match.end()
        authors = []
        # Extract each author block using extract_nested_content_sequence_blocks
        author_blocks, _ = extract_nested_content_sequence_blocks(
            entry_text[start_pos:], "{", "}", max_blocks=3
        )

        author_blocks = author_blocks[2]

        if author_blocks:
            # find the hash stuff
            for hash_match in re.finditer(r"\{hash=\w+\}\{", author_blocks):
                hash_pos = hash_match.end() - 1
                auth_block, end_pos = extract_nested_content(
                    author_blocks[hash_pos:], "{", "}"
                )
                if auth_block:
                    # Extract family and given names
                    family_match = re.search(r"family=\{([^}]+)\}", auth_block)
                    given_match = re.search(r"given=\{([^}]+)\}", auth_block)
                    if family_match and given_match:
                        family = family_match.group(1).strip()
                        given = given_match.group(1).strip()
                        given = given[:1] + "."
                        authors.append(f"{family}, {given}")

        if authors:
            entry["author"] = " and ".join(authors)

    # Parse \field blocks (e.g. title, year, eprinttype, eprintclass)
    for field_match in re.finditer(r"\\field\{([^}]+)\}\{([^}]+)\}", entry_text):
        field_key = field_match.group(1).strip()
        field_value = field_match.group(2).strip()
        # Skip internal fields that aren't needed.
        if field_key in ["labelnamesource", "labeltitlesource"]:
            continue
        if field_key == "journaltitle":
            field_key = "journal"
        entry[field_key] = field_value

    # Parse the eprint value from the \verb block
    eprint_match = re.search(
        r"\\verb\{eprint\}\s*\\verb\s+(.+?)\s+\\endverb", entry_text, re.DOTALL
    )
    if eprint_match:
        eprint_value = eprint_match.group(1).strip()
        entry["eprint"] = eprint_value

    return entry


def convert_to_regular_bibtex(entry):
    """
    Converts the parsed entry dictionary to a regular BibTeX formatted string.
    """
    lines = []
    entry_type = entry.get("type", "misc")
    key = entry.get("key", "unknown")
    lines.append(f"@{entry_type}{{{key},")

    # Specify the field order you want in the output.
    field_order = ["author", "title", "year", "eprint", "eprinttype", "eprintclass"]
    for field in field_order:
        if field in entry:
            lines.append(f"  {field} = {{{entry[field]}}},")

    # Optionally, add any additional fields that were parsed
    for field, value in entry.items():
        if field in ["key", "type"] or field in field_order:
            continue
        lines.append(f"  {field} = {{{value}}},")

    lines.append("}")
    return "\n".join(lines)


def process_compiled_bibtex_to_bibtex(input_text):
    """
    Processes the entire input text, finding all compiled BibTeX entries,
    converting each to standard BibTeX format, and returning the combined result.
    """
    # Find all blocks from \entry to \endentry (non-greedy match)
    entries = re.findall(r"(\\entry\{.*?\\endentry)", input_text, re.DOTALL)
    output_entries = []
    for entry_text in entries:
        try:
            entry = parse_compiled_bibtex_entry(entry_text)
            bibtex_entry = convert_to_regular_bibtex(entry)
            output_entries.append(bibtex_entry)
        except Exception as e:
            sys.stderr.write(f"Error parsing an entry: {e}\n")
    return output_entries


def is_compiled_bibtex(input_text: str) -> bool:
    # Check for the presence of an entry block from \entry to \endentry
    pattern = r"\\entry\{.*?\\endentry"
    return bool(re.search(pattern, input_text, re.DOTALL))


if __name__ == "__main__":
    text = r"""
 \entry{deitke2023objaverse}{inproceedings}{}
    \name{author}{10}{}{%
      {{hash=DM}{%
         family={Deitke},
         familyi={D\bibinitperiod},
         given={Matt},
         giveni={M\bibinitperiod},
      }}%
      {{hash=SD}{%
         family={Schwenk},
         familyi={S\bibinitperiod},
         given={Dustin},
         giveni={D\bibinitperiod},
      }}%
      {{hash=SJ}{%
         family={Salvador},
         familyi={S\bibinitperiod},
         given={Jordi},
         giveni={J\bibinitperiod},
      }}%
      {{hash=WL}{%
         family={Weihs},
         familyi={W\bibinitperiod},
         given={Luca},
         giveni={L\bibinitperiod},
      }}%
      {{hash=MO}{%
         family={Michel},
         familyi={M\bibinitperiod},
         given={Oscar},
         giveni={O\bibinitperiod},
      }}%
      {{hash=VE}{%
         family={VanderBilt},
         familyi={V\bibinitperiod},
         given={Eli},
         giveni={E\bibinitperiod},
      }}%
      {{hash=SL}{%
         family={Schmidt},
         familyi={S\bibinitperiod},
         given={Ludwig},
         giveni={L\bibinitperiod},
      }}%
      {{hash=EK}{%
         family={Ehsani},
         familyi={E\bibinitperiod},
         given={Kiana},
         giveni={K\bibinitperiod},
      }}%
      {{hash=KA}{%
         family={Kembhavi},
         familyi={K\bibinitperiod},
         given={Aniruddha},
         giveni={A\bibinitperiod},
      }}%
      {{hash=FA}{%
         family={Farhadi},
         familyi={F\bibinitperiod},
         given={Ali},
         giveni={A\bibinitperiod},
      }}%
    }
    \strng{namehash}{DMSDSJWLMOVESLEKKAFA1}
    \strng{fullhash}{DMSDSJWLMOVESLEKKAFA1}
    \field{labelnamesource}{author}
    \field{labeltitlesource}{title}
    \field{booktitle}{Proceedings of the IEEE/CVF Conference on Computer Vision and Pattern Recognition}
    \field{pages}{13142\bibrangedash 13153}
    \field{title}{Objaverse: A universe of annotated 3d objects}
    \field{year}{2023}
  \endentry
    
 \entry{levine2018learning}{article}{}
    \name{author}{5}{}{%
      {{hash=LS}{%
         family={Levine},
         familyi={L\bibinitperiod},
         given={Sergey},
         giveni={S\bibinitperiod},
      }}%
      {{hash=PP}{%
         family={Pastor},
         familyi={P\bibinitperiod},
         given={Peter},
         giveni={P\bibinitperiod},
      }}%
      {{hash=KA}{%
         family={Krizhevsky},
         familyi={K\bibinitperiod},
         given={Alex},
         giveni={A\bibinitperiod},
      }}%
      {{hash=IJ}{%
         family={Ibarz},
         familyi={I\bibinitperiod},
         given={Julian},
         giveni={J\bibinitperiod},
      }}%
      {{hash=QD}{%
         family={Quillen},
         familyi={Q\bibinitperiod},
         given={Deirdre},
         giveni={D\bibinitperiod},
      }}%
    }
    \list{publisher}{1}{%
      {SAGE Publications Sage UK: London, England}%
    }
    \strng{namehash}{LSPPKAIJQD1}
    \strng{fullhash}{LSPPKAIJQD1}
    \field{labelnamesource}{author}
    \field{labeltitlesource}{title}
    \field{number}{4-5}
    \field{pages}{421\bibrangedash 436}
    \field{title}{Learning hand-eye coordination for robotic grasping with deep learning and large-scale data collection}
    \field{volume}{37}
    \field{journaltitle}{The International journal of robotics research}
    \field{year}{2018}
  \endentry

    """
    out = process_compiled_bibtex_to_bibtex(text)
    for entry in out:
        print(entry)
        print("\n\n")
