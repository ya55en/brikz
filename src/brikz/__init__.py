"""brikz - a BrickLink API sync+async Python wrapper."""

from . import catalog_item
from .core import (
    AsyncBrickLink,
    BrickLink,
    BrickLinkAPIError,
    BrickLinkCredentials,
    BrikzError,
    MalformedResponseError,
    Request,
)
from .enums import AppearAs, GuideType, ItemType, NewOrUsed, Region, VatOption

__version__ = "0.0.2"

# The transport and BrickLink's enumerations are cross-cutting, so they live
# here; each sub-API keeps its own models (`from brikz.catalog_item import Item`).
__all__ = (
    "AppearAs",
    "AsyncBrickLink",
    "BrickLink",
    "BrickLinkAPIError",
    "BrickLinkCredentials",
    "BrikzError",
    "GuideType",
    "ItemType",
    "MalformedResponseError",
    "NewOrUsed",
    "Region",
    "Request",
    "VatOption",
    "catalog_item",
)
