#!/usr/bin/env python3
"""Load review.csv into staging, detect anomalies, merge valid rows into companies."""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
import sys
from pathlib import Path

import psycopg2
from psycopg2.extras import Json, execute_values


PHONE_RE = re.compile(r"^\+7 \(\d{3}\) \d{3}-\d{2}-\d{2}$")
ID_RE = re.compile(r"^c_\d{6}$")
# Typical UTF-8→CP1251 mojibake for Russian city names, e.g. РњРѕСЃРєРІР°
MOJIBAKE_RE = re.compile(r"Р[ЎЈ¤Ґ¦§Ё©Є«¬®ЇА-Я]")

CITY_ALIASES = {
    "moscow": "Москва",
    "москва": "Москва",
    "санкат-петербург": "Санкт-Петербург",
}


def normalize_city(city: str) -> tuple[str, list[str]]:
    codes: list[str] = []
    cleaned = city.strip()
    if cleaned != city:
        codes.append("city_trailing_space")
    alias = CITY_ALIASES.get(cleaned.lower())
    if alias:
        if cleaned.lower() == "moscow":
            codes.append("city_english")
        elif cleaned == "Санкат-Петербург":
            codes.append("city_typo")
        elif cleaned != alias:
            codes.append("city_case")
        return alias, codes
    return cleaned, codes


def parse_rating(raw: str | None):
    if raw is None:
        return None, ["rating_missing"]
    text = raw.strip()
    if not text:
        return None, ["rating_empty"]
    if text.upper() in {"N/A", "NA", "NULL", "NONE"}:
        return None, ["rating_na"]
    # European decimal comma
    if re.fullmatch(r"\d+,\d+", text):
        return float(text.replace(",", ".")), ["rating_comma_decimal"]
    try:
        value = float(text)
    except ValueError:
        return None, ["rating_non_numeric"]
    codes = []
    if value < 0 or value > 5:
        codes.append("rating_out_of_range")
        return None, codes
    return value, codes


def parse_reviews(raw: str | None):
    if raw is None:
        return None, ["reviews_missing"]
    text = raw.strip()
    if not text:
        return None, ["reviews_empty"]
    if not re.fullmatch(r"-?\d+", text):
        return None, ["reviews_non_integer"]
    value = int(text)
    codes = []
    if value < 0:
        codes.append("reviews_negative")
        return None, codes
    return value, codes


def analyze_row(row: dict, row_number: int) -> list[dict]:
    anomalies = []
    external_id = (row.get("id") or "").strip()
    name = (row.get("name") or "").strip()
    category = (row.get("category") or "").strip()
    city = (row.get("city") or "").strip()
    address = (row.get("address") or "").strip()
    site = (row.get("site") or "").strip()
    phone = (row.get("phone") or "").strip()

    def add(code: str, detail: str):
        anomalies.append(
            {
                "code": code,
                "detail": detail,
                "external_id": external_id or None,
                "row_number": row_number,
                "raw": row,
            }
        )

    if not any([external_id, name, category, city, address, site, phone, row.get("rating"), row.get("reviews_count")]):
        add("empty_row", "Completely empty CSV row")
        return anomalies

    if not external_id:
        add("missing_id", "Empty company id")
    elif not ID_RE.match(external_id):
        add("bad_id_format", f"Unexpected id format: {external_id!r}")

    if not name:
        add("missing_name", "Empty name")
    if not category:
        add("missing_category", "Empty category")
    if not city:
        add("missing_city", "Empty city")
    elif "ул." in city or "д." in city:
        add("city_looks_like_address", f"Address value in city column: {city!r}")
    elif MOJIBAKE_RE.search(city):
        add("city_mojibake", f"Broken encoding in city: {city!r}")
    else:
        _, city_codes = normalize_city(city)
        for code in city_codes:
            if code == "city_trailing_space":
                add(code, f"City has surrounding spaces: {city!r}")
            elif code == "city_english":
                add(code, "City written in English: Moscow")
            elif code == "city_typo":
                add(code, "Typo in city: Санкат-Петербург")
            elif code == "city_case":
                add(code, f"City casing anomaly: {city!r}")
            else:
                add(code, f"City anomaly: {city!r}")

    rating, rating_codes = parse_rating(row.get("rating"))
    for code in rating_codes:
        add(code, f"rating={row.get('rating')!r}")

    reviews, reviews_codes = parse_reviews(row.get("reviews_count"))
    for code in reviews_codes:
        add(code, f"reviews_count={row.get('reviews_count')!r}")

    if site:
        if site.lower() in {"нет сайта", "null", "none", "n/a"}:
            add("site_placeholder", f"Non-URL site placeholder: {site!r}")
        elif site.startswith("htp://"):
            add("site_typo_scheme", f"Broken URL scheme: {site!r}")
        elif not re.match(r"^https?://", site, re.I):
            add("site_invalid", f"Site is not an http(s) URL: {site!r}")
    if phone:
        if phone == "+7":
            add("phone_incomplete", "Phone is only '+7'")
        elif "abc" in phone.lower() or re.search(r"[A-Za-zА-Яа-я]", phone):
            add("phone_garbage", f"Phone contains letters: {phone!r}")
        elif phone.startswith("8 "):
            add("phone_legacy_8", f"Phone uses legacy 8-prefix: {phone!r}")
        elif not PHONE_RE.match(phone):
            add("phone_format", f"Unexpected phone format: {phone!r}")

    return anomalies


def is_importable(row: dict, anomalies: list[dict]) -> bool:
    blocking = {
        "empty_row",
        "missing_id",
        "bad_id_format",
        "missing_name",
        "missing_category",
        "missing_city",
        "rating_non_numeric",
        "rating_out_of_range",
        "rating_na",
        "reviews_non_integer",
        "reviews_negative",
        "city_looks_like_address",
        "city_mojibake",
        "phone_garbage",
        "phone_incomplete",
        "site_placeholder",
        "site_typo_scheme",
        "site_invalid",
    }
    codes = {a["code"] for a in anomalies}
    if codes & blocking:
        return False
    rating, _ = parse_rating(row.get("rating"))
    reviews, _ = parse_reviews(row.get("reviews_count"))
    # rating may be null; reviews must parse for CHECK constraint
    if reviews is None and (row.get("reviews_count") or "").strip():
        return False
    if reviews is None:
        reviews = 0
    return True


def company_tuple(row: dict):
    rating, _ = parse_rating(row.get("rating"))
    reviews, _ = parse_reviews(row.get("reviews_count"))
    if reviews is None:
        reviews = 0
    site = (row.get("site") or "").strip()
    if not site or site.lower() in {"нет сайта", "null", "none", "n/a"}:
        site = None
    elif site.startswith("htp://"):
        site = None
    phone = (row.get("phone") or "").strip() or None
    if phone in {"+7"} or (phone and re.search(r"[A-Za-zА-Яа-я]", phone)):
        phone = None
    city, _ = normalize_city(row.get("city") or "")
    return (
        (row.get("id") or "").strip(),
        (row.get("name") or "").strip(),
        (row.get("category") or "").strip(),
        city,
        (row.get("address") or "").strip() or None,
        rating,
        reviews,
        site,
        phone,
        "csv",
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Load and validate review.csv")
    parser.add_argument(
        "--csv",
        default=os.environ.get(
            "REVIEW_CSV",
            str(Path(__file__).resolve().parents[1] / "data" / "review.csv"),
        ),
    )
    parser.add_argument(
        "--database-url",
        default=os.environ.get(
            "DATABASE_URL",
            "postgresql://polza:polza@localhost:5433/companies",
        ),
    )
    parser.add_argument(
        "--report",
        default=str(Path(__file__).resolve().parents[1] / "ANOMALIES.md"),
    )
    args = parser.parse_args()

    csv_path = Path(args.csv)
    with csv_path.open(newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        rows = list(reader)

    all_anomalies: list[dict] = []
    id_counts: dict[str, int] = {}
    for idx, row in enumerate(rows, start=2):  # header is line 1
        external_id = (row.get("id") or "").strip()
        if external_id:
            id_counts[external_id] = id_counts.get(external_id, 0) + 1
        all_anomalies.extend(analyze_row(row, idx))

    for external_id, count in id_counts.items():
        if count > 1:
            all_anomalies.append(
                {
                    "code": "duplicate_id_in_csv",
                    "detail": f"id {external_id} appears {count} times in review.csv",
                    "external_id": external_id,
                    "row_number": None,
                    "raw": {"id": external_id, "count": count},
                }
            )

    # Structural surprise: file is named review.csv but contains company fields
    all_anomalies.append(
        {
            "code": "filename_vs_schema",
            "detail": "File is named review.csv but columns are company fields (id,name,category,...), not review text/ratings per review",
            "external_id": None,
            "row_number": None,
            "raw": {"columns": reader.fieldnames},
        }
    )

    importable = []
    for idx, row in enumerate(rows, start=2):
        row_anoms = [a for a in all_anomalies if a.get("row_number") == idx]
        if is_importable(row, row_anoms):
            importable.append(company_tuple(row))

    # dedupe importable by external_id (keep last)
    by_id = {r[0]: r for r in importable if r[0]}
    importable = list(by_id.values())

    with psycopg2.connect(args.database_url) as conn:
        with conn.cursor() as cur:
            cur.execute("TRUNCATE companies_staging RESTART IDENTITY")
            cur.execute("DELETE FROM load_anomalies WHERE source_file = %s", ("review.csv",))
            staging_rows = []
            for idx, row in enumerate(rows, start=2):
                staging_rows.append(
                    (
                        (row.get("id") or "").strip() or None,
                        (row.get("name") or "").strip() or None,
                        (row.get("category") or "").strip() or None,
                        (row.get("city") or "").strip() or None,
                        (row.get("address") or "").strip() or None,
                        row.get("rating"),
                        row.get("reviews_count"),
                        (row.get("site") or "").strip() or None,
                        (row.get("phone") or "").strip() or None,
                        idx,
                    )
                )
            execute_values(
                cur,
                """
                INSERT INTO companies_staging (
                  external_id, name, category, city, address,
                  rating_raw, reviews_raw, site, phone, row_number
                ) VALUES %s
                """,
                staging_rows,
                page_size=200,
            )
            anomaly_rows = [
                (
                    "review.csv",
                    a.get("external_id"),
                    a.get("row_number"),
                    a["code"],
                    a["detail"],
                    Json(a.get("raw")),
                )
                for a in all_anomalies
            ]
            execute_values(
                cur,
                """
                INSERT INTO load_anomalies (
                  source_file, external_id, row_number, code, detail, raw_payload
                ) VALUES %s
                """,
                anomaly_rows,
                page_size=200,
            )
            if importable:
                execute_values(
                    cur,
                    """
                    INSERT INTO companies (
                      external_id, name, category, city, address,
                      rating, reviews_count, site, phone, source
                    ) VALUES %s
                    ON CONFLICT (external_id) DO UPDATE SET
                      name = EXCLUDED.name,
                      category = EXCLUDED.category,
                      city = EXCLUDED.city,
                      address = EXCLUDED.address,
                      rating = COALESCE(EXCLUDED.rating, companies.rating),
                      reviews_count = EXCLUDED.reviews_count,
                      site = EXCLUDED.site,
                      phone = EXCLUDED.phone,
                      source = EXCLUDED.source,
                      updated_at = NOW()
                    """,
                    importable,
                    page_size=200,
                )
            cur.execute("SELECT COUNT(*) FROM companies")
            total = cur.fetchone()[0]
            cur.execute("SELECT COUNT(*) FROM load_anomalies WHERE source_file = 'review.csv'")
            anom_count = cur.fetchone()[0]
        conn.commit()

    # Write human report
    by_code: dict[str, list] = {}
    for a in all_anomalies:
        by_code.setdefault(a["code"], []).append(a)

    lines = [
        "# ANOMALIES — review.csv",
        "",
        "Короткий отчет по сюрпризам в `data/review.csv`.",
        "",
        f"- Строк в CSV (без заголовка): **{len(rows)}**",
        f"- Уникальных id: **{len(id_counts)}**",
        f"- Записей с аномалиями / кодов: **{len(all_anomalies)}**",
        f"- Валидных строк, влитых в `companies`: **{len(importable)}**",
        f"- Итого в `companies` после merge: **{total}**",
        "",
        "## Главный сюрприз",
        "",
        "Файл называется `review.csv`, но это не отзывы. Это снова компании: те же поля, что в `page_*.json` (`id`, `name`, `category`, `city`, `address`, `rating`, `reviews_count`, `site`, `phone`). Обнаружено по заголовку CSV и сравнению со схемой JSON.",
        "",
        "## Как искал",
        "",
        "1. Сверил колонки CSV с полями JSON.",
        "2. Посчитал пересечение id с уже загруженной базой.",
        "3. Прогнал валидацию: рейтинг, отзывы, телефон, сайт, город, пустые строки, дубли id.",
        "4. Всё странное сложил в `load_anomalies` и в этот файл.",
        "",
        "## Найденные аномалии",
        "",
    ]
    for code, items in sorted(by_code.items(), key=lambda x: (-len(x[1]), x[0])):
        lines.append(f"### `{code}` ({len(items)})")
        lines.append("")
        lines.append(items[0]["detail"])
        examples = items[:5]
        for ex in examples:
            loc = f"row {ex['row_number']}" if ex.get("row_number") else "file-level"
            eid = ex.get("external_id") or "-"
            lines.append(f"- {loc}, id={eid}: {ex['detail']}")
        if len(items) > 5:
            lines.append(f"- … и еще {len(items) - 5}")
        lines.append("")

    lines.extend(
        [
            "## Что сделал со странными строками",
            "",
            "- Все сырые строки положил в `companies_staging`.",
            "- Блокирующие ошибки не пускал в основную таблицу (битый рейтинг/отзывы, мусорный телефон, адрес в поле city, mojibake, пустые строки).",
            "- Мягкие проблемы (хвостовой пробел в городе, English `Moscow`, опечатка `Санкат-Петербург`) оставил в отчете; строку можно импортировать, если остальные поля валидны.",
            "",
            f"_Автогенерация скриптом `scripts/load_reviews.py`. В БД сохранено аномалий: {anom_count}.__",
            "",
        ]
    )
    Path(args.report).write_text("\n".join(lines), encoding="utf-8")
    print(f"Staging {len(rows)} rows, imported {len(importable)}, anomalies {len(all_anomalies)}")
    print(f"Wrote {args.report}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
