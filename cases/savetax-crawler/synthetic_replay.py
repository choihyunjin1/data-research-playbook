"""MIT. Synthetic, offline counterexample; not a crawler or price validator.

All IDs, URLs, text and amounts below are invented. Amounts are fictional minor
units, not a real currency. This deliberately small model allows one seller
association per inventory item. Observation ticks encode synthetic event time;
import order does not decide which observation is latest.
"""

from dataclasses import dataclass
import json
import sqlite3
from urllib.parse import urlsplit


@dataclass(frozen=True)
class Item:
    item_id: str
    fixed_order: int
    registration_price_minor: int


def positive_integer(value):
    if type(value) is not int or value <= 0:
        raise ValueError("expected a positive integer")


def validate_snapshot(rows, expected_ids):
    """Reject duplicate, missing, extra, or reordered inventory rows."""
    actual = [row["item_id"] for row in rows]
    expected = list(expected_ids)
    if len(set(actual)) != len(actual) or len(set(expected)) != len(expected):
        raise ValueError("duplicate inventory ID")
    if set(actual) != set(expected):
        raise ValueError("missing or extra inventory ID")
    if actual != expected:
        raise ValueError("fixed inventory order changed")


class Replay:
    """In-memory case-local state; source quarantine never deletes observations."""

    def __init__(self, items):
        items = list(items)
        if not items or any(not item.item_id for item in items):
            raise ValueError("nonempty inventory and IDs required")
        for item in items:
            positive_integer(item.fixed_order)
            positive_integer(item.registration_price_minor)
        if len({item.item_id for item in items}) != len(items):
            raise ValueError("duplicate inventory ID")
        if sorted(item.fixed_order for item in items) != list(range(1, len(items) + 1)):
            raise ValueError("fixed order must contain every position exactly once")
        items.sort(key=lambda item: item.fixed_order)
        self.expected_ids = tuple(item.item_id for item in items)
        self.db = sqlite3.connect(":memory:")
        self.db.row_factory = sqlite3.Row
        self.db.execute("PRAGMA foreign_keys=ON")
        self.db.executescript("""
            CREATE TABLE inventory (
                item_id TEXT PRIMARY KEY, fixed_order INTEGER UNIQUE NOT NULL,
                registration_price_minor INTEGER NOT NULL
            );
            CREATE TABLE documents (
                document_id TEXT PRIMARY KEY, url TEXT UNIQUE NOT NULL
            );
            CREATE TABLE sources (
                source_id TEXT PRIMARY KEY,
                item_id TEXT UNIQUE NOT NULL REFERENCES inventory(item_id),
                document_id TEXT NOT NULL REFERENCES documents(document_id),
                comparison_ready INTEGER NOT NULL, quarantined INTEGER NOT NULL DEFAULT 0
            );
            CREATE TABLE observations (
                observation_id INTEGER PRIMARY KEY,
                document_id TEXT NOT NULL REFERENCES documents(document_id),
                tick INTEGER NOT NULL, price_minor INTEGER, raw_text TEXT NOT NULL,
                UNIQUE(document_id, tick)
            );
            CREATE TABLE history (
                event_id INTEGER PRIMARY KEY,
                source_id TEXT NOT NULL REFERENCES sources(source_id),
                event TEXT NOT NULL, reason TEXT NOT NULL
            );
        """)
        with self.db:
            self.db.executemany("INSERT INTO inventory VALUES (?, ?, ?)",
                                [(i.item_id, i.fixed_order, i.registration_price_minor) for i in items])

    def close(self):
        self.db.close()

    def add_document(self, document_id, url):
        parts = urlsplit(url)
        if parts.scheme != "https" or parts.netloc != "example.invalid":
            raise ValueError("this synthetic case only accepts https://example.invalid URLs")
        with self.db:
            self.db.execute("INSERT INTO documents VALUES (?, ?)", (document_id, url))

    def add_source(self, source_id, item_id, document_id, comparison_ready=False):
        """comparison_ready is a fixture decision, not an automated validation."""
        if type(comparison_ready) is not bool:
            raise ValueError("comparison_ready must be boolean")
        with self.db:
            self.db.execute("INSERT INTO sources VALUES (?, ?, ?, ?, 0)",
                            (source_id, item_id, document_id, int(comparison_ready)))
            self.db.execute("INSERT INTO history(source_id, event, reason) VALUES (?, ?, ?)",
                            (source_id, "association_added", "synthetic fixture decision"))

    def observe(self, document_id, tick, price_minor, raw_text):
        """Append a page observation, including an explicit unknown latest price."""
        positive_integer(tick)
        if price_minor is not None:
            positive_integer(price_minor)
        if not isinstance(raw_text, str) or not raw_text.strip():
            raise ValueError("raw synthetic observation text required")
        with self.db:
            self.db.execute("""INSERT INTO observations(document_id, tick, price_minor, raw_text)
                               VALUES (?, ?, ?, ?)""", (document_id, tick, price_minor, raw_text))

    def quarantine(self, source_id, reason):
        """Exclude only this item-to-document association; preserve shared evidence."""
        if not reason.strip():
            raise ValueError("quarantine reason required")
        with self.db:
            source = self.db.execute("SELECT quarantined FROM sources WHERE source_id=?",
                                     (source_id,)).fetchone()
            if source is None:
                raise KeyError(source_id)
            if not source["quarantined"]:
                self.db.execute("UPDATE sources SET quarantined=1 WHERE source_id=?", (source_id,))
                self.db.execute("INSERT INTO history(source_id, event, reason) VALUES (?, ?, ?)",
                                (source_id, "quarantined", reason))

    def batches(self, size=500):
        """Partition the original fixed order; batching does not reorder priorities."""
        positive_integer(size)
        return [list(self.expected_ids[start:start + size])
                for start in range(0, len(self.expected_ids), size)]

    def snapshot(self):
        records = self.db.execute("""
            SELECT i.*, s.source_id, s.comparison_ready, s.quarantined, d.url,
                   o.tick AS latest_observation_tick, o.price_minor AS seller_observed_price_minor
            FROM inventory i
            LEFT JOIN sources s ON s.item_id=i.item_id
            LEFT JOIN documents d ON d.document_id=s.document_id
            LEFT JOIN observations o ON o.document_id=d.document_id
                AND o.tick=(SELECT MAX(tick) FROM observations WHERE document_id=d.document_id)
            ORDER BY i.fixed_order
        """).fetchall()
        rows = []
        for record in records:
            row = dict(record)
            row["comparable_market_price_minor"] = None
            if row["source_id"] is None:
                row["state"] = "no_source"
            elif row["quarantined"]:
                row["state"] = "association_quarantined"
            elif row["seller_observed_price_minor"] is None:
                row["state"] = "latest_price_unknown"
            elif not row["comparison_ready"]:
                row["state"] = "conditions_unconfirmed"
            else:
                row["state"] = "comparable_in_synthetic_fixture"
                row["comparable_market_price_minor"] = row["seller_observed_price_minor"]
            rows.append(row)
        validate_snapshot(rows, self.expected_ids)
        pages_with_latest_price = self.db.execute("""
            SELECT COUNT(*) FROM observations o WHERE o.price_minor IS NOT NULL
                AND o.tick=(SELECT MAX(tick) FROM observations WHERE document_id=o.document_id)
        """).fetchone()[0]
        return {
            "synthetic": True,
            "snapshot_complete": True,
            "inventory_rows": len(self.expected_ids),
            "snapshot_rows": len(rows),
            "seller_pages_with_latest_price": pages_with_latest_price,
            "comparable_market_price_rows": sum(r["comparable_market_price_minor"] is not None for r in rows),
            "rows": rows,
        }


def shared_url_fixture():
    replay = Replay([Item("fiction-a", 1, 2400), Item("fiction-b", 2, 4100),
                     Item("fiction-unsearched", 3, 6500)])
    replay.add_document("fiction-page", "https://example.invalid/fictional-widget")
    replay.add_source("source-correct", "fiction-a", "fiction-page", True)
    replay.add_source("source-mislinked", "fiction-b", "fiction-page", True)
    replay.observe("fiction-page", 10, 1200, "Invented widget offer: 1200 fictional minor units.")
    return replay


def run_demo():
    replay = shared_url_fixture()
    try:
        before = replay.snapshot()
        replay.quarantine("source-mislinked", "invented mismatch discovered")
        corrected = replay.snapshot()
        replay.observe("fiction-page", 20, None, "Invented latest page: price unavailable.")
        unknown = replay.snapshot()
        return {
            "synthetic": True,
            "scope": "case-local offline counterexample; no real prices, network, or production validation",
            "amount_unit": "fictional minor units",
            "initial_incorrect_fixture": before,
            "after_association_quarantine": corrected,
            "after_latest_price_unknown": unknown,
            "preserved_observations": replay.db.execute("SELECT COUNT(*) FROM observations").fetchone()[0],
            "preserved_history_events": replay.db.execute("SELECT COUNT(*) FROM history").fetchone()[0],
        }
    finally:
        replay.close()


if __name__ == "__main__":
    print(json.dumps(run_demo(), ensure_ascii=False, indent=2))
