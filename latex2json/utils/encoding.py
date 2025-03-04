import chardet
from chardet.universaldetector import UniversalDetector


def detect_encoding(path: str) -> str:
    """
    Detect the encoding of a file.

    Args:
        path (str): Path to the file

    Returns:
        str: Detected encoding, defaults to 'utf-8' if detection fails
    """

    # Read the file in binary mode
    with open(path, "rb") as file:
        # Read a sample of the file for faster detection
        # For larger files, reading the first few KB is usually sufficient
        raw_data = file.read(10000)  # Read first 10KB
        if len(raw_data) == 0:  # Empty file
            return "utf-8"

    # Detect encoding
    result = chardet.detect(raw_data)
    encoding = result.get("encoding", "utf-8")

    # Handle None or very low confidence results
    if encoding is None or result.get("confidence", 0) < 0.5:
        encoding = "utf-8"  # Default to utf-8 if unsure

    # Some common encoding mappings/normalizations
    encoding_map = {
        "ascii": "utf-8",  # ASCII is a subset of UTF-8
        "ISO-8859-1": "latin-1",
        "Windows-1252": "cp1252",
    }

    return encoding_map.get(encoding, encoding)


def read_file(path):
    """
    Read a file with proper encoding detection.

    Args:
        path (str): Path to the file

    Returns:
        str: Content of the file
    """
    encoding = detect_encoding(path)

    try:
        with open(path, "r", encoding=encoding) as f:
            return f.read()
    except UnicodeDecodeError:
        # First fallback: try utf-8 with error handling
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                return f.read()
        except UnicodeDecodeError:
            # Last resort: latin-1 can read any byte sequence
            with open(path, "r", encoding="latin-1") as f:
                return f.read()


# Usage
if __name__ == "__main__":
    file_path = "papers/new/arXiv-1903.10801v1.tex"
    detect_encoding(file_path)
