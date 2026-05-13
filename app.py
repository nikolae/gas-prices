import asyncio
import time
import logging
from flask import Flask, render_template, redirect, url_for
from py_gasbuddy import GasBuddy
from config import STATIONS, CACHE_TTL_SECONDS, PORT

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

app = Flask(__name__)

_price_cache: dict = {}
_cache_timestamps: dict = {}


def _parse_prices(raw) -> list[dict]:
    """Extract a flat list of {grade, price, unit, posted_time} from py-gasbuddy response."""
    prices = []
    if not raw:
        return prices

    # py-gasbuddy returns a dict with a nested structure; navigate defensively
    try:
        station_data = raw if isinstance(raw, dict) else {}
        fuel_prices = (
            station_data.get("station", {}).get("prices")
            or station_data.get("prices")
            or []
        )
        for entry in fuel_prices:
            grade = entry.get("fuelProduct", "Unknown")
            credit = entry.get("credit") or {}
            cash = entry.get("cash") or {}
            price = credit.get("price") or cash.get("price")
            unit = credit.get("priceUnit") or cash.get("priceUnit") or "per gallon"
            posted = credit.get("postedTime") or cash.get("postedTime")
            if price is not None:
                prices.append(
                    {
                        "grade": _friendly_grade(grade),
                        "price": float(price),
                        "unit": unit,
                        "posted_time": posted,
                    }
                )
    except Exception as exc:
        log.warning("Could not parse price data: %s — raw=%s", exc, raw)

    return prices


def _parse_station_meta(raw) -> dict:
    """Extract station name and address from py-gasbuddy response."""
    if not raw:
        return {}
    try:
        station = raw.get("station", raw)
        address = station.get("address", {})
        return {
            "name": station.get("name", ""),
            "address": ", ".join(
                filter(
                    None,
                    [
                        address.get("line1", ""),
                        address.get("city", ""),
                        address.get("state", ""),
                    ],
                )
            ),
        }
    except Exception:
        return {}


def _friendly_grade(raw: str) -> str:
    mapping = {
        "regular_gas": "Regular",
        "midgrade_gas": "Midgrade",
        "premium_gas": "Premium",
        "diesel": "Diesel",
        "e85": "E85",
        "ub_e85": "E85",
    }
    return mapping.get(raw.lower(), raw.replace("_", " ").title())


async def _fetch_station(station_id: str) -> dict | None:
    try:
        gb = GasBuddy()
        return await gb.price_lookup(station_id=station_id)
    except Exception as exc:
        log.error("Failed to fetch station %s: %s", station_id, exc)
        return None


def fetch_all_stations() -> list[dict]:
    now = time.time()
    results = []

    for cfg in STATIONS:
        sid = cfg["id"]
        age = now - _cache_timestamps.get(sid, 0)

        if sid not in _price_cache or age > CACHE_TTL_SECONDS:
            log.info("Fetching prices for station %s (%s)", sid, cfg["nickname"])
            raw = asyncio.run(_fetch_station(sid))
            _price_cache[sid] = raw
            _cache_timestamps[sid] = now
        else:
            log.debug("Using cached prices for station %s (age %.0fs)", sid, age)

        raw = _price_cache[sid]
        meta = _parse_station_meta(raw)
        results.append(
            {
                "id": sid,
                "nickname": cfg["nickname"],
                "name": meta.get("name", cfg["nickname"]),
                "address": meta.get("address", ""),
                "prices": _parse_prices(raw),
                "error": raw is None,
                "cached_at": _cache_timestamps[sid],
            }
        )

    return results


@app.route("/")
def index():
    stations = fetch_all_stations()
    return render_template("index.html", stations=stations, now=time.time())


@app.route("/refresh")
def refresh():
    _price_cache.clear()
    _cache_timestamps.clear()
    log.info("Cache cleared — forcing re-fetch")
    return redirect(url_for("index"))


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=PORT, debug=False)
