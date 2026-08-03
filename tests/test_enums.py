"""Behaviour specs for the `enums` package -- `LenientStrEnum` in `enums.shared`.

Stubs only -- see test_catalog_item.py for the arrangement.
"""

from __future__ import annotations

from urllib.parse import quote

import pytest

from brikz.enums.shared import ItemType


class describe_a_lenient_enum:
    def it_resolves_a_value_it_knows(self):
        assert ItemType('SET') is ItemType.SET

    def it_accepts_a_value_bricklink_added_after_us(self):
        member = ItemType('NEW_TYPE')

        assert isinstance(member, ItemType)
        assert member.value == 'NEW_TYPE'

    def it_keeps_an_unknown_value_reachable(self):
        # Without caching, every lookup would build a fresh, non-identical
        # member -- the value would be "reachable" but never the same object.
        assert ItemType('NEW_TYPE') is ItemType('NEW_TYPE')

    def it_compares_equal_to_its_own_string_value(self):
        assert ItemType('NEW_TYPE') == 'NEW_TYPE'

    def it_goes_into_a_url_as_its_value(self):
        assert quote(ItemType('NEW_TYPE')) == 'NEW_TYPE'

    def it_refuses_a_non_string_value(self):
        with pytest.raises(ValueError, match='123'):
            ItemType(123)  # pyright: ignore[reportArgumentType]

    def it_leaves_a_synthesized_member_out_of_iteration(self):
        ItemType('NEW_TYPE')

        assert 'NEW_TYPE' not in list(ItemType)
