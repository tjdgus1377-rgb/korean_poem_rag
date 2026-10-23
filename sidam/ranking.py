"""저장된 벡터로 수행하는 선택적 MMR."""
import math


def cosine(left, right):
    if len(left) != len(right) or not all(math.isfinite(x) for x in list(left) + list(right)):
        raise ValueError('임베딩 차원·유한 값을 확인하세요.')
    denominator = math.sqrt(sum(x*x for x in left) * sum(x*x for x in right))
    return sum(a*b for a,b in zip(left,right)) / denominator if denominator else 0.


def mmr_select(query, candidates, k, weight=.5, seeds=()):
    if type(k) is not int or k < 0 or isinstance(weight, bool) or not isinstance(weight, (int,float)) or not math.isfinite(weight) or not 0 <= weight <= 1:
        raise ValueError('MMR 개수·lambda 설정 오류')
    remaining = dict(candidates)
    selected, previous = [], list(seeds)
    while remaining and len(selected) < k:
        def score(ident):
            vector = remaining[ident]
            relevance = cosine(query, vector)
            return weight * relevance - (1-weight) * max(cosine(vector,s) for s in previous) if previous else relevance
        chosen = min(remaining, key=lambda ident: (-score(ident),ident))
        previous.append(remaining.pop(chosen))
        selected.append(chosen)
    return selected
