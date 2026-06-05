from __future__ import annotations

import argparse
import json
import logging
import time
from pathlib import Path
from typing import Callable
from urllib.error import HTTPError
from urllib.request import urlopen

from iesbhistorico.config import RAW_DIR, ensure_data_dirs
from iesbhistorico.logging_utils import configure_logging

LOGGER = logging.getLogger(__name__)


def download_month(
    year: int,
    month: int,
    api_key: str,
    output_dir: Path = RAW_DIR,
    max_429_retries: int = 10,
    initial_backoff_seconds: float = 20.0,
    opener: Callable | None = None,
    sleeper: Callable[[float], None] = time.sleep,
) -> Path:
    ensure_data_dirs()
    target = output_dir / str(year) / f"{month:02d}.json"
    if target.exists():
        LOGGER.info("Skipping existing archive file: %s", target)
        return target
    target.parent.mkdir(parents=True, exist_ok=True)
    url = f"https://api.nytimes.com/svc/archive/v1/{year}/{month}.json?api-key={api_key}"
    LOGGER.info("Downloading %s/%02d", year, month)
    payload = _request_json_with_backoff(
        url,
        max_429_retries=max_429_retries,
        initial_backoff_seconds=initial_backoff_seconds,
        opener=opener or urlopen,
        sleeper=sleeper,
    )
    tmp_target = target.with_suffix(target.suffix + ".tmp")
    tmp_target.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    tmp_target.replace(target)
    return target


def _request_json_with_backoff(
    url: str,
    max_429_retries: int = 10,
    initial_backoff_seconds: float = 20.0,
    opener: Callable = urlopen,
    sleeper: Callable[[float], None] = time.sleep,
) -> dict:
    attempt = 0
    while True:
        try:
            with opener(url, timeout=60) as response:
                return json.loads(response.read().decode("utf-8"))
        except HTTPError as error:
            if error.code != 429:
                raise
            if attempt >= max_429_retries:
                LOGGER.error("NYT request still rate-limited after %s retries: %s", max_429_retries, url)
                raise
            wait_seconds = initial_backoff_seconds * (2**attempt)
            attempt += 1
            LOGGER.warning(
                "NYT API returned 429 rate limit. Retry %s/%s in %.1fs",
                attempt,
                max_429_retries,
                wait_seconds,
            )
            sleeper(wait_seconds)


def main() -> None:
    parser = argparse.ArgumentParser(description="Download NYT Archive API JSON files.")
    parser.add_argument("--api-key", required=True)
    parser.add_argument("--start-year", type=int, required=True)
    parser.add_argument("--end-year", type=int, required=True)
    parser.add_argument("--months", type=int, nargs="*", default=list(range(1, 13)))
    parser.add_argument("--max-429-retries", type=int, default=10)
    parser.add_argument("--initial-backoff-seconds", type=float, default=20.0)
    args = parser.parse_args()

    configure_logging()
    for year in range(args.start_year, args.end_year + 1):
        for month in args.months:
            download_month(
                year,
                month,
                args.api_key,
                max_429_retries=args.max_429_retries,
                initial_backoff_seconds=args.initial_backoff_seconds,
            )


if __name__ == "__main__":
    main()
