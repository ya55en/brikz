"""BrickLink's own enumerations.

`shared` holds what more than one BrickLink doc page names; every other module
here mirrors one sub-API and holds the enums only that page uses. The whole
vocabulary is re-exported here, so where a member lives is free to change.
"""

from .catalog_item import AppearAs, GuideType, Region, VatOption
from .shared import ItemType, LenientStrEnum, NewOrUsed

__all__ = (
    'AppearAs',
    'GuideType',
    'ItemType',
    'LenientStrEnum',
    'NewOrUsed',
    'Region',
    'VatOption',
)
