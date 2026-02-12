"""Queue type enumeration for ranked matches."""
from enum import Enum


class QueueType(Enum):
    """Ranked queue types in League of Legends."""
    
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
    
    @classmethod
    def ranked_queues(cls) -> list['QueueType']:
        """Get all ranked queue types."""
        return [cls.RANKED_SOLO_5x5, cls.RANKED_FLEX_SR]
