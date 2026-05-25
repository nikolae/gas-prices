import sqlite3
import os
from datetime import datetime, timedelta, timezone

DB_PATH = os.environ.get("DB_PATH", "gas_prices.db")

_GRADE_ORDER = ["Regular", "Midgrade", "Premium", "Diesel", "E85"]


def init_db(default_stations: list[dict]):
    with _connect() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS price_history (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                station_id  TEXT    NOT NULL,
                grade       TEXT    NOT NULL,
                price       REAL    NOT NULL,
                recorded_at TEXT    NOT NULL
            )
        """)
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_station_time "
            "ON price_history(station_id, recorded_at)"
        )
        conn.execute("""
            CREATE TABLE IF NOT EXISTS stations (
                id       TEXT PRIMARY KEY,
                nickname TEXT NOT NULL
            )
        """)
        # Seed from config only if the table is empty
        count = conn.execute("SELECT COUNT(*) FROM stations").fetchone()[0]
        if count == 0:
            conn.executemany(
                "INSERT OR IGNORE INTO stations (id, nickname) VALUES (?, ?)",
                [(s["id"], s["nickname"]) for s in default_stations],
            )


def _connect() -> sqlite3.Connection:
    return sqlite3.connect(DB_PATH)


# --- Stations ---

def get_stations() -> list[dict]:
    with _connect() as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute("SELECT id, nickname FROM stations").fetchall()
        return [dict(r) for r in rows]


def add_station(station_id: str, nickname: str):
    with _connect() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO stations (id, nickname) VALUES (?, ?)",
            (station_id, nickname),
        )


def rename_station(station_id: str, nickname: str):
    with _connect() as conn:
        conn.execute(
            "UPDATE stations SET nickname = ? WHERE id = ?",
            (nickname, station_id),
        )


def remove_station(station_id: str):
    with _connect() as conn:
        conn.execute("DELETE FROM stations WHERE id = ?", (station_id,))


# --- Price history ---

def record_prices(station_id: str, prices: list[dict]):
    if not prices:
        return
    now = datetime.now(timezone.utc).isoformat()
    with _connect() as conn:
        conn.executemany(
            "INSERT INTO price_history (station_id, grade, price, recorded_at) "
            "VALUES (?, ?, ?, ?)",
            [(station_id, p["grade"], p["price"], now) for p in prices],
        )


def get_history(station_id: str, days: int = 7) -> dict[str, list[dict]]:
    since = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    with _connect() as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            """
            SELECT grade, price, recorded_at
            FROM   price_history
            WHERE  station_id = ? AND recorded_at >= ?
            ORDER  BY recorded_at ASC
            """,
            (station_id, since),
        ).fetchall()

    result: dict[str, list[dict]] = {}
    for row in rows:
        result.setdefault(row["grade"], []).append(
            {"price": row["price"], "time": row["recorded_at"]}
        )

    return {g: result[g] for g in _GRADE_ORDER if g in result}
