"""DNS helper utilities used by health and scraping commands."""
from __future__ import annotations

import socket
from typing import List

from domain.enums import Region


class DNSChecker:
    @staticmethod
    def resolves(host: str) -> bool:
        try:
            socket.getaddrinfo(host, None)
            return True
        except Exception:
            return False

    @classmethod
    def platform_candidates_for_region(cls, region: Region) -> List[str]:
        if region.regional_route == "sea":
            order = [region.platform_route, "sg2", "th2", "tw2", "vn2", "oc1"]
            seen: set[str] = set()
            result: List[str] = []
            for h in order:
                if h not in seen:
                    seen.add(h)
                    result.append(h)
            return result
        return [region.platform_route]

