from __future__ import annotations

import unittest

from iesbhistorico.sampling import SAMPLED_MONTHS_PER_YEAR, one_year_per_decade, sampled_year_months


class SamplingTest(unittest.TestCase):
    def test_one_year_per_decade(self) -> None:
        self.assertEqual(one_year_per_decade(1950, 1999), [1950, 1960, 1970, 1980, 1990])
        self.assertEqual(one_year_per_decade(1955, 1972), [1955, 1960, 1970])

    def test_sampled_year_months(self) -> None:
        pairs = sampled_year_months(1950, 1960)
        self.assertEqual(pairs, [(1950, 1), (1950, 4), (1950, 7), (1950, 10), (1960, 1), (1960, 4), (1960, 7), (1960, 10)])
        self.assertEqual(SAMPLED_MONTHS_PER_YEAR, (1, 4, 7, 10))


if __name__ == "__main__":
    unittest.main()
