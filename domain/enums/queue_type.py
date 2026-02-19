"""Queue type enumeration for ranked matches."""
from enum import Enum


class QueueType(Enum):
    """Ranked queue types in League of Legends.
    
    Provides:
    - queue_id: numeric queue id for match filters
    - queue_name: human-readable name
    - api_queue_name: string used by league endpoints
    """
    
    RANKED_SOLO_5x5 = 420  # Solo/Duo Queue
    RANKED_FLEX_SR = 440   # Flex 5v5 Queue
    
    @property
    def queue_id(self) -> int:
        """Get queue ID for API calls."""
        return self.value
    
    @property
    def queue_name(self) -> str:
        """Get human-readable queue name."""
        names = {
            420: "Ranked Solo/Duo",
            440: "Ranked Flex 5v5"
        }
        return names[self.value]
    
    @property
    def api_queue_name(self) -> str:
        """Get queue name string used in /league endpoints."""
        return "RANKED_SOLO_5x5" if self == QueueType.RANKED_SOLO_5x5 else "RANKED_FLEX_SR"
    
    @classmethod
    def ranked_queues(cls) -> list['QueueType']:
        """Get all ranked queue types."""
        return [cls.RANKED_SOLO_5x5, cls.RANKED_FLEX_SR]
