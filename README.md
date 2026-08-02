# brikz

The BrickLink API async+sync python wrapper

> **Pre-alpha.** The transport and the Catalog Item endpoints are written; the
> rest of the API is not, and the call shape below is going to change. Don't pin
> it as a dependency yet.

`brikz` has both a sync and an async client. An API call is a value:
`catalog_item.get_item(ItemType.SET, '6608-1')` returns a `Request` carrying its
path, its parameters and how to read the answer, and the client you hand it to
executes it. Sync and async therefore differ in exactly one method -- `send` --
rather than once per endpoint.

## Where things stand

| | state |
|---|---|
| `BrickLink`, `AsyncBrickLink`, `send` | written |
| Catalog Item -- six endpoints, their parsers and models | written |
| Category, Color, Order, and the rest | not started |

Nothing here has a stable API. In particular the six flat `get_*` builders are
on their way out: they will become methods on an `ItemRef` that names the item
once, so `catalog_item.get_subsets(ItemType.SET, '6608-1', break_minifigs=True)`
becomes `ItemRef(ItemType.SET, '6608-1').subsets(break_minifigs=True)`. See
`docs/design/` for that decision and what it is meant to buy.

## Example

```python
import asyncio
import os

import brikz
from brikz import ItemType, NewOrUsed, catalog_item

credentials = brikz.BrickLinkCredentials(
    consumer_key=os.environ['BRICKLINK_CONSUMER_KEY'],
    consumer_secret=os.environ['BRICKLINK_CONSUMER_SECRET'],
    token=os.environ['BRICKLINK_TOKEN'],
    token_secret=os.environ['BRICKLINK_TOKEN_SECRET'],
)

# A request is a plain value. Building one touches no network:
get_item_request = catalog_item.get_item(ItemType.SET, '6608-1')
print(get_item_request.path)  # /items/SET/6608-1

# Sending it via the sync client:
with brikz.BrickLink(credentials) as client:
    item = client.send(get_item_request)
    print(item.name, item.year_released)

    # Every other Catalog Item endpoint is built the same way:
    prices = client.send(
        catalog_item.get_price_guide(ItemType.SET, '6608-1', new_or_used=NewOrUsed.USED)
    )
    parts = client.send(
        catalog_item.get_subsets(ItemType.SET, '6608-1', break_minifigs=True)
    )

# The same request, sent by the async client:
async def async_call():
    async with brikz.AsyncBrickLink(credentials) as client:
        item = await client.send(get_item_request)
        print(item.name)

asyncio.run(async_call())
```

The same `Request` goes to either client, so the two spellings above differ only
in the `await`. Because building one is pure, requests can be made, inspected,
logged or collected before anything goes out.

`brikz` itself exports the clients, `Request`, the errors and BrickLink's
enumerations; the models a response parses into -- `Item`, `PriceGuide`,
`SubsetEntry` and the rest -- live in `brikz.models`. Each sub-API arrives as its
own module: `catalog_item`, then `category`, `color`, `order`.

## The BrickLink API

[BrickLink](https://www.bricklink.com) is the largest LEGO marketplace, and exposes a
REST API for stores to manage their catalog, inventory, and orders. It requires
OAuth 1.0a-signed requests; see the [API docs](https://www.bricklink.com/v3/api.page)
and the [API consumer console](https://www.bricklink.com/v2/api/register_consumer.page)
where credentials are issued.

## Development

The project is managed via [uv](https://docs.astral.sh/uv/), which is a hard dependency.

The `Makefile` is intended to make developers' life easier.

- `make test` will not only run the tests (spec mode) but also build the virtual
  environment if needed.

- `make format` and `make lint` -- they do what their names suggest ;)

### Behavior-based testing

Tests are written as behavior specs: a `describe_<Unit>` class groups `it_<does_something>`
methods, each stating one expected behavior in plain English. The
[pytest-spec](https://github.com/pchomik/pytest-spec) plugin renders these as readable,
indented output instead of raw test names.
