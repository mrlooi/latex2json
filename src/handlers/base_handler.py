from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Tuple

class TokenHandler(ABC):
    @abstractmethod
    def can_handle(self, content: str, current_pos: int) -> bool:
        """Check if this handler can process the current content"""
        pass
    
    @abstractmethod
    def handle(self, content: str, current_pos: int, parser) -> Tuple[Optional[Dict], int]:
        """Process the content and return (token, new_position)"""
        pass