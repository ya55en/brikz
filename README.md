# brikz

The BrickLink API async+sync python wrapper

> **Pre-alpha.** The transport and the Catalog Item endpoints are written; the
> rest of the API is not, and nothing here has a stable API yet. Don't pin it as
> a dependency.

## The BrickLink API

[BrickLink](https://www.bricklink.com) is the largest LEGO marketplace, and exposes a
REST API for stores to manage their catalog, inventory, and orders. It requires
OAuth 1.0a-signed requests; see the [API docs](https://www.bricklink.com/v3/api.page)
and the [API consumer console](https://www.bricklink.com/v2/api/register_consumer.page)
where credentials are issued.

## Example

`brikz` has both a sync and an async client. An API call is a value:
`ItemRef(ItemType.SET, '6608-1').get()` returns a `Request` carrying its path,
its parameters and how to read the answer, and the client you hand it to
executes it. Sync and async therefore differ in exactly one method -- `send` --
rather than once per endpoint.

```python
import asyncio
import os

import brikz
from brikz import ItemRef, ItemType, NewOrUsed

credentials = brikz.BrickLinkCredentials(
    consumer_key=os.environ['BRICKLINK_CONSUMER_KEY'],
    consumer_secret=os.environ['BRICKLINK_CONSUMER_SECRET'],
    token=os.environ['BRICKLINK_TOKEN'],
    token_secret=os.environ['BRICKLINK_TOKEN_SECRET'],
)

# A reference to one catalog item, and a request to ask about it.
# Both are plain values -- nothing has touched the network yet.
set_6608 = ItemRef(ItemType.SET, '6608-1')
print(set_6608.get().path)  # /items/SET/6608-1

# Sending the request via the sync client:
with brikz.BrickLink(credentials) as client:
    item = client.send(set_6608.get())
    print(item.name, item.year_released)

    # The same reference builds every other Catalog Item request:
    prices = client.send(set_6608.price_guide(new_or_used=NewOrUsed.USED))
    groups = client.send(set_6608.subsets(break_minifigs=True))

    # A parsed item is itself a key -- ask it the next question:
    part = groups[0].entries[0].item
    colors = client.send(part.ref().known_colors())

# The same request, sent by the async client:
async def async_call():
    async with brikz.AsyncBrickLink(credentials) as client:
        item = await client.send(set_6608.get())
        print(item.name)

asyncio.run(async_call())
```

### What an `ItemRef` is

An `ItemRef` is two pieces of data -- an item type and an item number -- and
nothing else:

```python
>>> ItemRef(ItemType.PART, '3001')
ItemRef(type=<ItemType.PART: 'PART'>, no='3001')
```

If you have used other API wrappers, you may expect that object to be a live
thing -- one that holds a connection, where calling a method fetches something.
It is not, and they do not. An `ItemRef` is closer to a file path than to an
open file: it *names* an item, and by itself it never talks to BrickLink.

So its methods do not fetch anything either. They describe a fetch:

```python
>>> ItemRef(ItemType.PART, '3001').known_colors()
Request(path='/items/PART/3001/colors', parse=<function parse_known_colors at 0x...>, params={})
```

That `Request` is a plain value too: a path, some query parameters, and the
function that will turn the answer into a model. Nothing has been sent yet. To
actually get the colors, hand it to a client:

```python
colors = client.send(ItemRef(ItemType.PART, '3001').known_colors())
```

Three things follow from that split, and they are the whole reason for it:

- **One request works with both clients.** `send` is the only method that
  differs between `BrickLink` and `AsyncBrickLink`, so the two spellings in the
  example above differ only in the `await`. There is no separate async version
  of every endpoint to learn.
- **You can look before you leap.** A request can be printed, logged, stored,
  compared, or collected into a list and sent later. Tests build requests and
  check them without touching a network.
- **Making one is free.** No connection, no handshake, nothing to close. Build a
  thousand in a loop if you like.

Because an `ItemRef` is only its two fields, two of them naming the same item
are equal and interchangeable, and either can be used as a dictionary key:

```python
>>> ItemRef(ItemType.PART, '3001') == ItemRef(ItemType.PART, '3001')
True
```

There is one thing an `ItemRef` does check: a blank type or number is refused
the moment you make one, because the URL is `brikz`'s to get right. Everything
else -- whether the item exists, whether the color is valid -- is BrickLink's
call, and comes back as an error from `send`.

Finally, `Item.ref()` closes the loop: any item in a response can turn itself
back into an `ItemRef` and become the subject of the next question. That is what
the `part.ref().known_colors()` line in the example does.

### How the API is laid out

Every Catalog Item endpoint hangs off `ItemRef`: `get`, `image`, `supersets`,
`subsets`, `price_guide` and `known_colors`. Each sub-API arrives as its own
module with its own reference type -- `catalog_item`, then `category`, `color`,
`order` -- and `send` never changes.

### What `brikz` exports

The whole vocabulary lands at the top level: the clients, `Request`, the errors,
BrickLink's enumerations, `ItemRef`, and the models a response parses into
(`Item`, `PriceGuide`, `SubsetEntry` and the rest). The machinery that builds
and reads requests stays behind its module -- `catalog_item.parse_item`,
`catalog_item.item_path`.

### What `send` raises

`send` raises `BrikzError` or an `httpx` exception, and nothing else.
`BrickLinkAPIError` says the envelope came back with a non-success code,
`MalformedResponseError` that the answer was not an envelope at all, and
`ResponseParseError` that the envelope was fine but its data could not be read
-- it carries the request and the offending payload, and the original failure
as its `__cause__`. Transport failures (timeouts, connection errors, an error
page) surface as the `httpx` exceptions they are: `httpx` is a public
dependency here, not an implementation detail.

### Logging

`brikz` configures no logging of its own -- it only attaches a `NullHandler`, so
nothing is emitted until your application asks for it. At `DEBUG` you get the
whole story of a call: the request as it was built, the path and query
parameters, the HTTP status and size, what the envelope said, and what the
answer parsed into. Failures narrate themselves before they raise.

```python
logging.basicConfig(level=logging.DEBUG)
```

```
DEBUG brikz.core: sending Request(path='/items/SET/6608-1', parse=<function parse_item ...>, params={})
DEBUG brikz.core: GET /items/SET/6608-1 params={}
DEBUG brikz.core: HTTP 200 for /items/SET/6608-1 (93 bytes)
DEBUG brikz.wire: body of /items/SET/6608-1: {"meta":{"code":200},"data":{"no":"6608-1",...}}
DEBUG brikz.core: envelope ok: meta.code=200, data is dict of 4
DEBUG brikz.core: /items/SET/6608-1 parsed into Item
```

Raw response bodies are logged verbatim and untruncated, but on their own
logger, `brikz.wire`, because they are the one part you may want off while
keeping the rest: they are unbounded (a `subsets` response runs to hundreds of
KB), and an order or member response carries personal data into wherever your
logs go. To keep everything else and drop the bodies:

```python
logging.getLogger('brikz.wire').setLevel(logging.INFO)
```

Sensitive data never reaches a log line (only `consumer_key` is ever logged
from the credential keys).

## Where things stand

| | state |
|---|---|
| `BrickLink`, `AsyncBrickLink`, `send` | written |
| Catalog Item -- `ItemRef`, six endpoints, their parsers and models | written |
| Category, Color, Order, and the rest | not started |

## Development

The project is managed via [uv](https://docs.astral.sh/uv/), which is a hard dependency.

The `Makefile` is intended to make developers' life easier.

- `make test` will not only run the tests but also build the virtual environment
  if needed. It is quiet by default; `make test PYTEST_ARGS=` gives the full
  spec output, and anything else in `PYTEST_ARGS` is passed to pytest.

- `make format` and `make lint` -- they do what their names suggest ;)

### Behavior-based testing

Tests are written as behavior specs: a `describe_<Unit>` class groups `it_<does_something>`
methods, each stating one expected behavior in plain English. The
[pytest-spec](https://github.com/pchomik/pytest-spec) plugin renders these as readable,
indented output instead of raw test names.
