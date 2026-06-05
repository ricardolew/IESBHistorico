from __future__ import annotations

import unittest

from iesbhistorico.modeling.tfidf_model import train_tfidf_model


class TfidfModelTest(unittest.TestCase):
    def test_tfidf_model_predicts_distribution(self) -> None:
        rows = [
            {"phrase": "telegram office", "target": {"1900s": 1.0}},
            {"phrase": "wireless telegraph", "target": {"1900s": 1.0}},
            {"phrase": "streaming platform", "target": {"2020s": 1.0}},
            {"phrase": "mobile application", "target": {"2020s": 1.0}},
        ]
        model = train_tfidf_model(rows)
        distribution = model.predict("telegram office")
        self.assertAlmostEqual(sum(distribution.values()), 1.0, places=5)
        self.assertIn("1900s", distribution)
        self.assertIn("2020s", distribution)


if __name__ == "__main__":
    unittest.main()

