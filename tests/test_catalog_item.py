"""Behaviour specs for the `catalog_item` module.

Stubs only: each spec names one behaviour and has no body yet. Deleting the
module-level skip below turns this list into the TDD worklist.

Requests are values, so these need no client, no transport and no async: a
builder spec compares a returned `Request` against the path, params and
parser it should carry, and a parser spec feeds it a documented payload and
checks the model that comes back. `send` is specced in test_core.py, where
it lives.
"""

from __future__ import annotations

import pytest

from brikz.catalog_item import (
    get_item,
    get_item_image,
    get_known_colors,
    get_price_guide,
    get_subsets,
    get_supersets,
    item_path,
    parse_item,
    parse_known_colors,
    parse_price_guide,
    parse_subset_entries,
    parse_superset_entries,
)
from brikz.core import clean_params
from brikz.enums.catalog_item import GuideType, Region, VatOption
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


class describe_get_item:
    def it_points_at_the_item_path(self):
        request = get_item(ItemType.SET, "6608-1")

        assert request.path == item_path(ItemType.SET, "6608-1")

    def it_asks_for_no_query_parameters(self):
        request = get_item(ItemType.SET, "6608-1")

        assert clean_params(request.params) == {}

    def it_reads_the_answer_as_an_item(self):
        request = get_item(ItemType.SET, "6608-1")

        assert request.parse is parse_item


class describe_get_item_image:
    def it_points_at_the_image_path_for_the_color(self):
        request = get_item_image(ItemType.SET, "6608-1", 5)

        assert request.path == item_path(ItemType.SET, "6608-1", "images", 5)

    def it_reads_the_answer_as_an_item(self):
        request = get_item_image(ItemType.SET, "6608-1", 5)

        assert request.parse is parse_item


class describe_get_supersets:
    def it_points_at_the_supersets_path(self):
        request = get_supersets(ItemType.PART, "3001old")

        assert request.path == item_path(ItemType.PART, "3001old", "supersets")

    def it_narrows_the_supersets_to_a_single_color(self):
        request = get_supersets(ItemType.PART, "3001old", color_id=5)

        assert request.params["color_id"] == 5

    def it_asks_for_every_color_when_given_no_color(self):
        request = get_supersets(ItemType.PART, "3001old")

        assert clean_params(request.params) == {}

    def it_reads_the_answer_as_superset_entries(self):
        request = get_supersets(ItemType.PART, "3001old")

        assert request.parse is parse_superset_entries


class describe_get_subsets:
    def it_points_at_the_subsets_path(self):
        request = get_subsets(ItemType.SET, "7644-1")

        assert request.path == item_path(ItemType.SET, "7644-1", "subsets")

    def it_narrows_the_subsets_to_a_single_color(self):
        request = get_subsets(ItemType.PART, "3001old", color_id=5)

        assert request.params["color_id"] == 5

    def it_asks_for_the_box_and_the_instruction_when_told_to(self):
        request = get_subsets(ItemType.SET, "7644-1", box=True, instruction=True)

        assert request.params["box"] is True
        assert request.params["instruction"] is True

    def it_breaks_minifigs_and_sets_down_when_told_to(self):
        request = get_subsets(ItemType.SET, "7644-1", break_minifigs=True, break_subsets=True)

        assert request.params["break_minifigs"] is True
        assert request.params["break_subsets"] is True

    def it_leaves_out_every_option_it_is_not_given(self):
        request = get_subsets(ItemType.SET, "7644-1")

        assert clean_params(request.params) == {}

    def it_reads_the_answer_as_subset_entries(self):
        request = get_subsets(ItemType.SET, "7644-1")

        assert request.parse is parse_subset_entries


class describe_get_price_guide:
    def it_points_at_the_price_path(self):
        request = get_price_guide(ItemType.SET, "7644-1")

        assert request.path == item_path(ItemType.SET, "7644-1", "price")

    def it_asks_for_the_sold_statistics_instead_of_the_stock_ones(self):
        request = get_price_guide(ItemType.SET, "7644-1", guide_type=GuideType.SOLD)

        assert request.params["guide_type"] == GuideType.SOLD

    def it_asks_for_the_used_condition(self):
        request = get_price_guide(ItemType.SET, "7644-1", new_or_used=NewOrUsed.USED)

        assert request.params["new_or_used"] == NewOrUsed.USED

    def it_narrows_the_price_guide_to_one_country(self):
        request = get_price_guide(ItemType.SET, "7644-1", country_code="US")

        assert request.params["country_code"] == "US"

    def it_narrows_the_price_guide_to_one_region(self):
        request = get_price_guide(ItemType.SET, "7644-1", region=Region.EUROPE)

        assert request.params["region"] == Region.EUROPE

    def it_asks_for_the_prices_in_a_given_currency(self):
        request = get_price_guide(ItemType.SET, "7644-1", currency_code="EUR")

        assert request.params["currency_code"] == "EUR"

    def it_asks_for_the_prices_with_vat_included(self):
        request = get_price_guide(ItemType.SET, "7644-1", vat=VatOption.INCLUDE)

        assert request.params["vat"] == VatOption.INCLUDE

    def it_leaves_out_every_option_it_is_not_given(self):
        request = get_price_guide(ItemType.SET, "7644-1")

        assert clean_params(request.params) == {}

    def it_reads_the_answer_as_a_price_guide(self):
        request = get_price_guide(ItemType.SET, "7644-1")

        assert request.parse is parse_price_guide


class describe_get_known_colors:
    def it_points_at_the_colors_path(self):
        request = get_known_colors(ItemType.PART, "3001")

        assert request.path == item_path(ItemType.PART, "3001", "colors")

    def it_reads_the_answer_as_known_colors(self):
        request = get_known_colors(ItemType.PART, "3001")

        assert request.parse is parse_known_colors


class describe_parse_item:
    pytestmark = pytest.mark.skip(reason="design stubs -- no implementation yet")

    def it_reads_the_documented_fields(self): ...

    def it_leaves_the_fields_bricklink_omits_unset(self): ...

    def it_reads_the_weight_and_the_dimensions_as_decimals(self): ...

    def it_reads_the_type_as_an_item_type(self): ...

    def it_survives_an_item_type_it_has_never_heard_of(self): ...


class describe_parse_superset_entries:
    pytestmark = pytest.mark.skip(reason="design stubs -- no implementation yet")

    def it_groups_the_including_items_by_color(self): ...

    def it_reads_the_nested_item_reference(self): ...

    def it_reads_how_each_entry_appears(self): ...


class describe_parse_subset_entries:
    pytestmark = pytest.mark.skip(reason="design stubs -- no implementation yet")

    def it_groups_the_included_items_by_matching(self): ...

    def it_reads_the_nested_item_reference(self): ...

    def it_marks_the_alternate_and_the_counterpart_entries(self): ...


class describe_parse_price_guide:
    pytestmark = pytest.mark.skip(reason="design stubs -- no implementation yet")

    def it_reads_the_price_statistics(self): ...

    def it_reads_every_price_as_a_decimal(self): ...

    def it_reads_the_stock_shaped_price_detail_rows(self): ...

    def it_reads_the_sold_shaped_price_detail_rows(self): ...

    def it_reads_the_order_date_as_a_datetime(self): ...

    def it_ignores_the_misspelled_qunatity_field(self): ...


class describe_parse_known_colors:
    pytestmark = pytest.mark.skip(reason="design stubs -- no implementation yet")

    def it_reads_the_color_ids_and_the_quantities(self): ...
