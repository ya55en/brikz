# brikz

The BrickLink API async+sync python wrapper

> **Not there yet.** `brikz` has no working functionality. Don't add it
> as a dependency yet. Working hard to bring this to you all.

`brikz` has both a sync and an async client. The API wrapper accepts either; if you pass it an async client, you need to `await` the API calls; otherwise just call it synchronously.

## Example

(The API below is the intended shape, not something you can run today.)

```python
import asyncio
import os

import brikz

credentials = brikz.BrickLinkCredentials(
    consumer_key=os.environ['BRICKLINK_CONSUMER_KEY'],
    consumer_secret=os.environ['BRICKLINK_CONSUMER_SECRET'],
    token=os.environ['BRICKLINK_TOKEN'],
    token_secret=os.environ['BRICKLINK_TOKEN_SECRET'],
)

# BrickLink gives back the sync client:
with brikz.BrickLink(credentials) as client:
    item = client.catalog_item.get_item('SET', '6608-1')
    print(item)

async def async_call():
    # AsyncBrickLink gives back (surprise!) the async client ;)
    async with brikz.AsyncBrickLink(credentials) as client:
        item = await client.catalog_item.get_item('SET', '6608-1')
        print(item)

asyncio.run(async_call())
```

## The BrickLink API

[BrickLink](https://www.bricklink.com) is the largest LEGO marketplace, and exposes a
REST API for stores to manage their catalog, inventory, and orders. It requires
OAuth 1.0a-signed requests; see the [API docs](https://www.bricklink.com/v3/api.page)
and the [API consumer console](https://www.bricklink.com/v2/api/register_consumer.page)
where credentials are issued.

## Behavior-based testing

Tests are written as behavior specs: a `describe_<Unit>` class groups `it_<does_something>`
methods, each stating one expected behavior in plain English. The
[pytest-spec](https://github.com/pchomik/pytest-spec) plugin renders these as readable,
indented output instead of raw test names.
