"""같은 질문 임베딩을 재사용해 similarity/MMR의 근거를 비교한다."""
import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from sidam.config import Config
from sidam.data import read_jsonl
from sidam.evaluation import ranking_metrics
from sidam.service import Service

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=ROOT)
    args = parser.parse_args()
    service = Service(Config.load(args.root))
    service.require_models()
    cache = {}
    embed = service.models.embed_query
    def shared_embedding(question):
        if question not in cache: cache[question] = embed(question)
        return cache[question]
    service.store.embeddings.embed_query = shared_embedding
    rows=[]
    for case in read_jsonl(ROOT/'evaluation/answers_v1.jsonl'):
        for method in ('similarity','mmr'):
            hits=service.store.retrieve(case['poem_id'],case['question'],search_type=method)[1:]
            rows.append({'case_id':case['case_id'],'method':method,'poem_id':case['poem_id'],
                         'source_ids':[h['source_id'] for h in hits], 'chunk_ids':[h['chunk_id'] for h in hits],
                         'unique_sources':len({h['source_id'] for h in hits}),
                         'metrics':ranking_metrics([h['source_id'] for h in hits],case['gold_source_ids'],service.config.top_k),
                         'isolated':all(h['poem_id']==case['poem_id'] for h in hits)})
    path=ROOT/'evaluation/runs'/f'retrieval-{time.time_ns()}.json'
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'cases':len(rows)//2,'query_embedding_calls':len(cache),'output':str(path),'results':rows},ensure_ascii=False))
