"""The enumerations more than one BrickLink doc page names.

Lenient by design: these appear on the response path as well as the request
path, so a value BrickLink adds later becomes a member rather than an error.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Any


class LenientStrEnum(StrEnum):
    """A StrEnum that accepts values it has never heard of."""

    @classmethod
    def _missing_(cls, value: Any) -> LenientStrEnum | None:
        """Synthesize a member for an unrecognized value."""
        if not isinstance(value, str):
            return None

        member = str.__new__(cls, value)
        member._name_ = value
        member._value_ = value
        cls._value2member_map_[value] = member
        return member


class ItemType(LenientStrEnum):
    MINIFIG = "MINIFIG"
    PART = "PART"
    SET = "SET"
    BOOK = "BOOK"
    GEAR = "GEAR"
    CATALOG = "CATALOG"
    INSTRUCTION = "INSTRUCTION"
    UNSORTED_LOT = "UNSORTED_LOT"
    ORIGINAL_BOX = "ORIGINAL_BOX"


class NewOrUsed(LenientStrEnum):
    NEW = "N"
    USED = "U"
