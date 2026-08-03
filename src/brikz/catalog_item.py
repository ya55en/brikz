"""The Catalog Item sub-API: `/items/{type}/{no}` and its sub-resources.

Every endpoint hangs off an `ItemRef`, which names the item once. Building a
request is pure -- it touches no network. Hand one to `BrickLink.send` or
`AsyncBrickLink.send` to execute it:

    item = client.send(ItemRef(ItemType.SET, '6608-1').get())

See docs/design/notes.md for the reasoning behind the shape.
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
from .models.catalog_item import (
    Item,
    KnownColor,
    PriceDetail,
    PriceGuide,
    SubsetEntry,
    SubsetItem,
    SupersetEntry,
    SupersetItem,
)

__all__ = (
    'Item',
    'KnownColor',
    'PriceDetail',
    'PriceGuide',
    'SubsetEntry',
    'SubsetItem',
    'SupersetEntry',
    'SupersetItem',
)

if TYPE_CHECKING:
    from .enums.catalog_item import GuideType, Region, VatOption


# --- Requests ---------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class ItemRef:
    """One catalog item, named once, as something to build requests about.

    Holds no client and performs no I/O -- it is a key, not a resource
    object. Every method here is pure and returns a `Request` for `send` to
    execute:

        set_6608 = ItemRef(ItemType.SET, '6608-1')
        prices = client.send(set_6608.price_guide(new_or_used=NewOrUsed.USED))
    """

    type: ItemType
    no: str

    def __post_init__(self) -> None:
        _reject_blank_item_key(self.type, self.no)

    def get(self) -> Request[Item]:
        """GET /items/{type}/{no} -- this catalog item."""
        return Request(path=item_path(self.type, self.no), parse=parse_item)

    def image(self, color_id: int) -> Request[Item]:
        """GET /items/{type}/{no}/images/{color_id} -- this item in one color.

        Answers a sparse `Item`: BrickLink fills only `no`, `type` and
        `thumbnail_url`.
        """
        return Request(
            path=item_path(self.type, self.no, 'images', color_id),
            parse=parse_item,
        )

    def supersets(self, *, color_id: int | None = None) -> Request[tuple[SupersetEntry, ...]]:
        """GET /items/{type}/{no}/supersets -- the items that include this one."""
        return Request(
            path=item_path(self.type, self.no, 'supersets'),
            parse=parse_superset_entries,
            params={'color_id': color_id},
        )

    def subsets(
        self,
        *,
        color_id: int | None = None,
        box: bool | None = None,
        instruction: bool | None = None,
        break_minifigs: bool | None = None,
        break_subsets: bool | None = None,
    ) -> Request[tuple[SubsetEntry, ...]]:
        """GET /items/{type}/{no}/subsets -- the items included in this one."""
        return Request(
            path=item_path(self.type, self.no, 'subsets'),
            parse=parse_subset_entries,
            params={
                'color_id': color_id,
                'box': box,
                'instruction': instruction,
                'break_minifigs': break_minifigs,
                'break_subsets': break_subsets,
            },
        )

    def price_guide(
        self,
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
            path=item_path(self.type, self.no, 'price'),
            parse=parse_price_guide,
            params={
                'color_id': color_id,
                'guide_type': guide_type,
                'new_or_used': new_or_used,
                'country_code': country_code,
                'region': region,
                'currency_code': currency_code,
                'vat': vat,
            },
        )

    def known_colors(self) -> Request[tuple[KnownColor, ...]]:
        """GET /items/{type}/{no}/colors -- the colors this item is known in."""
        return Request(
            path=item_path(self.type, self.no, 'colors'),
            parse=parse_known_colors,
        )


# --- Parsers ----------------------------------------------------------------


def parse_item(data: JsonStruct | None) -> Item:
    """Read an `Item` off the envelope's data."""
    if not isinstance(data, dict):
        raise ValueError(f'expected an item object, got {data!r}')  # noqa: TRY004

    weight = data.get('weight')
    dim_x = data.get('dim_x')
    dim_y = data.get('dim_y')
    dim_z = data.get('dim_z')
    year_released = data.get('year_released')
    category_id = data.get('category_id')
    if category_id is None:
        category_id = data.get('categoryID')

    return Item(
        no=str(data['no']),
        type=ItemType(data['type']),
        name=data.get('name'),
        category_id=int(category_id) if category_id is not None else None,
        alternate_no=data.get('alternate_no'),
        image_url=data.get('image_url'),
        thumbnail_url=data.get('thumbnail_url'),
        weight=Decimal(weight) if weight is not None else None,
        dim_x=Decimal(dim_x) if dim_x is not None else None,
        dim_y=Decimal(dim_y) if dim_y is not None else None,
        dim_z=Decimal(dim_z) if dim_z is not None else None,
        year_released=int(year_released) if year_released is not None else None,
        description=data.get('description'),
        is_obsolete=data.get('is_obsolete'),
        language_code=data.get('language_code'),
    )


def parse_superset_entries(data: JsonStruct | None) -> tuple[SupersetEntry, ...]:
    """Read the superset entries off the envelope's data."""
    if not isinstance(data, list):
        raise ValueError(f'expected a list of superset entries, got {data!r}')  # noqa: TRY004

    return tuple(_parse_superset_entry(entry) for entry in data)


def _parse_superset_entry(entry: Any) -> SupersetEntry:
    items = tuple(_parse_superset_item(item) for item in entry['entries'])
    return SupersetEntry(color_id=int(entry['color_id']), entries=items)


def _parse_superset_item(entry: Any) -> SupersetItem:
    appear_as = entry.get('appear_as')
    if appear_as is None:
        appear_as = entry.get('appears_as')

    return SupersetItem(
        item=parse_item(entry['item']),
        quantity=int(entry['quantity']),
        appear_as=AppearAs(appear_as) if appear_as is not None else None,
    )


def parse_subset_entries(data: JsonStruct | None) -> tuple[SubsetEntry, ...]:
    """Read the subset entries off the envelope's data."""
    if not isinstance(data, list):
        raise ValueError(f'expected a list of subset entries, got {data!r}')  # noqa: TRY004

    return tuple(_parse_subset_entry(entry) for entry in data)


def _parse_subset_entry(entry: Any) -> SubsetEntry:
    items = tuple(_parse_subset_item(item) for item in entry['entries'])
    return SubsetEntry(match_no=int(entry['match_no']), entries=items)


def _parse_subset_item(entry: Any) -> SubsetItem:
    color_id = entry.get('color_id')
    return SubsetItem(
        item=parse_item(entry['item']),
        color_id=int(color_id) if color_id is not None else None,
        quantity=int(entry.get('quantity', 0)),
        extra_quantity=int(entry.get('extra_quantity', 0)),
        is_alternate=bool(entry.get('is_alternate', False)),
        is_counterpart=bool(entry.get('is_counterpart', False)),
    )


def parse_price_guide(data: JsonStruct | None) -> PriceGuide:
    """Read a `PriceGuide` off the envelope's data."""
    if not isinstance(data, dict):
        raise ValueError(f'expected a price guide object, got {data!r}')  # noqa: TRY004

    price_detail: list[Any] = data.get('price_detail') or []
    return PriceGuide(
        item=parse_item(data['item']),
        new_or_used=NewOrUsed(data['new_or_used']),
        currency_code=str(data['currency_code']),
        min_price=Decimal(data['min_price']),
        max_price=Decimal(data['max_price']),
        avg_price=Decimal(data['avg_price']),
        qty_avg_price=Decimal(data['qty_avg_price']),
        unit_quantity=int(data['unit_quantity']),
        total_quantity=int(data['total_quantity']),
        price_detail=tuple(_parse_price_detail(row) for row in price_detail),
    )


def _parse_price_detail(row: Any) -> PriceDetail:
    date_ordered = row.get('date_ordered')
    return PriceDetail(
        quantity=int(row['quantity']),
        unit_price=Decimal(row['unit_price']),
        shipping_available=row.get('shipping_available'),
        seller_country_code=row.get('seller_country_code'),
        buyer_country_code=row.get('buyer_country_code'),
        date_ordered=datetime.fromisoformat(date_ordered) if date_ordered is not None else None,
    )


def parse_known_colors(data: JsonStruct | None) -> tuple[KnownColor, ...]:
    """Read the known colors off the envelope's data."""
    if not isinstance(data, list):
        raise ValueError(f'expected a list of known colors, got {data!r}')  # noqa: TRY004

    return tuple(
        KnownColor(color_id=int(entry['color_id']), quantity=int(entry['quantity']))
        for entry in data
    )


def _reject_blank_item_key(item_type: str, item_no: str) -> None:
    """Reject a blank type or number: they build a structurally different URL."""
    if not item_type:
        raise ValueError('item type must not be blank')

    if not item_no:
        raise ValueError('item number must not be blank')


def item_path(item_type: str, item_no: str, *segments: str | int) -> str:
    """Build `/items/{type}/{no}[/...]`, percent-encoding every segment.

    Raises ValueError on a blank type or number: those build a structurally
    different URL rather than a merely invalid one.
    """
    _reject_blank_item_key(item_type, item_no)

    parts = (item_type, item_no, *segments)
    return '/items/' + '/'.join(quote(str(part), safe='') for part in parts)
