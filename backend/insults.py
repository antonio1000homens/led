"""Fetch a safe-to-render insult for the hourly novelty screen."""

import json
import unicodedata
from urllib.request import Request, urlopen


class InsultProvider:
    URL = "https://insult.mattbas.org/api/insult.json"

    def fetch(self):
        request = Request(self.URL, headers={
            "Accept": "application/json",
            "User-Agent": "LED information display (github.com/antonio1000homens/led)",
        })
        with urlopen(request, timeout=5) as response:
            data = json.load(response)
        if not isinstance(data, dict) or data.get("error") is True:
            raise ValueError("Insult API returned an error")
        insult = data.get("insult")
        if not isinstance(insult, str) or not insult.strip():
            raise ValueError("Insult API returned an empty insult")
        insult = unicodedata.normalize("NFKD", insult)
        insult = insult.replace("\u2019", "'").replace("\u2018", "'")
        insult = insult.replace("\u201c", '"').replace("\u201d", '"')
        insult = " ".join(insult.encode("ascii", "ignore").decode("ascii").split())
        if not insult:
            raise ValueError("Insult API returned no renderable text")
        if len(insult) > 420:
            insult = insult[:417].rsplit(" ", 1)[0].rstrip() + "..."
        return insult
