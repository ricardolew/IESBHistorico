from __future__ import annotations

import argparse
import json
import logging
from collections import defaultdict
from pathlib import Path

import pandas as pd

from iesbhistorico.config import PARQUET_DIR, RAW_DIR, ensure_data_dirs
from iesbhistorico.extraction.phrase_extractor import extract_phrases
from iesbhistorico.logging_utils import configure_logging
from iesbhistorico.normalization.article_cleaner import normalize_text
from iesbhistorico.storage.partitioned_parquet import stable_hash, write_partition
from iesbhistorico.time_utils import decade_for_year, year_from_pub_date

LOGGER = logging.getLogger(__name__)


def ingest_raw_file(
    path: Path,
    parquet_dir: Path = PARQUET_DIR,
    start_year: int | None = None,
    end_year: int | None = None,
    months: set[int] | None = None,
    max_phrases_per_article: int | None = 300,
    context_radius: int = 40,
) -> dict[str, int]:
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)

    docs = payload.get("response", {}).get("docs", [])
    article_rows: list[dict] = []
    phrase_rows: list[dict] = []

    for doc in docs:
        source_id = doc.get("_id") or doc.get("uri") or doc.get("web_url")
        pub_date = doc.get("pub_date")
        year = year_from_pub_date(pub_date)
        if not source_id or year is None:
            continue
        if start_year is not None and year < start_year:
            continue
        if end_year is not None and year > end_year:
            continue

        month = _month_from_pub_date(pub_date) or _month_from_path(path)
        if months is not None and month not in months:
            continue
        decade = decade_for_year(year)
        article_id = stable_hash({"source": "nyt", "source_id": source_id})
        text = article_text(doc)
        content_hash = stable_hash(
            {
                "source_id": source_id,
                "pub_date": pub_date,
                "headline": (doc.get("headline") or {}).get("main"),
                "abstract": doc.get("abstract"),
                "snippet": doc.get("snippet"),
                "lead_paragraph": doc.get("lead_paragraph"),
                "keywords": doc.get("keywords"),
            }
        )

        article_rows.append(
            {
                "article_id": article_id,
                "source_id": source_id,
                "content_hash": content_hash,
                "pub_date": pub_date,
                "year": year,
                "month": month,
                "decade": decade,
                "section": doc.get("section_name") or doc.get("news_desk"),
                "subsection": doc.get("subsection_name"),
                "word_count": doc.get("word_count"),
            }
        )

        for phrase in extract_phrases(text, max_phrases=max_phrases_per_article, context_radius=context_radius):
            phrase_id = stable_hash(
                {
                    "article_id": article_id,
                    "phrase": phrase.phrase,
                    "context": phrase.context,
                }
            )
            phrase_rows.append(
                {
                    "phrase_id": phrase_id,
                    "article_id": article_id,
                    "phrase_hash": stable_hash({"phrase": phrase.phrase}),
                    "phrase": phrase.phrase,
                    "context": phrase.context,
                    "context_hash": stable_hash({"context": phrase.context}),
                    "year": year,
                    "month": month,
                    "decade": decade,
                    "frequency": phrase.frequency,
                }
            )

    counts = {"articles": 0, "phrases": 0}
    if article_rows:
        counts["articles"] = len(article_rows)
        write_partition(pd.DataFrame(article_rows), parquet_dir, "articles", year=article_rows[0]["year"], month=f"{article_rows[0]['month']:02d}")
    if phrase_rows:
        counts["phrases"] = len(phrase_rows)
        write_partition(pd.DataFrame(phrase_rows), parquet_dir, "phrases", year=phrase_rows[0]["year"], month=f"{phrase_rows[0]['month']:02d}")
    return counts


def article_text(doc: dict) -> str:
    headline = doc.get("headline") or {}
    keywords = doc.get("keywords") or []
    keyword_values = " ".join(str(item.get("value", "")) for item in keywords if isinstance(item, dict))
    parts = [
        headline.get("main"),
        headline.get("print_headline"),
        doc.get("abstract"),
        doc.get("snippet"),
        doc.get("lead_paragraph"),
        keyword_values,
    ]
    return normalize_text(" ".join(part for part in parts if part))


def ingest_directory(
    raw_dir: Path = RAW_DIR,
    parquet_dir: Path = PARQUET_DIR,
    start_year: int | None = None,
    end_year: int | None = None,
    years: set[int] | None = None,
    months: set[int] | None = None,
    max_phrases_per_article: int | None = 300,
    context_radius: int = 40,
) -> dict[str, int]:
    ensure_data_dirs()
    totals: dict[str, int] = defaultdict(int)
    paths = [
        path
        for path in sorted(raw_dir.rglob("*.json"))
        if _path_may_be_in_range(path, start_year, end_year, years, months)
    ]
    for index, path in enumerate(paths, start=1):
        counts = ingest_raw_file(
            path,
            parquet_dir,
            start_year,
            end_year,
            months=months,
            max_phrases_per_article=max_phrases_per_article,
            context_radius=context_radius,
        )
        for key, value in counts.items():
            totals[key] += value
        LOGGER.info(
            "Ingested %s articles and %s phrase rows from %s",
            counts["articles"],
            counts["phrases"],
            path,
        )
        LOGGER.info("Ingestion progress: %s/%s files (%.1f%%)", index, len(paths), index / max(len(paths), 1) * 100)
    return dict(totals)


def _path_may_be_in_range(
    path: Path,
    start_year: int | None,
    end_year: int | None,
    years: set[int] | None = None,
    months: set[int] | None = None,
) -> bool:
    try:
        year = int(path.parent.name)
        month = int(path.stem)
    except ValueError:
        return True
    if years is not None and year not in years:
        return False
    if months is not None and month not in months:
        return False
    if start_year is not None and year < start_year:
        return False
    if end_year is not None and year > end_year:
        return False
    return True


def _month_from_path(path: Path) -> int:
    return int(path.stem)


def _month_from_pub_date(pub_date: str | None) -> int | None:
    if not pub_date or len(pub_date) < 7:
        return None
    value = pub_date[5:7]
    return int(value) if value.isdigit() else None


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest NYT raw JSON files into partitioned Parquet.")
    parser.add_argument("--raw-dir", type=Path, default=RAW_DIR)
    parser.add_argument("--parquet-dir", type=Path, default=PARQUET_DIR)
    parser.add_argument("--start-year", type=int)
    parser.add_argument("--end-year", type=int)
    parser.add_argument("--months", type=int, nargs="*")
    parser.add_argument("--max-phrases-per-article", type=int, default=300)
    parser.add_argument("--context-radius", type=int, default=40)
    parser.add_argument("--log-level", default="INFO")
    args = parser.parse_args()

    configure_logging(args.log_level)
    totals = ingest_directory(
        args.raw_dir,
        args.parquet_dir,
        args.start_year,
        args.end_year,
        months=set(args.months) if args.months else None,
        max_phrases_per_article=args.max_phrases_per_article,
        context_radius=args.context_radius,
    )
    LOGGER.info("Ingestion complete: %s", totals)


if __name__ == "__main__":
    main()
