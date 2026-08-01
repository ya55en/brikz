from __future__ import annotations

from dataclasses import dataclass, field
from functools import cache
from types import NoneType
from typing import TYPE_CHECKING, Any, Self

import httpx
from authlib.integrations.httpx_client import OAuth1Auth

if TYPE_CHECKING:
    from ._types import JsonStruct

BASE_URL = "https://api.bricklink.com/api/store/v1"


@dataclass(frozen=True, slots=True)
class BrickLinkCredentials:
    """OAuth1.0a credentials issued by BrickLink's API consumer console.

    consumer_key is kept visible in repr() to identify which account is in
    play; the three secret fields are redacted so they don't end up in
    tracebacks or logs by accident.
    """

    consumer_key: str
    consumer_secret: str = field(repr=False)
    token: str = field(repr=False)
    token_secret: str = field(repr=False)

    def auth(self) -> httpx.Auth:
        # OAuth1Auth subclasses httpx.Auth at runtime, but the typeshed stub
        # omits that base (typeshed cannot depend on httpx).
        return OAuth1Auth(  # pyright: ignore[reportReturnType]
            client_id=self.consumer_key,
            client_secret=self.consumer_secret,
            token=self.token,
            token_secret=self.token_secret,
        )


class AsyncBrickLink:
    """Thin async HTTP client for the BrickLink API based on `httpx`.

    Credentials are mandatory: the API rejects unsigned requests. Any extra
    keyword arguments go straight to `httpx.AsyncClient` (`timeout`,
    `transport`, ...).
    """

    def __init__(
        self,
        credentials: BrickLinkCredentials,
        base_url: str = BASE_URL,
        **httpx_kwargs: Any,
    ) -> None:
        self._client = httpx.AsyncClient(
            base_url=base_url,
            auth=credentials.auth(),
            headers={"User-Agent": user_agent()},
            **httpx_kwargs,
        )

    async def get(self, path: str, params: dict[str, Any] | None = None) -> JsonStruct | None:
        response = await self._client.get(path, params=clean_params(params))
        return unwrap(response)

    async def aclose(self) -> None:
        await self._client.aclose()

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(self, *exc_info: object) -> None:
        await self.aclose()


class BrickLink:
    """Thin sync HTTP client for the BrickLink API.

    Credentials are mandatory: the API rejects unsigned requests. Any extra
    keyword arguments go straight to `httpx.Client` (`timeout`, `transport`,
    ...).
    """

    def __init__(
        self,
        credentials: BrickLinkCredentials,
        base_url: str = BASE_URL,
        **httpx_kwargs: Any,
    ) -> None:
        self._client = httpx.Client(
            base_url=base_url,
            auth=credentials.auth(),
            headers={"User-Agent": user_agent()},
            **httpx_kwargs,
        )

    def get(self, path: str, params: dict[str, Any] | None = None) -> JsonStruct | None:
        response = self._client.get(path, params=clean_params(params))
        return unwrap(response)

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()


def unwrap(response: httpx.Response) -> JsonStruct | None:
    """Validate a BrickLink API response envelope and return its "data" field."""
    meta: Any = None
    code: int = 0
    parse_error: Exception | None = None

    try:
        body: dict[str, Any] = response.json()
        meta = body["meta"]
        code = int(meta["code"])

    except (ValueError, TypeError, KeyError) as err:
        meta = None
        body = {}
        parse_error = err

    if meta is None:
        # Not a BrickLink envelope (gateway error page, HTML, ...).
        response.raise_for_status()
        raise MalformedResponseError(response) from parse_error

    if code // 100 != 2:  # not a 2xx response
        raise BrickLinkAPIError(
            code=code,
            message=meta.get("message", "n/a"),
            description=meta.get("description", "n/a"),
        )

    # The envelope is untyped JSON; assert the shape at this single boundary
    # rather than leaking Any into every caller.
    data = body.get("data")

    # `None` is legit for body-less responses, like a DELETE response
    if not isinstance(data, (dict, list, NoneType)):
        raise MalformedResponseError(response)

    return data  # pyright: ignore[reportUnknownVariableType]


def clean_params(params: dict[str, Any] | None) -> dict[str, Any]:
    """Drop unset (None) query parameters."""
    return {key: value for key, value in (params or {}).items() if value is not None}


class BrikzError(Exception):
    """Base for every custom error raised by brikz."""


class BrickLinkAPIError(BrikzError):
    """Raised when the BrickLink API responds with a non-success meta.code."""

    def __init__(self, code: int, message: str, description: str = "") -> None:
        self.code = code
        self.message = message
        self.description = description

        super().__init__(f"[{code}] {message}: {description}")


class MalformedResponseError(BrikzError):
    """Raised when the response is not a BrickLink envelope at all."""

    def __init__(self, response: httpx.Response) -> None:
        self.response = response
        super().__init__(f"HTTP {response.status_code}: {response.text[:200]!r}")


@cache
def user_agent() -> str:
    from brikz import __version__

    return f"brikz/{__version__}"
