import os
import json

def _parse_stations() -> list[dict]:
    raw = os.environ.get("STATIONS")
    if raw:
        return json.loads(raw)
    # fallback for local dev — override via STATIONS env var in Docker
    return [
        {"id": "44946",  "nickname": "Costco North"},
        {"id": "164236", "nickname": "Murphy Express 144th"},
        {"id": "119297", "nickname": "King Soopers 136th"},
        {"id": "208619", "nickname": "Costco Work"},
    ]

STATIONS = _parse_stations()
CACHE_TTL_SECONDS = int(os.environ.get("CACHE_TTL_SECONDS", 900))
PORT = int(os.environ.get("PORT", 5050))
