"""Behaviour specs for the top-level `brikz` package."""

from __future__ import annotations

import re

import brikz


class describe_the_package:
    def it_has_a_valid_version_property(self):
        assert re.fullmatch(r"\d\.\d{1,3}\.\d{1,3}", brikz.__version__)

    def it_exports_the_documented_names(self):
        for name in brikz.__all__:
            assert hasattr(brikz, name)
