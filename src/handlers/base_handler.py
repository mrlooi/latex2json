from abc import ABC, abstractmethod
from typing import Callable, Dict, List, Optional, Tuple

class TokenHandler(ABC):
    @abstractmethod
    def can_handle(self, content: str) -> bool:
        """Check if this handler can process the current content"""
        pass
    
    @abstractmethod
    def handle(self, content: str, expand_command_fn: Optional[Callable[[str], str]] = None) -> Tuple[Optional[Dict], int]:
        """Process the content and return (token, new_position)"""
        pass