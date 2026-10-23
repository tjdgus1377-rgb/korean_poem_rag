"""실제 연결의 단계별 시간 측정. 원문 질문·대화·키는 결과에 저장하지 않는다."""
import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from sidam.config import Config
from sidam.service import Service

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=ROOT)
    parser.add_argument('--poem-id', required=True)
    parser.add_argument('--question', required=True)
    parser.add_argument('--repeat', type=int, default=3)
    parser.add_argument('--search-query')
    args = parser.parse_args()
    if not 1 <= args.repeat <= 20:
        parser.error('repeat은 1~20이어야 합니다.')
    config = Config.load(args.root)
    service = Service(config)
    rows = []
    for i in range(args.repeat):
        row = {'phase': 'first' if i == 0 else 'followup', 'poem_id': args.poem_id, 'model': config.chat_model, 'embedding_model': config.embedding_model}
        if args.search_query:
            start = time.monotonic()
            hits, _ = service.search(args.search_query)
            row.update(search_total_seconds=time.monotonic()-start, found_poem_ids=[p['poem_id'] for p in hits])
        answer = service.ask(args.poem_id, args.question)
        row.update(timings=answer['timings'], citation_error=answer['citation_error'], source_isolation=all(s['poem_id'] == args.poem_id for s in answer['sources']))
        rows.append(row)
    path = args.root / 'evaluation/runs' / f'profile-{time.time_ns()}.json'
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'measurements': rows, 'output': str(path)}, ensure_ascii=False))
