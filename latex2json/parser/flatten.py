from typing import List, Dict
from collections import OrderedDict


def flatten_tokens(tokens: str | List[Dict]) -> tuple[str, OrderedDict[str, Dict]]:
    flattened_content = ""
    reference_map = OrderedDict[str, Dict]()
    ref_counter = 1

    if isinstance(tokens, str):
        return tokens, {}

    for token in tokens:
        if (
            token["type"] == "text"
            and isinstance(token["content"], str)
            and "styles" not in token
        ):
            flattened_content += token["content"]
        else:
            # Create a reference key and store token in map
            ref_key = "`|REF_%s|`" % ref_counter
            reference_map[ref_key] = token.copy()
            # Add reference placeholder to flattened content
            flattened_content += ref_key
            ref_counter += 1

    return flattened_content, reference_map


if __name__ == "__main__":
    tokens = [
        {
            "type": "command",
            "content": "\\multicolumn{2}{|c|}{\\multirow{2}{*}{Region}} ",
        },
        {"type": "text", "content": "&"},
        {"type": "command", "content": "\\multicolumn{2}{c|}{Sales} "},
        {"type": "text", "content": "\\\\"},
        {"type": "command", "content": "\\multicolumn{2}{|c|}{} "},
        {"type": "text", "content": "& 2022 & 2023\\\\"},
        {"type": "command", "content": "\\multirow{2}{*}{North} "},
        {"type": "text", "content": "& Urban &"},
        {"type": "equation", "content": "x^2 + y^2 = z^2", "display": "inline"},
        {"type": "text", "content": "& 180\\\\& Rural & 100 & 120\\\\"},
        {"type": "command", "content": "\\multirow{2}{*}{South} "},
        {"type": "text", "content": "& Urban & 200 &"},
        {
            "type": "equation",
            "content": "E = mc^2 \\\\ $F = ma$",
            "display": "block",
            "labels": ["eq:1"],
        },
        {"type": "text", "content": "\\\\& & 130 & 160\\\\"},
    ]

    out = flatten_tokens(tokens)
    print(out)
