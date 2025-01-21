import logging
import os
import json
from typing import Dict, List, TypeVar, Callable, Any, Tuple, Optional
import warnings
from dataclasses import dataclass
from pathlib import Path
import shutil

from latex2json.structure.tokens.base import BaseToken
from latex2json.tex_file_extractor import TexFileExtractor
from latex2json.parser.tex_parser import LatexParser
from latex2json.structure.builder import TokenBuilder

T = TypeVar("T")


@dataclass
class ProcessingResult:
    """Represents the result of processing a TeX file."""

    tokens: List[BaseToken]
    temp_dir: Optional[Path] = None
    color_map: Optional[Dict[str, Dict[str, str]]] = None

    def cleanup(self):
        """Clean up temporary resources."""
        if self.temp_dir and self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)
            self.temp_dir = None


class TexProcessingError(Exception):
    """Base exception for TeX processing errors."""

    pass


class TexReader:
    """
    Handles reading and processing TeX files into tokens and JSON output.

    Attributes:
        logger: Logger instance for tracking operations
        parser: LaTeX parser instance
        token_builder: Token builder instance
    """

    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger(__name__)
        self.parser = LatexParser(logger=self.logger)
        self.token_builder = TokenBuilder(logger=self.logger)

    def _handle_file_operation(
        self, operation: Callable[..., T], error_msg: str, *args, **kwargs
    ) -> T:
        """
        Generic error handler for file operations.

        Args:
            operation: Callable to execute
            error_msg: Error message template
            *args: Positional arguments for operation
            **kwargs: Keyword arguments for operation

        Returns:
            Result of the operation

        Raises:
            FileNotFoundError: If required files are missing
            TexProcessingError: If processing fails
        """
        try:
            return operation(*args, **kwargs)
        except FileNotFoundError as e:
            self.logger.error("File not found error: %s", str(e), exc_info=True)
            raise
        except Exception as e:
            self.logger.error("%s: %s", error_msg, str(e), exc_info=True)
            raise TexProcessingError(f"{error_msg}: {str(e)}") from e

    def _verify_file_exists(self, file_path: Path, file_type: str = "File") -> None:
        """
        Verify file exists and log appropriate error if not.

        Args:
            file_path: Path to verify
            file_type: Type of file for error messaging

        Raises:
            FileNotFoundError: If file doesn't exist
        """
        if not file_path.exists():
            raise FileNotFoundError(f"{file_type} not found: {file_path}")

    def process_file(self, file_path: Path | str) -> ProcessingResult:
        """
        Process a single TeX file and return the token output.

        Args:
            file_path: Path to the TeX file

        Returns:
            ProcessingResult containing the processed tokens

        Raises:
            FileNotFoundError: If file doesn't exist
            TexProcessingError: If processing fails
        """
        file_path = Path(file_path)

        def _process() -> ProcessingResult:
            self.clear()
            self._verify_file_exists(file_path)
            tokens = self.parser.parse_file(file_path)
            output = self.token_builder.build(tokens)
            color_map = self.parser.get_colors()
            self.clear()
            return ProcessingResult(tokens=output, color_map=color_map)

        return self._handle_file_operation(
            _process, f"Failed to process TeX file {file_path}"
        )

    def to_json(self, result: ProcessingResult) -> str:
        """
        Convert token output to JSON string.

        Args:
            result: ProcessingResult containing tokens to convert

        Returns:
            JSON string representation of the tokens

        Raises:
            TexProcessingError: If conversion fails
        """

        def _convert() -> str:
            with warnings.catch_warnings():
                warnings.filterwarnings("ignore", module="pydantic")
                json_output = [
                    t.model_dump(mode="json", exclude_none=True) for t in result.tokens
                ]
            data = {
                "tokens": json_output,
                "color_map": result.color_map,
            }
            # ensure_ascii=False to prevent unnecessary escape characters
            return json.dumps(data, ensure_ascii=False)

        return self._handle_file_operation(_convert, "Failed to convert tokens to JSON")

    def save_to_json(
        self, result: ProcessingResult, json_path: Path | str = "output.json"
    ) -> None:
        """
        Save token output to JSON file.

        Args:
            result: ProcessingResult containing tokens to save
            json_path: Path where to save the JSON

        Raises:
            TexProcessingError: If saving fails
        """
        json_path = Path(json_path)

        def _save() -> None:
            json_output = self.to_json(result)
            json_path.parent.mkdir(parents=True, exist_ok=True)
            json_path.write_text(json_output, encoding="utf-8")
            self.logger.info("Successfully saved output to %s", json_path)

        return self._handle_file_operation(
            _save, f"Failed to save JSON output to {json_path}"
        )

    def clear(self):
        """Clear both parser and token builder states."""
        self.parser.clear()
        self.token_builder.clear()

    def process_compressed(self, gz_path: str, cleanup: bool = True):
        """Process a compressed TeX file and save results to JSON."""
        if not os.path.exists(gz_path):
            error_msg = f"Compressed file not found: {gz_path}"
            self.logger.error(error_msg, exc_info=True)
            raise FileNotFoundError(error_msg)

        try:
            with TexFileExtractor.from_compressed(gz_path, cleanup) as (
                main_tex,
                temp_dir,
            ):
                self.logger.info(
                    f"Found main TeX file in archive: {main_tex}, {gz_path}"
                )
                file_path = os.path.join(temp_dir, main_tex)
                output = self.process_file(file_path)
                return output, temp_dir
        except Exception as e:
            error_msg = f"Failed to process compressed file {gz_path}: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            raise RuntimeError(error_msg) from e

    def process_folder(self, folder_path: str | Path) -> ProcessingResult:
        """Process a folder containing TeX files and return results.

        Args:
            folder_path: Path to the folder containing TeX files

        Returns:
            ProcessingResult containing the processed tokens

        Raises:
            FileNotFoundError: If folder doesn't exist or no main TeX file found
            TexProcessingError: If processing fails
        """
        folder_path = Path(folder_path)

        def _process() -> ProcessingResult:
            self._verify_file_exists(folder_path, file_type="Folder")
            main_tex, _ = TexFileExtractor.from_folder(str(folder_path))
            file_path = folder_path / main_tex
            return self.process_file(file_path)

        return self._handle_file_operation(
            _process, f"Failed to process TeX folder {folder_path}"
        )

    def process(
        self, input_path: str | Path, cleanup: bool = False
    ) -> ProcessingResult:
        """
        Process input which can be a single file, folder, or compressed archive.

        Args:
            input_path: Path to the input (file, folder, or compressed archive)
            cleanup: Whether to clean up temporary files (for compressed archives)

        Returns:
            ProcessingResult containing the processed tokens

        Raises:
            FileNotFoundError: If input doesn't exist
            TexProcessingError: If processing fails
        """
        input_path = Path(input_path)
        self._verify_file_exists(input_path)

        def _process() -> ProcessingResult:
            if input_path.is_dir():
                return self.process_folder(input_path)
            elif input_path.suffix in [".gz", ".tar.gz", ".tgz", ".zip"]:
                result, temp_dir = self.process_compressed(
                    str(input_path), cleanup=False
                )
                result.temp_dir = temp_dir
                if cleanup:
                    result.cleanup()
                return result
            else:
                return self.process_file(input_path)

        return self._handle_file_operation(
            _process, f"Failed to process input {input_path}"
        )


if __name__ == "__main__":
    from latex2json.utils.logger import setup_logger

    logging.getLogger("asyncio").setLevel(logging.WARNING)

    logger = setup_logger(level=logging.INFO, log_file="logs/tex_reader.log")

    tex_reader = TexReader(logger)

    # # Example usage with compressed file
    # gz_file = "papers/arXiv-2301.10945v1.tar.gz"
    # output, temp_dir = tex_reader.process_compressed(gz_file)
    # tex_reader.save_to_json(output)

    # Example usage with folder
    target_folder = "outputs"
    folders = [
        # "papers/new/arXiv-math0503066v2",
        # "papers/tested/arXiv-1509.05363v6",
        # "papers/tested/arXiv-1706.03762v7",
        # "papers/tested/arXiv-2303.08774v6",
        # "papers/tested/arXiv-2301.10945v1",
        # "papers/tested/arXiv-1907.11692v1",
        # "papers/tested/arXiv-1712.01815v1",
        # "papers/new/arXiv-2304.02643v1",
        # "papers/tested/arXiv-2010.13219v3",
        # "papers/tested/arXiv-1710.09829v2",
        "papers/tested/arXiv-1512.03385v1",
        # "papers/new/arXiv-hep-th0603057v3",
        "papers/tested/arXiv-math9404236v1.tex",
        # "papers/tested/arXiv-2301.10303v4.tex",
        # "papers/tested/arXiv-2105.02865v3.tex",
        "papers/arXiv-2301.10945v1.tar.gz",
    ]
    for folder in folders:
        save_path = target_folder + "/" + folder.split("/")[-1] + ".json"
        output = tex_reader.process(folder)
        try:
            tex_reader.save_to_json(output, save_path)
            print("SAVED TO", save_path)
        finally:
            output.cleanup()  # Ensure cleanup happens even if save_to_json fails
