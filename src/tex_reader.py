import logging
import os
import json
from typing import List
import warnings

from src.structure.tokens.base import BaseToken
from src.tex_file_extractor import TexFileExtractor
from src.parser.tex_parser import LatexParser
from src.structure.builder import TokenBuilder


class TexReader:
    """Class to handle reading and processing TeX files into tokens and JSON output."""

    def __init__(self, logger: logging.Logger = None):
        self.logger = logger or logging.getLogger(__name__)

        self.parser = LatexParser(logger=self.logger)
        self.token_builder = TokenBuilder(logger=self.logger)

    def process_file(self, file_path: str) -> List[BaseToken]:
        """Process a single TeX file and return the token output."""
        if not os.path.exists(file_path):
            self.logger.error(f"File {file_path} does not exist")
            raise FileNotFoundError(f"File {file_path} does not exist")

        tokens = self.parser.parse_file(file_path)
        output = self.token_builder.build(tokens)
        self.clear()
        return output

    def save_to_json(self, output: List[BaseToken], json_path="output.json"):
        """Save token output to JSON file."""

        # serialize output to json (use model_dump(mode='json') instead of model_dump_json since latter adds unnecessary escape chars)
        with warnings.catch_warnings():
            warnings.filterwarnings(
                "ignore",
                module="pydantic",
            )
            json_output = [t.model_dump(mode="json") for t in output]

        with open(json_path, "w") as f:
            json.dump(json_output, f)
        self.logger.info(f"Saved output to {json_path}")

    def clear(self):
        """Clear both parser and token builder states."""
        self.parser.clear()
        self.token_builder.clear()

    def process_compressed(self, gz_path: str, cleanup: bool = True):
        """Process a compressed TeX file and save results to JSON."""
        if not os.path.exists(gz_path):
            error_msg = f"Compressed file not found: {gz_path}"
            self.logger.error(error_msg)
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
            self.logger.error(error_msg)
            raise RuntimeError(error_msg) from e


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.DEBUG,  # More verbose when running directly
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        force=True,
        handlers=[
            # logging.FileHandler(
            #     "logs/tex_parser.log"
            # ),  # Output to a file named 'tex_parser.log'
            logging.StreamHandler(),  # Optional: also output to console
        ],
    )
    logging.getLogger("asyncio").setLevel(logging.WARNING)

    logger = logging.getLogger(__name__)

    tex_reader = TexReader(logger)

    try:
        # Example usage with compressed file
        gz_file = "papers/arXiv-2301.10945v1.tar.gz"
        output, temp_dir = tex_reader.process_compressed(gz_file)
        tex_reader.save_to_json(output)

    except Exception as e:
        print(f"Error: {str(e)}")
