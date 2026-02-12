"""Role/Position enumeration."""
from enum import Enum


class Role(Enum):
    """League of Legends lane roles/positions."""
    
    TOP = "TOP"
    JUNGLE = "JUNGLE"
    MIDDLE = "MIDDLE"
    BOTTOM = "BOTTOM"
    UTILITY = "UTILITY"  # Support
    
    @property
    def position_name(self) -> str:
        """Get position name."""
        return self.value
    
    @property
    def short_name(self) -> str:
        """Get short position name."""
        short_names = {
            "TOP": "top",
            "JUNGLE": "jg",
            "MIDDLE": "mid",
            "BOTTOM": "adc",
            "UTILITY": "sup"
        }
        return short_names[self.value]
    
    @classmethod
    def all_roles(cls) -> list['Role']:
        """Get all roles."""
        return list(cls)
    
    @classmethod
    def from_string(cls, role_str: str) -> 'Role':
        """Create Role from string."""
        try:
            return cls[role_str.upper()]
        except KeyError:
            # Try mapping common variations
            mappings = {
                "SUPPORT": cls.UTILITY,
                "SUP": cls.UTILITY,
                "ADC": cls.BOTTOM,
                "BOT": cls.BOTTOM,
                "MID": cls.MIDDLE,
                "JG": cls.JUNGLE,
                "JGL": cls.JUNGLE
            }
            return mappings.get(role_str.upper(), cls.BOTTOM)
