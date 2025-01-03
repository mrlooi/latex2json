import pytest
import logging
import shutil
from pathlib import Path
import os

from src.tex_reader import TexReader, ProcessingResult


@pytest.fixture
def tex_reader():
    """Create a TexReader instance with test logger."""
    return TexReader(logger=logging.getLogger("test_logger"))


dir_path = os.path.dirname(os.path.abspath(__file__))
test_dir = Path(dir_path) / "test_data"


@pytest.fixture
def sample_files(request):
    """Provide paths to test files and ensure cleanup after tests."""
    test_files = {
        "single_file": test_dir / "arXiv-2301.10303v4.gz",
        "directory": test_dir / "arXiv-1907.11692v1.tar.gz",
    }

    # Verify test files exist
    for file_path in test_files.values():
        assert file_path.exists(), f"Test file not found: {file_path}"

    return test_files


class TestTexReader:
    """Test suite for the TexReader class.

    Tests cover:
    - Processing of single and multi-file archives
    - Error handling
    - State management
    - Cleanup behavior
    """

    def test_process_single_file_gz(self, tex_reader: TexReader, sample_files: dict):
        """Verify processing of a single gzipped TeX file."""
        result, temp_dir = tex_reader.process_compressed(
            str(sample_files["single_file"])
        )

        assert isinstance(result, ProcessingResult)
        assert result.tokens, "Expected non-empty token list"
        assert not Path(temp_dir).exists(), "Temporary directory should be cleaned up"

    def test_process_directory_tar_gz(self, tex_reader: TexReader, sample_files: dict):
        """Verify processing of a tar.gz archive with multiple TeX files."""
        result, temp_dir = tex_reader.process_compressed(str(sample_files["directory"]))

        assert isinstance(result, ProcessingResult)
        assert result.tokens, "Expected non-empty token list"
        assert not Path(temp_dir).exists(), "Temporary directory should be cleaned up"

    def test_error_handling(self, tex_reader: TexReader, tmp_path: Path):
        """Verify appropriate error handling for various failure scenarios."""
        # Test nonexistent file
        with pytest.raises(FileNotFoundError, match=".*not found"):
            tex_reader.process_compressed("nonexistent_file.gz")

        # Test corrupted archive
        invalid_file = tmp_path / "invalid.tar.gz"
        invalid_file.write_text("Invalid content")
        with pytest.raises(RuntimeError, match="Failed to process.*"):
            tex_reader.process_compressed(str(invalid_file))

    @pytest.mark.parametrize("cleanup", [True, False])
    def test_cleanup_behavior(
        self, tex_reader: TexReader, sample_files: dict, cleanup: bool
    ):
        """Verify temporary directory cleanup behavior.

        Args:
            cleanup: Whether automatic cleanup should be performed
        """
        _, temp_dir = tex_reader.process_compressed(
            str(sample_files["single_file"]), cleanup=cleanup
        )
        temp_path = Path(temp_dir)

        if cleanup:
            assert (
                not temp_path.exists()
            ), "Directory should be automatically cleaned up"
        else:
            assert (
                temp_path.exists()
            ), "Directory should be preserved when cleanup=False"
            assert any(temp_path.iterdir()), "Directory should contain extracted files"
            # Clean up manually
            shutil.rmtree(temp_dir)

    def test_to_json(self, tex_reader: TexReader, sample_files: dict):
        """Verify JSON conversion functionality."""
        result, _ = tex_reader.process_compressed(str(sample_files["single_file"]))

        json_str = tex_reader.to_json(result)
        assert isinstance(json_str, str), "to_json should return a string"
        assert json_str.startswith("["), "JSON output should be an array"
        assert len(json_str) > 2, "JSON output should not be empty"

    def test_save_to_json(
        self, tex_reader: TexReader, sample_files: dict, tmp_path: Path
    ):
        """Verify JSON output functionality."""
        result, _ = tex_reader.process_compressed(str(sample_files["single_file"]))
        output_path = tmp_path / "output.json"

        try:
            tex_reader.save_to_json(result, output_path)

            assert output_path.exists(), "JSON output file should be created"
            assert output_path.stat().st_size > 0, "JSON output should not be empty"
        finally:
            # Clean up the output file
            if output_path.exists():
                output_path.unlink()
