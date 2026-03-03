"""Helpers for validating and listing platform codes."""
from __future__ import annotations

from typing import Dict, List

from domain.enums import Region


class PlatformChecker:
    """Validates platform codes against the Region enum."""

    @staticmethod
    def all_platform_rows() -> List[tuple[str, str, str]]:
        regions = Region.all_regions()
        return [(r.platform_route, r.friendly, r.regional_route) for r in regions]

    @staticmethod
    def validate_codes(codes: List[str]) -> Dict[str, bool]:
        valid = {r.platform_route.lower() for r in Region.all_regions()}
        return {c: (c.lower() in valid) for c in codes}

