from __future__ import annotations


SAMPLED_MONTHS_PER_YEAR = (1, 4, 7, 10)


def one_year_per_decade(start_year: int, end_year: int) -> list[int]:
    """Pick one deterministic representative year for each decade in range."""

    years: list[int] = []
    first_decade = (start_year // 10) * 10
    last_decade = (end_year // 10) * 10
    for decade in range(first_decade, last_decade + 1, 10):
        representative = decade
        if representative < start_year:
            representative = start_year
        if representative > end_year:
            representative = end_year
        if representative not in years:
            years.append(representative)
    return years


def sampled_year_months(start_year: int, end_year: int) -> list[tuple[int, int]]:
    return [
        (year, month)
        for year in one_year_per_decade(start_year, end_year)
        for month in SAMPLED_MONTHS_PER_YEAR
    ]
