"""오프라인 고정 평가 자료 검증."""
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from sidam.data import load_corpus, load_documents, read_jsonl
from sidam.evaluation import validate_benchmark

if __name__ == '__main__':
    poems = load_corpus(ROOT / 'data')
    docs, _ = load_documents(ROOT / 'data', poems)
    paths = [ROOT / f'evaluation/{name}_v1.jsonl' for name in ('search', 'answers')]
    result = validate_benchmark(*(read_jsonl(p) for p in paths), poems, docs)
    result['sha256'] = {p.name: hashlib.sha256(p.read_text(encoding='utf-8-sig').replace('\r\n', '\n').encode()).hexdigest() for p in paths}
    print(json.dumps(result, ensure_ascii=False))
