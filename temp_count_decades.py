from pathlib import Path
import json
from collections import Counter

path = Path('data/datasets/training_dataset.jsonl')
counts = Counter()
rows = 0
with path.open('r', encoding='utf-8') as f:
    for line in f:
        line = line.strip()
        if not line:
            continue
        row = json.loads(line)
        target = row.get('target', {})
        if target:
            decade = max(target, key=lambda k: float(target[k]))
            counts[decade] += 1
        rows += 1
print('rows=', rows)
for decade, cnt in sorted(counts.items(), key=lambda item: item[0]):
    print(f'{decade}\t{cnt}')
most = counts.most_common(1)[0]
least_count = min(counts.values())
least = [(d, c) for d, c in counts.items() if c == least_count]
print('most common', most)
print('least common', least)
print('ratio most/least', most[1] / least[0][1])
print('unique decades', len(counts))
