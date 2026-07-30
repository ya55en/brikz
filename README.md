# brikz

The BrickLink API async+sync python wrapper

> **Not there yet.** `brikz` has no working functionality — importing it raises
> `NotImplementedError`. Don't add it as a dependency yet. Working hard to
> bring this to you all.

`brikz` has both a sync and an async client. The API wrapper accepts either; if you pass an async client to it, you need to `await` the API calls; otherwise just call it synchronously.

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
