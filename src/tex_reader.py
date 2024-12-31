import os
import gzip
import tarfile
import tempfile
from contextlib import contextmanager
from src.tex_utils import strip_latex_comments


class TexFileExtractor:
    """A class to handle reading and processing TeX files from various sources."""

    @staticmethod
    def is_main_tex_file(content):
        """Check if content contains markers indicating it's a main TeX file.

        Args:
            content (str): The file content to check

        Returns:
            bool: True if the content appears to be a main TeX file
        """
        clean_content = strip_latex_comments(content)
        if r"\documentclass" in clean_content:
            return True
        if r"\begin{document}" in clean_content:
            return True
        return False

    @staticmethod
    def find_main_tex_file(folder_path):
        """Find the main TeX file in a directory.

        Args:
            folder_path (str): Path to the directory to search

        Returns:
            str: Name of the main TeX file

        Raises:
            FileNotFoundError: If no main TeX file is found
        """
        tex_files = [f for f in os.listdir(folder_path) if f.endswith(".tex")]

        if not tex_files:
            raise FileNotFoundError(f"No .tex files found in {folder_path}")

        for tex_file in tex_files:
            file_path = os.path.join(folder_path, tex_file)
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
                if TexFileExtractor.is_main_tex_file(content):
                    return tex_file
            except Exception as e:
                print(f"Error reading {tex_file}: {str(e)}")
                continue

        raise FileNotFoundError(
            "No main TeX file found (no documentclass or begin{document} found)"
        )

    @staticmethod
    @contextmanager
    def process_compressed_file(gz_path):
        """Process a gzipped file (either single file or tar archive).

        Args:
            gz_path (str): Path to the gzipped file

        Yields:
            tuple: (main_tex_file, temp_dir)
                  main_tex_file: Name of the main TeX file
                  temp_dir: Path to temporary directory containing extracted files
        """
        temp_dir = tempfile.mkdtemp()
        try:
            with gzip.open(gz_path, "rb") as f_in:
                content = f_in.read()
                is_tar = content.startswith(b"ustar") or gz_path.endswith(".tar.gz")

                if is_tar:
                    temp_tar = os.path.join(temp_dir, "temp.tar")
                    with open(temp_tar, "wb") as f_out:
                        f_out.write(content)

                    with tarfile.open(temp_tar) as tar:

                        def safe_extract(tar_info, kwds=None):
                            if os.path.isabs(tar_info.name) or ".." in tar_info.name:
                                return None
                            return tar_info

                        tar.extractall(temp_dir, filter=safe_extract)

                    main_tex = TexFileExtractor.find_main_tex_file(temp_dir)
                else:
                    # Single file case
                    temp_file = os.path.join(temp_dir, "temp_file")
                    with open(temp_file, "wb") as f_out:
                        f_out.write(content)

                    with open(temp_file, "r", encoding="utf-8") as f:
                        if TexFileExtractor.is_main_tex_file(f.read()):
                            main_tex = "temp_file"
                        else:
                            raise FileNotFoundError("Extracted file is not a TeX file")

                yield main_tex, temp_dir

        finally:
            # Clean up temporary directory
            import shutil

            shutil.rmtree(temp_dir)

    @classmethod
    def from_folder(cls, folder_path):
        """Create a TexReader instance from a folder containing TeX files.

        Args:
            folder_path (str): Path to the folder

        Returns:
            tuple: (main_tex_file, folder_path)
        """
        main_tex = cls.find_main_tex_file(folder_path)
        return main_tex, folder_path

    @classmethod
    @contextmanager
    def from_compressed(cls, gz_path):
        """Create a TexReader instance from a compressed file.

        Args:
            gz_path (str): Path to the compressed file

        Yields:
            tuple: (main_tex_file, temp_dir)
                  main_tex_file: Name of the main TeX file
                  temp_dir: Path to temporary directory containing extracted files
        """
        with cls.process_compressed_file(gz_path) as (main_tex, temp_dir):
            yield main_tex, temp_dir


if __name__ == "__main__":
    from src.parser.tex_parser import LatexParser
    from src.structure.builder import TokenBuilder

    parser = LatexParser()
    token_builder = TokenBuilder()

    # Example usage
    try:
        # # From compressed file
        # gz_file = "papers/arXiv-1907.11692v1.tar.gz"
        gz_file = "papers/arXiv-2301.10303v4.gz"
        with TexFileExtractor.from_compressed(gz_file) as (main_tex, temp_dir):
            print(f"Found main TeX file in archive: {main_tex}")
            # Work with files in temp_dir...
            file = os.path.join(temp_dir, main_tex)
            tokens = parser.parse_file(file)
            parser.clear()
            output = token_builder.build(tokens)

        # # From folder
        # main_tex, folder = TexReader.from_folder("papers/new/arXiv-1907.11692v1")
        # print(f"Found main TeX file in folder: {main_tex}")

    except Exception as e:
        print(f"Error: {str(e)}")

    with open("papers/tested/arXiv-math9404236v1.tex", "r", encoding="utf-8") as f:
        print(TexFileExtractor.is_main_tex_file(f.read()))
