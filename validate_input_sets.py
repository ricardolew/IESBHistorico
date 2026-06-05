from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from iesbhistorico.inference.input_validation import validate_input_file


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate sample and evaluation JSONL input sets.")
    parser.add_argument("--sample", type=Path, default=Path("sample_inputs/phrases.jsonl"))
    parser.add_argument("--evaluation", type=Path, default=Path("evaluation_inputs/decade_labeled_phrases.jsonl"))
    parser.add_argument("--min-evaluation-per-decade", type=int, default=2)
    args = parser.parse_args()

    reports = [
        validate_input_file(args.sample),
        validate_input_file(args.evaluation, require_expected_decade=True, min_per_decade=args.min_evaluation_per_decade),
    ]
    print(json.dumps(reports, ensure_ascii=False, indent=2))
    if any(not report["valid"] for report in reports):
        sys.exit(1)


if __name__ == "__main__":
    main()

