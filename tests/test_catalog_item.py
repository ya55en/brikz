"""Behaviour specs for the `catalog_item` module.

Requests are values, so these need no client, no transport and no async: a
builder spec compares the `Request` an `ItemRef` method returns against the
path, params and parser it should carry, and a parser spec feeds it a
documented payload and checks the model that comes back. `send` is specced
in test_core.py, where it lives.
"""

from __future__ import annotations

import dataclasses
from datetime import datetime
from decimal import Decimal

import pytest

from brikz.catalog_item import (
    Item,
    ItemRef,
    KnownColor,
    item_path,
    parse_item,
    parse_known_colors,
    parse_price_guide,
    parse_subset_entries,
    parse_superset_entries,
)
from brikz.core import clean_params
from brikz.enums.catalog_item import AppearAs, GuideType, Region, VatOption
from brikz.enums.shared import ItemType, NewOrUsed


class describe_item_path:
    def it_builds_the_items_path_from_the_type_and_the_number(self):
        assert item_path("SET", "6608-1") == "/items/SET/6608-1"

    def it_appends_the_sub_resource_segments_it_is_given(self):
        assert item_path("SET", "6608-1", "supersets") == "/items/SET/6608-1/supersets"

    def it_accepts_an_integer_segment(self):
        assert item_path("SET", "6608-1", "images", 5) == "/items/SET/6608-1/images/5"

    def it_percent_encodes_a_number_that_contains_a_slash(self):
        assert item_path("PART", "3001/old") == "/items/PART/3001%2Fold"

    def it_percent_encodes_a_number_that_contains_a_hash(self):
        assert item_path("SET", "6608-1#1") == "/items/SET/6608-1%231"

    def it_refuses_a_blank_item_number(self):
        with pytest.raises(ValueError, match="number"):
            item_path("SET", "")

    def it_refuses_a_blank_item_type(self):
        with pytest.raises(ValueError, match="type"):
            item_path("", "6608-1")


class describe_ItemRef:
    def it_refuses_a_blank_item_number(self):
        with pytest.raises(ValueError, match="number"):
            ItemRef(ItemType.SET, "")

    def it_refuses_a_blank_item_type(self):
        with pytest.raises(ValueError, match="type"):
            ItemRef(ItemType(""), "6608-1")

    def it_equals_another_reference_to_the_same_item(self):
        assert ItemRef(ItemType.SET, "6608-1") == ItemRef(ItemType.SET, "6608-1")

    def it_differs_from_a_reference_to_the_same_number_of_another_type(self):
        assert ItemRef(ItemType.SET, "6608-1") != ItemRef(ItemType.PART, "6608-1")

    def it_refuses_to_be_mutated(self):
        ref = ItemRef(ItemType.SET, "6608-1")

        with pytest.raises(dataclasses.FrozenInstanceError):
            ref.no = "6609-1"  # pyright: ignore[reportAttributeAccessIssue]


class describe_ItemRef_get:
    def it_points_at_the_item_path(self):
        request = ItemRef(ItemType.SET, "6608-1").get()

        assert request.path == item_path(ItemType.SET, "6608-1")

    def it_asks_for_no_query_parameters(self):
        request = ItemRef(ItemType.SET, "6608-1").get()

        assert clean_params(request.params) == {}

    def it_reads_the_answer_as_an_item(self):
        request = ItemRef(ItemType.SET, "6608-1").get()

        assert request.parse is parse_item


class describe_ItemRef_image:
    def it_points_at_the_image_path_for_the_color(self):
        request = ItemRef(ItemType.SET, "6608-1").image(5)

        assert request.path == item_path(ItemType.SET, "6608-1", "images", 5)

    def it_reads_the_answer_as_an_item(self):
        request = ItemRef(ItemType.SET, "6608-1").image(5)

        assert request.parse is parse_item


class describe_ItemRef_supersets:
    def it_points_at_the_supersets_path(self):
        request = ItemRef(ItemType.PART, "3001old").supersets()

        assert request.path == item_path(ItemType.PART, "3001old", "supersets")

    def it_narrows_the_supersets_to_a_single_color(self):
        request = ItemRef(ItemType.PART, "3001old").supersets(color_id=5)

        assert request.params["color_id"] == 5

    def it_asks_for_every_color_when_given_no_color(self):
        request = ItemRef(ItemType.PART, "3001old").supersets()

        assert clean_params(request.params) == {}

    def it_reads_the_answer_as_superset_entries(self):
        request = ItemRef(ItemType.PART, "3001old").supersets()

        assert request.parse is parse_superset_entries


class describe_ItemRef_subsets:
    def it_points_at_the_subsets_path(self):
        request = ItemRef(ItemType.SET, "7644-1").subsets()

        assert request.path == item_path(ItemType.SET, "7644-1", "subsets")

    def it_narrows_the_subsets_to_a_single_color(self):
        request = ItemRef(ItemType.PART, "3001old").subsets(color_id=5)

        assert request.params["color_id"] == 5

    def it_asks_for_the_box_and_the_instruction_when_told_to(self):
        request = ItemRef(ItemType.SET, "7644-1").subsets(box=True, instruction=True)

        assert request.params["box"] is True
        assert request.params["instruction"] is True

    def it_breaks_minifigs_and_sets_down_when_told_to(self):
        request = ItemRef(ItemType.SET, "7644-1").subsets(
            break_minifigs=True, break_subsets=True
        )

        assert request.params["break_minifigs"] is True
        assert request.params["break_subsets"] is True

    def it_leaves_out_every_option_it_is_not_given(self):
        request = ItemRef(ItemType.SET, "7644-1").subsets()

        assert clean_params(request.params) == {}

    def it_reads_the_answer_as_subset_entries(self):
        request = ItemRef(ItemType.SET, "7644-1").subsets()

        assert request.parse is parse_subset_entries


class describe_ItemRef_price_guide:
    def it_points_at_the_price_path(self):
        request = ItemRef(ItemType.SET, "7644-1").price_guide()

        assert request.path == item_path(ItemType.SET, "7644-1", "price")

    def it_asks_for_the_sold_statistics_instead_of_the_stock_ones(self):
        request = ItemRef(ItemType.SET, "7644-1").price_guide(guide_type=GuideType.SOLD)

        assert request.params["guide_type"] == GuideType.SOLD

    def it_asks_for_the_used_condition(self):
        request = ItemRef(ItemType.SET, "7644-1").price_guide(new_or_used=NewOrUsed.USED)

        assert request.params["new_or_used"] == NewOrUsed.USED

    def it_narrows_the_price_guide_to_one_country(self):
        request = ItemRef(ItemType.SET, "7644-1").price_guide(country_code="US")

        assert request.params["country_code"] == "US"

    def it_narrows_the_price_guide_to_one_region(self):
        request = ItemRef(ItemType.SET, "7644-1").price_guide(region=Region.EUROPE)

        assert request.params["region"] == Region.EUROPE

    def it_asks_for_the_prices_in_a_given_currency(self):
        request = ItemRef(ItemType.SET, "7644-1").price_guide(currency_code="EUR")

        assert request.params["currency_code"] == "EUR"

    def it_asks_for_the_prices_with_vat_included(self):
        request = ItemRef(ItemType.SET, "7644-1").price_guide(vat=VatOption.INCLUDE)

        assert request.params["vat"] == VatOption.INCLUDE

    def it_leaves_out_every_option_it_is_not_given(self):
        request = ItemRef(ItemType.SET, "7644-1").price_guide()

        assert clean_params(request.params) == {}

    def it_reads_the_answer_as_a_price_guide(self):
        request = ItemRef(ItemType.SET, "7644-1").price_guide()

        assert request.parse is parse_price_guide


class describe_ItemRef_known_colors:
    def it_points_at_the_colors_path(self):
        request = ItemRef(ItemType.PART, "3001").known_colors()

        assert request.path == item_path(ItemType.PART, "3001", "colors")

    def it_reads_the_answer_as_known_colors(self):
        request = ItemRef(ItemType.PART, "3001").known_colors()

        assert request.parse is parse_known_colors


class describe_Item_ref:
    def it_names_the_item_it_came_from(self):
        item = Item(no="6608-1", type=ItemType.SET, name="Tractor")

        assert item.ref() == ItemRef(ItemType.SET, "6608-1")

    def it_builds_requests_about_that_item(self):
        item = parse_item({"no": "3001old", "type": "PART"})

        assert item.ref().known_colors().path == item_path(ItemType.PART, "3001old", "colors")


class describe_parse_item:
    def it_reads_the_documented_fields(self):
        item = parse_item(
            {
                "no": "3305-1",
                "name": "World Team Player",
                "type": "SET",
                "image_url": "http://bltest.ubifun.com/SL/3305-1.jpg",
                "thumbnail_url": "http://bltest.ubifun.com/S/3305-1.gif",
                "weight": "3.92",
                "dim_x": "0.00",
                "dim_y": "0.00",
                "dim_z": "0.00",
                "year_released": 1998,
                "is_obsolete": False,
                "category_id": 473,
            }
        )

        assert item == Item(
            no="3305-1",
            name="World Team Player",
            type=ItemType.SET,
            image_url="http://bltest.ubifun.com/SL/3305-1.jpg",
            thumbnail_url="http://bltest.ubifun.com/S/3305-1.gif",
            weight=Decimal("3.92"),
            dim_x=Decimal("0.00"),
            dim_y=Decimal("0.00"),
            dim_z=Decimal("0.00"),
            year_released=1998,
            is_obsolete=False,
            category_id=473,
        )

    def it_leaves_the_fields_bricklink_omits_unset(self):
        item = parse_item({"no": "3305-1", "type": "SET"})

        assert item.name is None
        assert item.alternate_no is None
        assert item.description is None
        assert item.language_code is None

    def it_reads_the_weight_and_the_dimensions_as_decimals(self):
        item = parse_item({"no": "3305-1", "type": "SET", "weight": "96.0440", "dim_x": "3.92"})

        assert item.weight == Decimal("96.0440")
        assert item.dim_x == Decimal("3.92")

    def it_reads_the_type_as_an_item_type(self):
        item = parse_item({"no": "3305-1", "type": "SET"})

        assert item.type is ItemType.SET

    def it_survives_an_item_type_it_has_never_heard_of(self):
        item = parse_item({"no": "3305-1", "type": "NEW_TYPE"})

        assert item.type == "NEW_TYPE"


class describe_parse_superset_entries:
    def it_groups_the_including_items_by_color(self):
        entries = parse_superset_entries(
            [
                {"color_id": 6, "entries": []},
                {"color_id": 7, "entries": []},
            ]
        )

        assert entries[0].color_id == 6
        assert entries[1].color_id == 7

    def it_reads_the_nested_item_reference(self):
        entries = parse_superset_entries(
            [
                {
                    "color_id": 6,
                    "entries": [
                        {
                            "item": {
                                "no": "555-1",
                                "name": "Hospital",
                                "type": "SET",
                                "categoryID": 277,
                            },
                            "quantity": 1,
                            "appears_as": "R",
                        }
                    ],
                }
            ]
        )

        item = entries[0].entries[0].item
        assert item.no == "555-1"
        assert item.name == "Hospital"
        assert item.type is ItemType.SET
        assert item.category_id == 277

    def it_reads_how_each_entry_appears(self):
        entries = parse_superset_entries(
            [
                {
                    "color_id": 6,
                    "entries": [
                        {
                            "item": {"no": "555-1", "type": "SET"},
                            "quantity": 1,
                            "appears_as": "R",
                        }
                    ],
                }
            ]
        )

        assert entries[0].entries[0].appear_as is AppearAs.REGULAR


class describe_parse_subset_entries:
    def it_groups_the_included_items_by_matching(self):
        entries = parse_subset_entries(
            [
                {"match_no": 1, "entries": []},
                {"match_no": 2, "entries": []},
            ]
        )

        assert entries[0].match_no == 1
        assert entries[1].match_no == 2

    def it_reads_the_nested_item_reference(self):
        entries = parse_subset_entries(
            [
                {
                    "match_no": 1,
                    "entries": [
                        {
                            "item": {
                                "no": "3001old",
                                "name": "Brick 2 x 4 without Cross Supports",
                                "type": "PART",
                                "categoryID": 5,
                            },
                            "color_id": 5,
                            "quantity": 1,
                            "extra_quantity": 0,
                            "is_alternate": False,
                            "is_counterpart": False,
                        }
                    ],
                }
            ]
        )

        item = entries[0].entries[0].item
        assert item.no == "3001old"
        assert item.type is ItemType.PART
        assert item.category_id == 5

    def it_marks_the_alternate_and_the_counterpart_entries(self):
        entries = parse_subset_entries(
            [
                {
                    "match_no": 1,
                    "entries": [
                        {
                            "item": {"no": "3001old", "type": "PART"},
                            "color_id": 5,
                            "quantity": 1,
                            "extra_quantity": 0,
                            "is_alternate": False,
                            "is_counterpart": False,
                        },
                        {
                            "item": {"no": "3001old", "type": "PART"},
                            "color_id": 7,
                            "quantity": 1,
                            "extra_quantity": 0,
                            "is_alternate": True,
                            "is_counterpart": False,
                        },
                    ],
                }
            ]
        )

        assert entries[0].entries[0].is_alternate is False
        assert entries[0].entries[1].is_alternate is True


def _price_guide_payload(price_detail: list[dict[str, object]]) -> dict[str, object]:
    return {
        "item": {"no": "7644-1", "type": "SET"},
        "new_or_used": "N",
        "currency_code": "USD",
        "min_price": "96.0440",
        "max_price": "695.9884",
        "avg_price": "162.3401",
        "qty_avg_price": "155.3686",
        "unit_quantity": 298,
        "total_quantity": 359,
        "price_detail": price_detail,
    }


class describe_parse_price_guide:
    def it_reads_the_price_statistics(self):
        guide = parse_price_guide(_price_guide_payload([]))

        assert guide.item.no == "7644-1"
        assert guide.new_or_used is NewOrUsed.NEW
        assert guide.currency_code == "USD"
        assert guide.unit_quantity == 298
        assert guide.total_quantity == 359

    def it_reads_every_price_as_a_decimal(self):
        guide = parse_price_guide(_price_guide_payload([]))

        assert guide.min_price == Decimal("96.0440")
        assert guide.max_price == Decimal("695.9884")
        assert guide.avg_price == Decimal("162.3401")
        assert guide.qty_avg_price == Decimal("155.3686")

    def it_reads_the_stock_shaped_price_detail_rows(self):
        guide = parse_price_guide(
            _price_guide_payload(
                [
                    {
                        "quantity": 2,
                        "qunatity": 2,
                        "unit_price": "96.0440",
                        "shipping_available": True,
                    }
                ]
            )
        )

        detail = guide.price_detail[0]
        assert detail.quantity == 2
        assert detail.unit_price == Decimal("96.0440")
        assert detail.shipping_available is True

    def it_reads_the_sold_shaped_price_detail_rows(self):
        guide = parse_price_guide(
            _price_guide_payload(
                [
                    {
                        "quantity": 1,
                        "unit_price": "98.2618",
                        "seller_country_code": "CZ",
                        "buyer_country_code": "HK",
                        "date_ordered": "2013-12-30T14:59:01.850Z",
                    }
                ]
            )
        )

        detail = guide.price_detail[0]
        assert detail.seller_country_code == "CZ"
        assert detail.buyer_country_code == "HK"

    def it_reads_the_order_date_as_a_datetime(self):
        guide = parse_price_guide(
            _price_guide_payload(
                [
                    {
                        "quantity": 1,
                        "unit_price": "98.2618",
                        "date_ordered": "2013-12-30T14:59:01.850Z",
                    }
                ]
            )
        )

        assert guide.price_detail[0].date_ordered == datetime.fromisoformat(
            "2013-12-30T14:59:01.850Z"
        )

    def it_ignores_the_misspelled_qunatity_field(self):
        guide = parse_price_guide(
            _price_guide_payload([{"quantity": 2, "qunatity": 999, "unit_price": "96.0440"}])
        )

        assert guide.price_detail[0].quantity == 2


class describe_parse_known_colors:
    def it_reads_the_color_ids_and_the_quantities(self):
        colors = parse_known_colors([{"color_id": "1", "quantity": "10"}])

        assert colors == (KnownColor(color_id=1, quantity=10),)
