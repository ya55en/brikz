"""Behaviour specs for the `enums` package -- `LenientStrEnum` in `enums.shared`.

Stubs only -- see test_catalog_item.py for the arrangement.
"""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.skip(reason="design stubs -- no implementation yet")


class describe_a_lenient_enum:
    def it_resolves_a_value_it_knows(self): ...

    def it_accepts_a_value_bricklink_added_after_us(self): ...

    def it_keeps_an_unknown_value_reachable(self): ...

    def it_compares_equal_to_its_own_string_value(self): ...

    def it_goes_into_a_url_as_its_value(self): ...
