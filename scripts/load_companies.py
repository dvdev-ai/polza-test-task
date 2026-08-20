#!/usr/bin/env python3
"""Load page_*.json company dumps into PostgreSQL with deduplication."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

import psycopg2
from psycopg2.extras import execute_values


UPSERT_SQL = """
INSERT INTO companies (
  external_id, name, category, city, address,
  rating, reviews_count, site, phone, source
) VALUES %s
ON CONFLICT (external_id) DO UPDATE SET
  name = EXCLUDED.name,
  category = EXCLUDED.category,
  city = EXCLUDED.city,
  address = EXCLUDED.address,
  rating = EXCLUDED.rating,
  reviews_count = EXCLUDED.reviews_count,
  site = EXCLUDED.site,
  phone = EXCLUDED.phone,
  source = EXCLUDED.source,
  updated_at = NOW()
"""


def normalize_site(value):
    if value is None:
        return None
    text = str(value).strip()
    if not text or text.lower() in {"null", "none", "n/a", "нет сайта"}:
        return None
    return text


def normalize_phone(value):
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def row_from_item(item: dict, source: str = "json"):
    rating = item.get("rating")
    if rating is not None:
        rating = float(rating)
        if rating < 0 or rating > 5:
            rating = None
    reviews = item.get("reviews_count")
    if reviews is None:
        reviews = 0
    reviews = int(reviews)
    if reviews < 0:
        reviews = 0
    return (
        str(item["id"]).strip(),
        str(item["name"]).strip(),
        str(item["category"]).strip(),
        str(item["city"]).strip(),
        (item.get("address") or "").strip() or None,
        rating,
        reviews,
        normalize_site(item.get("site")),
        normalize_phone(item.get("phone")),
        source,
    )


def load_pages(data_dir: Path) -> tuple[list[tuple], int]:
    pages = sorted(data_dir.glob("page_*.json"))
    if not pages:
        raise FileNotFoundError(f"No page_*.json in {data_dir}")

    seen: dict[str, tuple] = {}
    raw_count = 0
    for path in pages:
        payload = json.loads(path.read_text(encoding="utf-8"))
        items = payload["items"] if isinstance(payload, dict) else payload
        for item in items:
            raw_count += 1
            row = row_from_item(item, source="json")
            seen[row[0]] = row
    return list(seen.values()), raw_count


def main() -> int:
    parser = argparse.ArgumentParser(description="Load companies JSON pages into Postgres")
    parser.add_argument(
        "--data-dir",
        default=os.environ.get("DATA_DIR", str(Path(__file__).resolve().parents[1] / "data")),
    )
    parser.add_argument(
        "--database-url",
        default=os.environ.get(
            "DATABASE_URL",
            "postgresql://polza:polza@localhost:5433/companies",
        ),
    )
    args = parser.parse_args()

    data_dir = Path(args.data_dir)
    rows, raw_count = load_pages(data_dir)
    print(f"Read {raw_count} rows from JSON, {len(rows)} unique external_id")

    with psycopg2.connect(args.database_url) as conn:
        with conn.cursor() as cur:
            execute_values(cur, UPSERT_SQL, rows, page_size=200)
            cur.execute("SELECT COUNT(*) FROM companies WHERE source = 'json' OR source = 'csv'")
            total = cur.fetchone()[0]
            cur.execute("SELECT COUNT(*) FROM companies")
            all_count = cur.fetchone()[0]
        conn.commit()

    print(f"Upserted {len(rows)} companies. Table now has {all_count} rows.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
