from __future__ import annotations

import logging
from contextlib import contextmanager
from dataclasses import dataclass, field
from functools import cache
from types import NoneType
from typing import TYPE_CHECKING, Any, Self

import httpx
from authlib.integrations.httpx_client import OAuth1Auth

if TYPE_CHECKING:
    from collections.abc import Callable, Generator

log = logging.getLogger(__name__)

# Raw response bodies get their own channel: they are long, and an order or a
# member response carries personal data. Silence with
# `logging.getLogger("brikz.wire").setLevel(logging.INFO)`.
wire = logging.getLogger("brikz.wire")

BASE_URL = "https://api.bricklink.com/api/store/v1"

# BrickLink's envelope "data", once unwrap has checked its shape.
type JsonStruct = dict[str, Any] | list[Any]


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


@dataclass(frozen=True, slots=True)
class Request[T]:
    """One API call, as a value: where to go, and how to read the answer.

    Built by the sub-API modules (`catalog_item.get_item(...)`) and executed
    by `BrickLink.send` / `AsyncBrickLink.send`. Sync and async differ in
    those two methods and nowhere else.
    """

    path: str
    parse: Callable[[JsonStruct | None], T]
    params: dict[str, Any] = field(default_factory=dict)


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
        log.debug(
            "AsyncBrickLink ready: base_url=%s consumer_key=%s user_agent=%s",
            base_url,
            credentials.consumer_key,
            user_agent(),
        )

    async def send[T](self, request: Request[T]) -> T:
        """Execute a request and read its answer into the request's own type.

        Requests come from the sub-API modules -- `ItemRef(...).get()` and its
        siblings.

        Raises `BrikzError` or an `httpx` exception, nothing else. `BrikzError`
        can be a `BrickLinkAPIError` when the envelope reports a failure,
        `MalformedResponseError` when the answer is no envelope at all,
        `ResponseParseError` when its data cannot be read, and `httpx`'s own
        exceptions when the call never got that far.
        """
        log.debug("sending %s", request)
        data = await self.get(request.path, request.params)

        with _handle_parse_errors(request, data):
            result = request.parse(data)

        log.debug("%s parsed into %s", request.path, _describe(result))
        return result

    async def get(self, path: str, params: dict[str, Any] | None = None) -> JsonStruct | None:
        query = clean_params(params)
        log.debug("GET %s params=%r", path, query)

        response = await self._client.get(path, params=query)
        log.debug("HTTP %d for %s (%d bytes)", response.status_code, path, len(response.content))
        _log_body(path, response)

        return unwrap(response)

    async def aclose(self) -> None:
        log.debug("closing AsyncBrickLink")
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
        log.debug(
            "BrickLink ready: base_url=%s consumer_key=%s user_agent=%s",
            base_url,
            credentials.consumer_key,
            user_agent(),
        )

    def send[T](self, request: Request[T]) -> T:
        """Execute a request and read its answer into the request's own type.

        Requests come from the sub-API modules -- `ItemRef(...).get()` and its
        siblings.

        Raises `BrikzError` or an `httpx` exception, nothing else:
        `BrickLinkAPIError` when the envelope reports a failure,
        `MalformedResponseError` when the answer is no envelope at all,
        `ResponseParseError` when its data cannot be read, and `httpx`'s own
        exceptions when the call never got that far.
        """
        log.debug("sending %s", request)
        data = self.get(request.path, request.params)

        with _handle_parse_errors(request, data):
            result = request.parse(data)

        log.debug("%s parsed into %s", request.path, _describe(result))
        return result

    def get(self, path: str, params: dict[str, Any] | None = None) -> JsonStruct | None:
        query = clean_params(params)
        log.debug("GET %s params=%r", path, query)

        response = self._client.get(path, params=query)
        log.debug("HTTP %d for %s (%d bytes)", response.status_code, path, len(response.content))
        _log_body(path, response)

        return unwrap(response)

    def close(self) -> None:
        log.debug("closing BrickLink")
        self._client.close()

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()


def unwrap(response: httpx.Response) -> JsonStruct | None:
    """Validate a BrickLink API response envelope and return its "data" field."""
    if not response.content:
        # A body-less response, like a 204 from a DELETE, is legit.
        log.debug("empty body on HTTP %d -- no envelope to read", response.status_code)
        response.raise_for_status()
        return None

    try:
        body: Any = response.json()
        meta: Any = body["meta"]
        code = int(meta["code"])

    except (ValueError, TypeError, KeyError) as err:
        # Not a BrickLink envelope (gateway error page, HTML, ...).
        log.debug("no envelope in the body: %r", response.text[:200])
        response.raise_for_status()
        raise MalformedResponseError(response) from err

    if code // 100 != 2:  # not a 2xx response
        log.debug("envelope reports meta.code=%d: %r", code, meta)
        raise BrickLinkAPIError(
            code=code,
            message=meta.get("message", "n/a"),
            description=meta.get("description", "n/a"),
        )

    # The envelope is untyped JSON; assert the shape at this single boundary
    # rather than leaking Any into every caller.
    data = body.get("data")
    if not isinstance(data, (dict, list, NoneType)):
        log.debug("envelope data is neither object nor list: %r", data)
        raise MalformedResponseError(response)

    log.debug("envelope ok: meta.code=%d, data is %s", code, _describe(data))
    return data  # pyright: ignore[reportUnknownVariableType]


@contextmanager
def _handle_parse_errors(request: Request[Any], data: JsonStruct | None) -> Generator[None]:
    """Turn any failure of a request's parser into one error type."""

    try:
        yield

    except BrikzError:
        raise

    except _PARSE_FAILURES as err:
        log.debug("%s failed on %r: %r", request.parse, data, err)
        raise ResponseParseError(request, data) from err


def _log_body(path: str, response: httpx.Response) -> None:
    """Log the response body verbatim, decoding it only if anyone is listening."""
    if wire.isEnabledFor(logging.DEBUG):
        wire.debug("body of %s: %s", path, response.text)


def _describe(value: Any) -> str:
    """Name a value for a log line without spelling the whole thing out."""
    name: str = type(value).__name__
    if isinstance(value, (dict, list, tuple)):
        return f"{name} of {len(value)}"  # pyright: ignore[reportUnknownArgumentType]

    return name


# What a parser reading a payload it did not expect can hit: a missing key, a
# field of the wrong type, an unparsable number or date.
_PARSE_FAILURES = (ValueError, TypeError, LookupError, AttributeError, ArithmeticError)


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


class ResponseParseError(BrikzError):
    """Raised when the envelope was fine but its data could not be read."""

    def __init__(self, request: Request[Any], data: JsonStruct | None) -> None:
        self.request = request
        self.data = data
        super().__init__(f"could not read the response to {request.path}: {data!r:.200}")


@cache
def user_agent() -> str:
    from brikz import __version__

    return f"brikz/{__version__}"
