"""The enumerations only the Catalog Item page names."""

from .shared import LenientStrEnum


class GuideType(LenientStrEnum):
    SOLD = 'sold'
    STOCK = 'stock'


class Region(LenientStrEnum):
    ASIA = 'asia'
    AFRICA = 'africa'
    NORTH_AMERICA = 'north_america'
    SOUTH_AMERICA = 'south_america'
    MIDDLE_EAST = 'middle_east'
    EUROPE = 'europe'
    EU = 'eu'
    OCEANIA = 'oceania'


class VatOption(LenientStrEnum):
    EXCLUDE = 'N'
    INCLUDE = 'Y'
    NORWAY = 'O'


class AppearAs(LenientStrEnum):
    """How an entry appears in the inventory of the item that includes it."""

    ALTERNATE = 'A'
    COUNTERPART = 'C'
    EXTRA = 'E'
    REGULAR = 'R'
