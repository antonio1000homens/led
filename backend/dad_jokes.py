"""Fetch a compact, safe-to-render dad joke without board-side network calls."""

import json
import unicodedata
from urllib.request import Request, urlopen


class DadJokeProvider:
    URL = "https://icanhazdadjoke.com/"

    def fetch(self):
        request = Request(self.URL, headers={
            "Accept": "application/json",
            "User-Agent": "LED information display (github.com/antonio1000homens/led)",
        })
        with urlopen(request, timeout=5) as response:
            data = json.load(response)
        joke = data.get("joke") if isinstance(data, dict) else None
        if not isinstance(joke, str) or not joke.strip():
            raise ValueError("Dad joke API returned an empty joke")
        # The MatrixPortal's compact 5x7 font is ASCII-oriented.
        joke = unicodedata.normalize("NFKD", joke)
        joke = joke.replace("\u2019", "'").replace("\u2018", "'").replace("\u201c", '"').replace("\u201d", '"')
        joke = joke.encode("ascii", "ignore").decode("ascii")
        return " ".join(joke.split())[:126]
