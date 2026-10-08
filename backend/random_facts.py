"""Fetch random English facts on the backend, never from CircuitPython."""

import json
import unicodedata
from urllib.request import Request, urlopen


class RandomFactProvider:
    URL = "https://uselessfacts.jsph.pl/api/v2/facts/random?language=en"

    def fetch(self):
        request = Request(self.URL, headers={
            "Accept": "application/json",
            "User-Agent": "LED information display (github.com/antonio1000homens/led)",
        })
        with urlopen(request, timeout=5) as response:
            data = json.load(response)
        if not isinstance(data, dict):
            raise ValueError("Facts API returned invalid JSON")
        fact_id, text = data.get("id"), data.get("text")
        if not isinstance(fact_id, str) or not fact_id.strip():
            raise ValueError("Facts API returned a missing fact ID")
        if not isinstance(text, str) or not text.strip():
            raise ValueError("Facts API returned an empty fact")
        if data.get("language") != "en":
            raise ValueError("Facts API returned an unexpected language")
        # The board's 5x7 font supports only ASCII; preserve readable punctuation.
        text = unicodedata.normalize("NFKD", text)
        text = text.replace("\u2019", "'").replace("\u2018", "'").replace("\u201c", '"').replace("\u201d", '"')
        text = " ".join(text.encode("ascii", "ignore").decode("ascii").split())
        if not text:
            raise ValueError("Facts API returned no renderable text")
        # Keep payload bounded; fit full facts onto multiple screen pages.
        if len(text) > 420:
            text = text[:417].rsplit(" ", 1)[0].rstrip() + "..."
        return {"id": fact_id.strip(), "text": text, "source": data.get("source") or "uselessfacts.jsph.pl"}
