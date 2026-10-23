"""공통 원문을 제공하는 외부 해설 유무 비교."""
import hashlib
import json
import time

from .pipeline import build_graph


class FixedEvidence:
    def __init__(self, rows):
        self.rows = rows

    def retrieve(self, *args, **kwargs):
        return self.rows


def compare_case(case, poem, original, store, prompts, method='similarity', reverse=False):
    if method not in {'similarity','mmr'}:
        raise ValueError('비교 검색 방식 오류')
    pid = poem['poem_id']
    if original.get('poem_id') != pid or original.get('document_type') != 'poem_text' or original.get('rights_status') != 'verified' or not original.get('text'):
        raise ValueError('비교 공통 원문의 작품·이용 범위를 확인하세요.')
    started=time.monotonic()
    retrieved=store.retrieve(pid,case['question'],search_type=method)
    external=[s for s in retrieved if s.get('document_type') not in {'metadata','poem_text'}]
    if any(s.get('poem_id') != pid or s.get('rights_status') != 'verified' for s in external):
        raise ValueError('비교 외부 근거의 작품·이용 범위를 확인하세요.')
    retrieval_seconds=time.monotonic()-started
    clean_poem={k:poem[k] for k in ('poem_id','title','author')}
    order=['with_external','without_external'] if reverse else ['without_external','with_external']
    arms={}
    for arm in order:
        sources=[original] + (external if arm=='with_external' else [])
        result=build_graph(FixedEvidence(sources),prompts).invoke({'poem':clean_poem,'question':case['question'],'messages':[]})
        extra=retrieval_seconds if arm=='with_external' else 0.
        arms[arm]={'answer':result['answer'],'sources':sources,'citation_error':result['citation_error'],
                   'timings':{'external_retrieve_seconds':extra,'generate_seconds':result['timings']['generate_seconds'],
                              'total_seconds':extra+sum(result['timings'].values())},
                   'semantic_review':None}
    digest=hashlib.sha256(json.dumps([clean_poem,original['text']],ensure_ascii=False,sort_keys=True).encode()).hexdigest()
    return {'case_id':case['case_id'],'poem_id':pid,'order':order,'retrieval_method':method,'common_input_sha256':digest,'external_count':len(external),'arms':arms}
