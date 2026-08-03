"""brikz - a BrickLink API sync+async Python wrapper."""

import logging

from . import catalog_item
from .catalog_item import ItemRef
from .core import (
    AsyncBrickLink,
    BrickLink,
    BrickLinkAPIError,
    BrickLinkCredentials,
    BrikzError,
    MalformedResponseError,
    Request,
    ResponseParseError,
)
from .enums import AppearAs, GuideType, ItemType, NewOrUsed, Region, VatOption
from .models import (
    Item,
    KnownColor,
    PriceDetail,
    PriceGuide,
    SubsetEntry,
    SubsetItem,
    SupersetEntry,
    SupersetItem,
)

__version__ = '0.0.2'

# A library configures no logging; it only makes sure its records go nowhere
# until an application asks for them.
logging.getLogger(__name__).addHandler(logging.NullHandler())

# The whole vocabulary lands here -- the transport, BrickLink's enumerations,
# the models a response parses into, and each sub-API's reference type -- so
# where a name lives is free to change. The machinery that builds and reads
# requests stays behind its module: `catalog_item.parse_item`, `item_path`.
__all__ = (
    'AppearAs',
    'AsyncBrickLink',
    'BrickLink',
    'BrickLinkAPIError',
    'BrickLinkCredentials',
    'BrikzError',
    'GuideType',
    'Item',
    'ItemRef',
    'ItemType',
    'KnownColor',
    'MalformedResponseError',
    'NewOrUsed',
    'PriceDetail',
    'PriceGuide',
    'Region',
    'Request',
    'ResponseParseError',
    'SubsetEntry',
    'SubsetItem',
    'SupersetEntry',
    'SupersetItem',
    'VatOption',
    'catalog_item',
)
