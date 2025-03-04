import os
import gzip
import tarfile
import tempfile
import shutil
import zipfile
from contextlib import contextmanager

from latex2json.utils.tex_utils import strip_latex_comments
from latex2json.utils.encoding import read_file


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
        """Find the main TeX file and its containing folder in a directory or its subdirectories.

        Args:
            folder_path (str): Path to the directory to search

        Returns:
            tuple: (main_tex_file, main_folder)
                  main_tex_file: Relative path to the main TeX file
                  main_folder: Path to the folder containing the main TeX file

        Raises:
            FileNotFoundError: If no main TeX file is found
        """
        for root, _, files in os.walk(folder_path):
            for file in files:
                if file.endswith(".tex"):
                    full_path = os.path.join(root, file)
                    try:
                        content = read_file(full_path)
                        if TexFileExtractor.is_main_tex_file(content):
                            # Return both the relative path and the containing folder
                            return os.path.relpath(full_path, folder_path), root
                    except Exception as e:
                        print(f"Error reading {full_path}: {str(e)}")
                        continue

        raise FileNotFoundError(
            "No main TeX file found (no documentclass or begin{document} found)"
        )

    @staticmethod
    @contextmanager
    def process_compressed_file(compressed_path, cleanup: bool = True):
        """Process a compressed file (gzip, tar.gz, or zip).

        Args:
            compressed_path (str): Path to the compressed file
            cleanup (bool): Whether to clean up temporary files after processing

        Yields:
            tuple: (main_tex_file, main_folder)
                  main_tex_file: Name of the main TeX file
                  main_folder: Path to folder containing the main TeX file
        """
        temp_dir = tempfile.mkdtemp()
        try:
            if compressed_path.endswith(".zip"):
                with zipfile.ZipFile(compressed_path, "r") as zip_ref:
                    # Check for path traversal attempts before extraction
                    for member in zip_ref.namelist():
                        if os.path.isabs(member) or ".." in member:
                            continue
                        zip_ref.extract(member, temp_dir)
                main_tex, main_folder = TexFileExtractor.find_main_tex_file(temp_dir)
            else:
                with gzip.open(compressed_path, "rb") as f_in:
                    content = f_in.read()
                    is_tar = content.startswith(b"ustar") or compressed_path.endswith(
                        ".tar.gz"
                    )

                    if is_tar:
                        temp_tar = os.path.join(temp_dir, "temp.tar")
                        with open(temp_tar, "wb") as f_out:
                            f_out.write(content)

                        try:
                            # Try to open as a tar file with error handling
                            with tarfile.open(temp_tar) as tar:
                                # Check for path traversal attempts before extraction
                                for member in tar.getmembers():
                                    if (
                                        os.path.isabs(member.name)
                                        or ".." in member.name
                                    ):
                                        continue
                                    tar.extract(member, temp_dir)

                            main_tex, main_folder = TexFileExtractor.find_main_tex_file(
                                temp_dir
                            )
                        except (
                            tarfile.ReadError,
                            tarfile.CompressionError,
                            EOFError,
                        ) as e:
                            # Handle tar file errors by treating it as a single file
                            print(
                                f"Error processing tar file: {str(e)}. Treating as a single file."
                            )
                            temp_file = os.path.join(temp_dir, "temp_file.tex")
                            with open(temp_file, "wb") as f_out:
                                f_out.write(content)

                            content_str = read_file(temp_file)
                            if TexFileExtractor.is_main_tex_file(content_str):
                                main_tex = "temp_file.tex"
                                main_folder = temp_dir
                            else:
                                raise FileNotFoundError(
                                    f"Could not process as tar file and extracted content is not a valid TeX file: {str(e)}"
                                )
                    else:
                        # Single file case
                        temp_file = os.path.join(temp_dir, "temp_file.tex")
                        with open(temp_file, "wb") as f_out:
                            f_out.write(content)

                        content_str = read_file(temp_file)
                        if TexFileExtractor.is_main_tex_file(content_str):
                            main_tex = "temp_file.tex"
                            main_folder = temp_dir
                        else:
                            raise FileNotFoundError(
                                "Extracted file is not a valid TeX file"
                            )

            yield main_tex, temp_dir

        finally:
            # Clean up temporary directory
            if cleanup:
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
        return main_tex

    @classmethod
    @contextmanager
    def from_compressed(cls, gz_path, cleanup: bool = True):
        """Create a TexReader instance from a compressed file.

        Args:
            gz_path (str): Path to the compressed file

        Yields:
            tuple: (main_tex_file, temp_dir)
                  main_tex_file: Name of the main TeX file
                  temp_dir: Path to temporary directory containing extracted files
        """
        with cls.process_compressed_file(gz_path, cleanup) as (main_tex, temp_dir):
            yield main_tex, temp_dir


if __name__ == "__main__":
    path = "./source.tar.gz"
    with TexFileExtractor.from_compressed(path, cleanup=False) as (
        main_tex,
        temp_dir,
    ):
        print("Found main tex %s in folder %s" % (main_tex, temp_dir))
