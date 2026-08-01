"""The Catalog Item sub-API: `/items/{type}/{no}` and its sub-resources.

Every function here is pure -- it builds a `Request` and touches no network.
Hand one to `BrickLink.send` or `AsyncBrickLink.send` to execute it:

    item = client.send(catalog_item.get_item(ItemType.SET, '6608-1'))

Stubs only. See docs/design/notes.md for the reasoning behind the shape.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING
from urllib.parse import quote

from .core import JsonStruct, Request

if TYPE_CHECKING:
    from datetime import datetime
    from decimal import Decimal

    from .enums.catalog_item import AppearAs, GuideType, Region, VatOption
    from .enums.shared import ItemType, NewOrUsed


# --- Models -----------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Item:
    """A catalog item.

    Only `no` and `type` are always there. BrickLink omits fields freely, and
    the nested item references inside supersets, subsets and price guides
    carry just a handful of them -- so one model covers all four shapes.
    """

    no: str
    type: ItemType
    name: str | None = None
    category_id: int | None = None
    alternate_no: str | None = None
    image_url: str | None = None
    thumbnail_url: str | None = None
    weight: Decimal | None = None
    dim_x: Decimal | None = None
    dim_y: Decimal | None = None
    dim_z: Decimal | None = None
    year_released: int | None = None
    description: str | None = None
    is_obsolete: bool | None = None
    language_code: str | None = None


@dataclass(frozen=True, slots=True)
class SupersetItem:
    """One item that includes the item asked about."""

    item: Item
    quantity: int
    appear_as: AppearAs | None = None


@dataclass(frozen=True, slots=True)
class SupersetEntry:
    """The items including the item asked about, for one color."""

    color_id: int
    entries: tuple[SupersetItem, ...]


@dataclass(frozen=True, slots=True)
class SubsetItem:
    """One item included in the item asked about."""

    item: Item
    color_id: int | None = None
    quantity: int = 0
    extra_quantity: int = 0
    is_alternate: bool = False
    is_counterpart: bool = False


@dataclass(frozen=True, slots=True)
class SubsetEntry:
    """One matching group of items included in the item asked about."""

    match_no: int
    entries: tuple[SubsetItem, ...]


@dataclass(frozen=True, slots=True)
class PriceDetail:
    """One row behind a price guide.

    Which fields are filled depends on the `guide_type` the request asked
    for: `stock` fills `shipping_available`, `sold` fills the country codes
    and `date_ordered`.
    """

    quantity: int
    unit_price: Decimal
    shipping_available: bool | None = None
    seller_country_code: str | None = None
    buyer_country_code: str | None = None
    date_ordered: datetime | None = None


@dataclass(frozen=True, slots=True)
class PriceGuide:
    """Price statistics for an item, VAT excluded unless asked otherwise."""

    item: Item
    new_or_used: NewOrUsed
    currency_code: str
    min_price: Decimal
    max_price: Decimal
    avg_price: Decimal
    qty_avg_price: Decimal
    unit_quantity: int
    total_quantity: int
    price_detail: tuple[PriceDetail, ...]


@dataclass(frozen=True, slots=True)
class KnownColor:
    """A color an item is known in, and how many exist in it."""

    color_id: int
    quantity: int


# --- Requests ---------------------------------------------------------------


def get_item(item_type: ItemType, item_no: str) -> Request[Item]:
    """GET /items/{type}/{no} -- one catalog item."""
    return Request(path=item_path(item_type, item_no), parse=parse_item)


def get_item_image(item_type: ItemType, item_no: str, color_id: int) -> Request[Item]:
    """GET /items/{type}/{no}/images/{color_id} -- the item's image in one color.

    Answers a sparse `Item`: BrickLink fills only `no`, `type` and
    `thumbnail_url`.
    """
    return Request(path=item_path(item_type, item_no, "images", color_id), parse=parse_item)


def get_supersets(
    item_type: ItemType,
    item_no: str,
    *,
    color_id: int | None = None,
) -> Request[tuple[SupersetEntry, ...]]:
    """GET /items/{type}/{no}/supersets -- the items that include this one."""
    return Request(
        path=item_path(item_type, item_no, "supersets"),
        parse=parse_superset_entries,
        params={"color_id": color_id},
    )


def get_subsets(
    item_type: ItemType,
    item_no: str,
    *,
    color_id: int | None = None,
    box: bool | None = None,
    instruction: bool | None = None,
    break_minifigs: bool | None = None,
    break_subsets: bool | None = None,
) -> Request[tuple[SubsetEntry, ...]]:
    """GET /items/{type}/{no}/subsets -- the items included in this one."""
    return Request(
        path=item_path(item_type, item_no, "subsets"),
        parse=parse_subset_entries,
        params={
            "color_id": color_id,
            "box": box,
            "instruction": instruction,
            "break_minifigs": break_minifigs,
            "break_subsets": break_subsets,
        },
    )


def get_price_guide(
    item_type: ItemType,
    item_no: str,
    *,
    color_id: int | None = None,
    guide_type: GuideType | None = None,
    new_or_used: NewOrUsed | None = None,
    country_code: str | None = None,
    region: Region | None = None,
    currency_code: str | None = None,
    vat: VatOption | None = None,
) -> Request[PriceGuide]:
    """GET /items/{type}/{no}/price -- price statistics for this item."""
    return Request(
        path=item_path(item_type, item_no, "price"),
        parse=parse_price_guide,
        params={
            "color_id": color_id,
            "guide_type": guide_type,
            "new_or_used": new_or_used,
            "country_code": country_code,
            "region": region,
            "currency_code": currency_code,
            "vat": vat,
        },
    )


def get_known_colors(item_type: ItemType, item_no: str) -> Request[tuple[KnownColor, ...]]:
    """GET /items/{type}/{no}/colors -- the colors this item is known in."""
    return Request(path=item_path(item_type, item_no, "colors"), parse=parse_known_colors)


# --- Parsers ----------------------------------------------------------------


def parse_item(data: JsonStruct | None) -> Item:
    """Read an `Item` off the envelope's data."""
    raise NotImplementedError


def parse_superset_entries(data: JsonStruct | None) -> tuple[SupersetEntry, ...]:
    """Read the superset entries off the envelope's data."""
    raise NotImplementedError


def parse_subset_entries(data: JsonStruct | None) -> tuple[SubsetEntry, ...]:
    """Read the subset entries off the envelope's data."""
    raise NotImplementedError


def parse_price_guide(data: JsonStruct | None) -> PriceGuide:
    """Read a `PriceGuide` off the envelope's data."""
    raise NotImplementedError


def parse_known_colors(data: JsonStruct | None) -> tuple[KnownColor, ...]:
    """Read the known colors off the envelope's data."""
    raise NotImplementedError


def item_path(item_type: str, item_no: str, *segments: str | int) -> str:
    """Build `/items/{type}/{no}[/...]`, percent-encoding every segment.

    Raises ValueError on a blank type or number: those build a structurally
    different URL rather than a merely invalid one.
    """
    if not item_type:
        raise ValueError("item type must not be blank")
    if not item_no:
        raise ValueError("item number must not be blank")

    parts = (item_type, item_no, *segments)
    return "/items/" + "/".join(quote(str(part), safe="") for part in parts)
