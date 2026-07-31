"""brikz - a BrickLink API sync+async Python wrapper."""

__version__ = "0.0.0"


YEL = "\033[33m"
BLU = "\033[94m"
BLD = "\033[1;97m"
ORN = "\033[38;5;208m"
GRN = "\033[32m"
RST = "\033[0m"


print(f"""
  {YEL}The BrickLink API sync+async Python wrapper{RST}

  {ORN}Not there yet.{RST} {BLD}brikz has no working functionality —
  importing it raises `NotImplementedError`. Don’t add it as a
  dependency yet. Working hard to bring this to you all.{RST}

  {BLU}Coming soon...{RST}

  {BLU}`brikz` has both a sync and an async client. The API wrapper accepts
  either; if you pass it an async client, you need to await the API calls;
  otherwise just call it synchronously.{RST}

  {YEL}Watch this space: https://github.com/ya55en/brikz !
  {GRN}Enjoy! ;){RST}
""")


raise NotImplementedError(f"{YEL}Coming sooooooon ;){RST}\n")
