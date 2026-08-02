"""The data models only the Catalog Item page names."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from ..enums.catalog_item import AppearAs
from ..enums.shared import ItemType, NewOrUsed

if TYPE_CHECKING:
    from ..catalog_item import ItemRef


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

    def ref(self) -> ItemRef:
        """This item, as something to ask further questions about."""
        from ..catalog_item import ItemRef

        return ItemRef(self.type, self.no)


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
