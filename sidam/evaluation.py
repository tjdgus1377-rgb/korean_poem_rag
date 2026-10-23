"""고정 평가 데이터 검증과 검색 지표. 평가 내용을 색인에 공급하지 않는다."""
from .search import matches_conditions


def ranking_metrics(predicted, gold, k=5):
    if type(k) is not int or k < 1:
        raise ValueError('k는 양의 정수여야 합니다.')
    gold = set(gold)
    if not gold:
        return {'recall': None, 'mrr': None, 'empty_correct': not predicted}
    found = set(predicted[:k]) & gold
    reciprocal = next((1 / i for i, pid in enumerate(predicted, 1) if pid in gold), 0.0)
    return {'recall': len(found) / len(gold), 'mrr': reciprocal, 'empty_correct': None}


def validate_benchmark(search_cases, answer_cases, poems, documents):
    required = {'exact', 'partial', 'spacing', 'typo', 'hanja', 'author_alias', 'shorthand', 'year', 'theme', 'synonym', 'emotion', 'homonym', 'edition', 'verse', 'unanswerable'}
    if not required <= {c.get('category') for c in search_cases} or len(answer_cases) < 5:
        raise ValueError('필수 평가 범주·질문 수 누락')
    ids = [c.get('case_id') for c in search_cases + answer_cases]
    if not all(isinstance(i, str) and i for i in ids) or len(set(ids)) != len(ids):
        raise ValueError('평가 ID 누락·중복')
    allowed = {(d['poem_id'], d['source_id']) for d in documents if d.get('rights_status') == 'verified'}
    for c in search_cases:
        if not c.get('query') or not c.get('provenance') or not isinstance(c.get('gold_poem_ids'), list) or not set(c['gold_poem_ids']) <= poems.keys():
            raise ValueError('작품 검색 정답·출처 오류')
        if any(not matches_conditions(poems[pid], c.get('conditions', {})) for pid in c['gold_poem_ids']):
            raise ValueError('골드 작품과 명시 조건 불일치')
    for c in answer_cases:
        if c.get('poem_id') not in poems or not c.get('question') or type(c.get('expected_abstention')) is not bool:
            raise ValueError('근거 질문의 작품·형식 오류')
        if not all(c.get(k) and isinstance(c[k], list) for k in ('minimum_points', 'allowed_interpretations', 'forbidden_claims', 'provenance')):
            raise ValueError('답변 판정 기준 누락')
        sources = c.get('gold_source_ids')
        if not isinstance(sources, list) or any((c['poem_id'], s) not in allowed for s in sources) or (not sources and not c['expected_abstention']):
            raise ValueError('정답 근거의 작품 연결·이용 범위 오류')
    return {'search': len(search_cases), 'answers': len(answer_cases)}


def filter_accuracy(results, conditions):
    if not results:
        return None
    return sum(matches_conditions(p, conditions) for p in results) / len(results)
