from __future__ import annotations

from datetime import datetime


def year_from_pub_date(pub_date: str | None) -> int | None:
    if not pub_date:
        return None
    value = pub_date.strip()
    for fmt in ("%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%S%f%z", "%Y-%m-%d"):
        try:
            return datetime.strptime(value, fmt).year
        except ValueError:
            continue
    if len(value) >= 4 and value[:4].isdigit():
        return int(value[:4])
    return None


def decade_for_year(year: int) -> str:
    return f"{(year // 10) * 10}s"


def decade_sort_key(decade: str) -> int:
    digits = "".join(char for char in decade if char.isdigit())
    return int(digits) if digits else 0
