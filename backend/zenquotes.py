"""ZenQuotes batch provider. The MatrixPortal never calls ZenQuotes directly."""

import json
import unicodedata
from urllib.request import Request, urlopen


MAX_QUOTE_CHOICES = 3


class ZenQuotesProvider:
    URL = "https://zenquotes.io/api/quotes"

    @staticmethod
    def _ascii(value, max_length):
        if not isinstance(value, str) or not value.strip():
            return None
        value = value.replace("\u2018", "'").replace("\u2019", "'")
        value = value.replace("\u201c", '"').replace("\u201d", '"')
        value = value.replace("\u2013", "-").replace("\u2014", "-")
        value = unicodedata.normalize("NFKD", value)
        value = " ".join(value.encode("ascii", "ignore").decode("ascii").split())
        # Parse only the plain-text fields (never the API's HTML 'h').
        if not value or "<" in value or ">" in value or len(value) > max_length:
            return None
        return value

    def fetch(self):
        request = Request(self.URL, headers={
            "Accept": "application/json",
            "User-Agent": "LED information display (github.com/antonio1000homens/led)",
        })
        with urlopen(request, timeout=5) as response:
            data = json.load(response)
        if not isinstance(data, list) or not data:
            raise ValueError("ZenQuotes API returned an empty or invalid batch")
        quotes, seen = [], set()
        for entry in data[:100]:
            if not isinstance(entry, dict):
                continue
            quote = self._ascii(entry.get("q"), 420)
            author = self._ascii(entry.get("a"), 120)
            if not quote or not author:
                continue
            key = (quote.casefold(), author.casefold())
            if key not in seen:
                seen.add(key)
                quotes.append({"quote": quote, "author": author})
        if not quotes:
            raise ValueError("ZenQuotes API returned no usable plain-text quotes")
        return quotes[:MAX_QUOTE_CHOICES]
