import logging
import colorama
from colorama import Fore, Style
import sys

# Initialize colorama for Windows support
colorama.init()


class ColoredFormatter(logging.Formatter):
    """Custom formatter that adds colors to log messages based on level"""

    COLORS = {
        "DEBUG": Fore.BLUE,
        "INFO": Fore.WHITE,
        "WARNING": Fore.YELLOW,
        "ERROR": Fore.RED,
        "CRITICAL": Fore.RED + Style.BRIGHT,
    }

    def format(self, record):
        # Store original message and levelname
        original_msg = record.msg
        original_levelname = record.levelname

        # Add color only if outputting to terminal
        if self._is_tty_output():
            record.levelname = f"{self.COLORS.get(record.levelname, '')}{record.levelname}{Style.RESET_ALL}"
            record.msg = (
                f"{self.COLORS.get(record.levelname, '')}{record.msg}{Style.RESET_ALL}"
            )

        formatted_message = super().format(record)

        # Restore original values
        record.msg = original_msg
        record.levelname = original_levelname

        return formatted_message

    def _is_tty_output(self):
        """Check if the output is going to a terminal"""
        return hasattr(sys.stdout, "isatty") and sys.stdout.isatty()


def setup_logger(
    name: str = None, level: int = logging.WARNING, log_file: str = None
) -> logging.Logger:
    """
    Set up and return a logger instance with colored output.

    Args:
        name: Logger name (defaults to root logger if None)
        level: Logging level (defaults to WARNING)

    Returns:
        logging.Logger: Configured logger instance
    """
    logger = logging.getLogger(name)

    # Clear any existing handlers
    logger.handlers.clear()

    # Create console handler with colored formatter
    console_handler = logging.StreamHandler()
    console_formatter = ColoredFormatter(
        fmt="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)
    logger.propagate = False

    # Create file handler with non-colored formatter (optional)
    if log_file:
        file_handler = logging.FileHandler(log_file, mode="w")
        file_formatter = logging.Formatter(
            fmt="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)

    # Set level
    logger.setLevel(level)

    return logger
