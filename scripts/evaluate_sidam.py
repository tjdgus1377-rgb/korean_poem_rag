"""고정 검색/원문 공통 RAG 비교. 정답은 평가에만 사용한다."""
import argparse
import hashlib
import inspect
import json
import sys
import time
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from sidam.citations import citation_numbers, cited_sources
from sidam.comparison import compare_case
from sidam.config import Config
from sidam.data import read_jsonl
from sidam.evaluation import filter_accuracy, ranking_metrics, validate_benchmark
from sidam.prompts import BOUNDARY, Prompts
from sidam.repro import verify_index, verify_manifest, verify_settings
from sidam.service import Service


def run(args):
    config=Config.load(args.root)
    service=Service(config); service.require_models()
    manifest=verify_manifest(args.root); verify_settings(config,manifest); verify_index(service.store,manifest)
    paths={name:ROOT/f'evaluation/{name}_v1.jsonl' for name in ('search','answers')}
    search,questions=(read_jsonl(paths[name]) for name in ('search','answers'))
    validate_benchmark(search,questions,service.poems,service.docs)
    if not args.search_only and not 5 <= args.limit <= len(questions):
        raise ValueError('답변 비교는 고정 질문 5개 이상이어야 합니다.')
    result={'schema_version':1,'model':config.chat_model,'embedding_model':config.embedding_model,
            'generation_options':{'temperature':'공급자 기본값(미지정)','seed':'공급자 기본값(미지정)'},
            'prompt_sha256':hashlib.sha256((inspect.getsource(Prompts.answer)+BOUNDARY).encode()).hexdigest(),
            'dataset_sha256':{name:hashlib.sha256(p.read_text(encoding='utf-8-sig').replace('\r\n','\n').encode()).hexdigest() for name,p in paths.items()},
            'baseline':manifest,'retrieval_method':args.method,'search':[],'comparisons':[]}
    path=ROOT/'evaluation/runs'/f'comparison-{time.time_ns()}.json'
    path.parent.mkdir(parents=True,exist_ok=True)
    def save(): path.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    if not args.answers_only:
        for case in search:
            start=time.monotonic()
            try:
                poems,conditions=service.search(case['query']); predicted=[p['poem_id'] for p in poems]
                row={'case_id':case['case_id'],'category':case['category'],'predicted_poem_ids':predicted,
                     'metrics':{str(k):ranking_metrics(predicted,case['gold_poem_ids'],k) for k in (1,5,10)},
                     'filter_accuracy':filter_accuracy(poems,case['conditions']),'conditions':conditions}
            except Exception as error:
                row={'case_id':case['case_id'],'error_type':type(error).__name__}
            row['total_seconds']=time.monotonic()-start
            result['search'].append(row); save()
    originals={d['poem_id']:d for d in service.docs if d['document_type']=='poem_text'}
    if not args.search_only:
        for index,case in enumerate(questions[:args.limit]):
            try:
                pair=compare_case(case,service.poems[case['poem_id']],originals[case['poem_id']],service.store,service.prompts,args.method,reverse=bool(index%2))
                for arm in pair['arms'].values():
                    arm['cited_source_ids']=[s['source_id'] for _,s in cited_sources(arm['answer'],arm['sources'])]
                result['comparisons'].append(pair)
            except Exception as error:
                result['comparisons'].append({'case_id':case['case_id'],'error_type':type(error).__name__})
            save()
            print(json.dumps({'completed_case':case['case_id'],'output':str(path)},ensure_ascii=False),flush=True)
    verify_index(service.store,manifest)
    print(json.dumps({'search_cases':len(result['search']),'answer_cases':len(result['comparisons']),'output':str(path)},ensure_ascii=False))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,default=ROOT)
    group=parser.add_mutually_exclusive_group()
    group.add_argument('--search-only',action='store_true'); group.add_argument('--answers-only',action='store_true')
    parser.add_argument('--limit',type=int,default=12)
    parser.add_argument('--method',choices=['similarity','mmr'],default='similarity')
    run(parser.parse_args())
