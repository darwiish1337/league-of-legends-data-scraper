"""Region enumeration for League of Legends servers."""
from enum import Enum


class Region(Enum):
    """League of Legends regional servers."""
    
    # Europe
    EUW1 = "euw1"  # Europe West
    EUN1 = "eun1"  # Europe Nordic & East
    
    # Americas
    NA1 = "na1"    # North America
    BR1 = "br1"    # Brazil
    LA1 = "la1"    # Latin America North
    LA2 = "la2"    # Latin America South
    
    # Asia
    KR = "kr"      # Korea
    JP1 = "jp1"    # Japan
    
    # SEA & Oceania
    OC1 = "oc1"    # Oceania
    PH2 = "ph2"    # Philippines
    SG2 = "sg2"    # Singapore
    TH2 = "th2"    # Thailand
    TW2 = "tw2"    # Taiwan
    VN2 = "vn2"    # Vietnam
    
    # Other
    TR1 = "tr1"    # Turkey
    RU = "ru"      # Russia
    ME1 = "me1"    # Middle East
    
    @property
    def platform_route(self) -> str:
        """Get platform routing value for API calls."""
        return self.value
    
    @property
    def regional_route(self) -> str:
        """Get regional routing for account and match APIs."""
        regional_mapping = {
            # Americas
            "na1": "americas",
            "br1": "americas",
            "la1": "americas",
            "la2": "americas",
            
            # Europe
            "euw1": "europe",
            "eun1": "europe",
            "tr1": "europe",
            "ru": "europe",
            "me1": "europe",
            
            # Asia
            "kr": "asia",
            "jp1": "asia",
            
            # SEA
            "oc1": "sea",
            "ph2": "sea",
            "sg2": "sea",
            "th2": "sea",
            "tw2": "sea",
            "vn2": "sea",
        }
        return regional_mapping.get(self.value, "americas")
    
    @classmethod
    def all_regions(cls) -> list['Region']:
        """Get all available regions."""
        return list(cls)
