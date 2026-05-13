import sqlite3
import os
from datetime import datetime, timedelta, timezone

DB_PATH = os.environ.get("DB_PATH", "gas_prices.db")

_GRADE_ORDER = ["Regular", "Midgrade", "Premium", "Diesel", "E85"]


def init_db():
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


def _connect() -> sqlite3.Connection:
    return sqlite3.connect(DB_PATH)


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

    # Return grades in a consistent display order
    return {g: result[g] for g in _GRADE_ORDER if g in result}
