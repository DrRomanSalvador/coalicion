from __future__ import annotations
import hashlib, re
from bs4 import BeautifulSoup
from ..poll_monitor import SourceMonitor, Poll, normalize_party_name, validate_poll

class ElectomaniaMonitor(SourceMonitor):
    """Electomania public-page adapter."""
    def parse(self, body: bytes):
        soup = BeautifulSoup(body, "html.parser")
        text = soup.get_text(" ", strip=True)
        title = soup.title.get_text(" ", strip=True) if soup.title else self.source.get("name", self.source["id"])
        if "elecciones" not in text.lower() or "voto (%)" not in text.lower():
            return [], [{"discovery_id": hashlib.sha256(body).hexdigest(),
                          "title": title, "link": self.source["url"],
                          "publication_raw": "", "source_id": self.source["id"],
                          "validation": "PAGE_FINGERPRINT_ONLY", "alertable": False}]
        date_match = re.search(r"([0-3]?\d)/([01]?\d)/(20\d{2})", text)
        if not date_match:
            return [], []
        pub = f"{date_match.group(3)}-{int(date_match.group(2)):02d}-{int(date_match.group(1)):02d}"
        parties = {}
        for party in ("PP","PSOE","VOX","SUMAR","PODEMOS","ERC","JUNTS","PNV","EH BILDU","BNG","CC","UPN","SALF","SE ACABÓ LA FIESTA"):
            pattern = rf"\b{re.escape(party)}\b[^%]{{0,180}}?([0-9]+(?:[.,][0-9]+)?)%"
            match = re.search(pattern, text, re.I)
            if match:
                parties[normalize_party_name(party)] = float(match.group(1).replace(",", "."))
        if len(parties) < 5:
            return [], []
        poll = Poll(f"{self.source['id']}::{pub}::{title}", pub,
                    self.source.get("pollster") or "Electomanía",
                    self.source["id"], self.source["url"], parties)
        return ([poll], []) if validate_poll(poll)[0] else ([], [])
