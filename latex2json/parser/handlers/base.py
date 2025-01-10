from abc import ABC, abstractmethod
from typing import Callable, Dict, List, Optional, Tuple, Any


class TokenHandler(ABC):
    def __init__(self, process_content_fn: Optional[Callable[[str], Any]] = None):
        """Initialize handler with optional command expansion function"""
        self.process_content_fn = process_content_fn

    def set_process_content_fn(self, process_content_fn: Callable[[str], Any]):
        self.process_content_fn = process_content_fn

    @abstractmethod
    def can_handle(self, content: str) -> bool:
        """Check if this handler can process the current content"""
        raise NotImplementedError

    @abstractmethod
    def handle(
        self, content: str, prev_token: Optional[Dict] = None
    ) -> Tuple[Optional[Dict], int]:
        """Process the content and return (token, new_position)"""
        raise NotImplementedError

    def clear(self):
        self.process_content_fn = None
