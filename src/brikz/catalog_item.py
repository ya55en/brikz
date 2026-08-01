"""The Catalog Item sub-API: `/items/{type}/{no}` and its sub-resources.

Every function here is pure -- it builds a `Request` and touches no network.
Hand one to `BrickLink.send` or `AsyncBrickLink.send` to execute it:

    item = client.send(catalog_item.get_item(ItemType.SET, '6608-1'))

Stubs only. See docs/design/notes.md for the reasoning behind the shape.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Any
from urllib.parse import quote

from .core import JsonStruct, Request
from .enums.catalog_item import AppearAs
from .enums.shared import ItemType, NewOrUsed

if TYPE_CHECKING:
    from .enums.catalog_item import GuideType, Region, VatOption


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
    if not isinstance(data, dict):
        raise ValueError(f"expected an item object, got {data!r}")  # noqa: TRY004

    weight = data.get("weight")
    dim_x = data.get("dim_x")
    dim_y = data.get("dim_y")
    dim_z = data.get("dim_z")
    year_released = data.get("year_released")
    category_id = data.get("category_id")
    if category_id is None:
        category_id = data.get("categoryID")

    return Item(
        no=str(data["no"]),
        type=ItemType(data["type"]),
        name=data.get("name"),
        category_id=int(category_id) if category_id is not None else None,
        alternate_no=data.get("alternate_no"),
        image_url=data.get("image_url"),
        thumbnail_url=data.get("thumbnail_url"),
        weight=Decimal(weight) if weight is not None else None,
        dim_x=Decimal(dim_x) if dim_x is not None else None,
        dim_y=Decimal(dim_y) if dim_y is not None else None,
        dim_z=Decimal(dim_z) if dim_z is not None else None,
        year_released=int(year_released) if year_released is not None else None,
        description=data.get("description"),
        is_obsolete=data.get("is_obsolete"),
        language_code=data.get("language_code"),
    )


def parse_superset_entries(data: JsonStruct | None) -> tuple[SupersetEntry, ...]:
    """Read the superset entries off the envelope's data."""
    if not isinstance(data, list):
        raise ValueError(f"expected a list of superset entries, got {data!r}")  # noqa: TRY004

    return tuple(_parse_superset_entry(entry) for entry in data)


def _parse_superset_entry(entry: Any) -> SupersetEntry:
    items = tuple(_parse_superset_item(item) for item in entry["entries"])
    return SupersetEntry(color_id=int(entry["color_id"]), entries=items)


def _parse_superset_item(entry: Any) -> SupersetItem:
    appear_as = entry.get("appear_as")
    if appear_as is None:
        appear_as = entry.get("appears_as")

    return SupersetItem(
        item=parse_item(entry["item"]),
        quantity=int(entry["quantity"]),
        appear_as=AppearAs(appear_as) if appear_as is not None else None,
    )


def parse_subset_entries(data: JsonStruct | None) -> tuple[SubsetEntry, ...]:
    """Read the subset entries off the envelope's data."""
    if not isinstance(data, list):
        raise ValueError(f"expected a list of subset entries, got {data!r}")  # noqa: TRY004

    return tuple(_parse_subset_entry(entry) for entry in data)


def _parse_subset_entry(entry: Any) -> SubsetEntry:
    items = tuple(_parse_subset_item(item) for item in entry["entries"])
    return SubsetEntry(match_no=int(entry["match_no"]), entries=items)


def _parse_subset_item(entry: Any) -> SubsetItem:
    color_id = entry.get("color_id")
    return SubsetItem(
        item=parse_item(entry["item"]),
        color_id=int(color_id) if color_id is not None else None,
        quantity=int(entry.get("quantity", 0)),
        extra_quantity=int(entry.get("extra_quantity", 0)),
        is_alternate=bool(entry.get("is_alternate", False)),
        is_counterpart=bool(entry.get("is_counterpart", False)),
    )


def parse_price_guide(data: JsonStruct | None) -> PriceGuide:
    """Read a `PriceGuide` off the envelope's data."""
    if not isinstance(data, dict):
        raise ValueError(f"expected a price guide object, got {data!r}")  # noqa: TRY004

    price_detail: list[Any] = data.get("price_detail") or []
    return PriceGuide(
        item=parse_item(data["item"]),
        new_or_used=NewOrUsed(data["new_or_used"]),
        currency_code=str(data["currency_code"]),
        min_price=Decimal(data["min_price"]),
        max_price=Decimal(data["max_price"]),
        avg_price=Decimal(data["avg_price"]),
        qty_avg_price=Decimal(data["qty_avg_price"]),
        unit_quantity=int(data["unit_quantity"]),
        total_quantity=int(data["total_quantity"]),
        price_detail=tuple(_parse_price_detail(row) for row in price_detail),
    )


def _parse_price_detail(row: Any) -> PriceDetail:
    date_ordered = row.get("date_ordered")
    return PriceDetail(
        quantity=int(row["quantity"]),
        unit_price=Decimal(row["unit_price"]),
        shipping_available=row.get("shipping_available"),
        seller_country_code=row.get("seller_country_code"),
        buyer_country_code=row.get("buyer_country_code"),
        date_ordered=datetime.fromisoformat(date_ordered) if date_ordered is not None else None,
    )


def parse_known_colors(data: JsonStruct | None) -> tuple[KnownColor, ...]:
    """Read the known colors off the envelope's data."""
    if not isinstance(data, list):
        raise ValueError(f"expected a list of known colors, got {data!r}")  # noqa: TRY004

    return tuple(
        KnownColor(color_id=int(entry["color_id"]), quantity=int(entry["quantity"]))
        for entry in data
    )


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
