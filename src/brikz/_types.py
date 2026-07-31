"""Typing hints stuff."""

from typing import Any, Protocol

type JsonStruct = dict[str, Any] | list[Any]


class SupportsGet[R](Protocol):
    """Anything with a `get()` shaped like `BrickLink.get` / `AsyncBrickLink.get`.

    Resource classes are generic over `R` so that a `BrickLink` (`get()` ->
    `JsonStruct | None`) and an `AsyncBrickLink` (`get()` -> a coroutine of
    the same) each carry their own, fully-narrowed return type instead of a
    union neither call style can use.
    """

    def get(self, path: str, params: dict[str, Any] | None = None) -> R: ...
