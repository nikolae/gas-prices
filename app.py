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

storage.init_db(STATIONS)

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

    for cfg in storage.get_stations():
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
    # Just pass station metadata — prices are fetched async by the browser
    stations = [{"id": s["id"], "nickname": s["nickname"]} for s in storage.get_stations()]
    return render_template("index.html", stations=stations)


@app.route("/api/prices")
def api_prices():
    results = fetch_all_stations()
    return jsonify({
        s["id"]: {
            "prices": s["prices"],
            "error": s["error"],
            "cached_at": s["cached_at"],
        }
        for s in results
    })


@app.route("/api/stations", methods=["POST"])
def api_add_station():
    data = request.get_json()
    station_id = str(data.get("id", "")).strip()
    nickname = str(data.get("nickname", "")).strip() or f"Station {station_id}"

    if not station_id.isdigit():
        return jsonify({"error": "Invalid station ID"}), 400

    # Validate by fetching prices
    raw = asyncio.run(_fetch_station(station_id))
    if raw is None:
        return jsonify({"error": "Could not fetch prices — check the station ID"}), 400

    storage.add_station(station_id, nickname)
    _price_cache[station_id] = raw
    _cache_timestamps[station_id] = time.time()
    prices = _parse_prices(raw)
    if prices:
        storage.record_prices(station_id, prices)

    log.info("Added station %s (%s)", station_id, nickname)
    return jsonify({"ok": True})


@app.route("/api/stations/<station_id>", methods=["PUT"])
def api_rename_station(station_id: str):
    data = request.get_json()
    nickname = str(data.get("nickname", "")).strip()
    if not nickname:
        return jsonify({"error": "Nickname is required"}), 400
    storage.rename_station(station_id, nickname)
    log.info("Renamed station %s to '%s'", station_id, nickname)
    return jsonify({"ok": True})


@app.route("/api/stations/<station_id>", methods=["DELETE"])
def api_remove_station(station_id: str):
    storage.remove_station(station_id)
    _price_cache.pop(station_id, None)
    _cache_timestamps.pop(station_id, None)
    log.info("Removed station %s", station_id)
    return jsonify({"ok": True})


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
