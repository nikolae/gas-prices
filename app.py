import asyncio
import time
import logging
from flask import Flask, render_template, redirect, url_for, jsonify, request
from py_gasbuddy import GasBuddy
from config import STATIONS, CACHE_TTL_SECONDS, PORT
import storage

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

app = Flask(__name__)

storage.init_db()

_price_cache: dict = {}
_cache_timestamps: dict = {}

_GRADE_KEYS = {
    "regular_gas": "Regular",
    "midgrade_gas": "Midgrade",
    "premium_gas": "Premium",
    "diesel": "Diesel",
    "e85": "E85",
    "ub_e85": "E85",
}


def _parse_prices(raw) -> list[dict]:
    prices = []
    if not raw:
        return prices
    for key, label in _GRADE_KEYS.items():
        entry = raw.get(key)
        if entry and entry.get("price") is not None:
            prices.append(
                {
                    "grade": label,
                    "price": float(entry["price"]),
                    "posted_time": entry.get("last_updated"),
                }
            )
    return prices


async def _fetch_station(station_id: str) -> dict | None:
    try:
        gb = GasBuddy(station_id=int(station_id))
        return await gb.price_lookup()
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
            prices = _parse_prices(raw)
            if prices:
                storage.record_prices(sid, prices)
        else:
            log.debug("Using cached prices for station %s (age %.0fs)", sid, age)

        raw = _price_cache[sid]
        results.append(
            {
                "id": sid,
                "nickname": cfg["nickname"],
                "name": cfg["nickname"],
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


@app.route("/api/history/<station_id>")
def api_history(station_id: str):
    days = min(int(request.args.get("days", 7)), 90)
    data = storage.get_history(station_id, days=days)
    return jsonify(data)


@app.route("/refresh")
def refresh():
    _price_cache.clear()
    _cache_timestamps.clear()
    log.info("Cache cleared — forcing re-fetch")
    return redirect(url_for("index"))


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=PORT, debug=False)
