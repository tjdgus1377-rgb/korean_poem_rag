from types import SimpleNamespace

import pytest

from sidam.collectors import CollectionService
from sidam.models import ModelError
from test_collectors import Adapter, P


class CountingPlans(P):
    query_cache_identity = 'model-a:p1-v1'

    def __init__(self):
        self.calls = 0
        self.fail = False

    def queries(self, poem, question):
        self.calls += 1
        if self.fail:
            raise ModelError('가짜 장애')
        return ['작품 검색']


def test_same_question_plan_reused_but_model_and_poem_are_isolated(tmp_path):
    prompts = CountingPlans()
    adapter = Adapter()
    path = tmp_path / 'plans.sqlite3'
    poem = {'poem_id': 'a', 'title': '제목', 'author': '시인'}
    for _ in range(2):
        CollectionService(path, adapter, prompts).collect(poem, '질문')
    assert prompts.calls == 1
    assert adapter.calls == 1
    prompts.query_cache_identity = 'model-b:p1-v1'
    CollectionService(path, adapter, prompts).collect(poem, '질문')
    assert prompts.calls == 2
    CollectionService(path, adapter, prompts).collect({**poem, 'poem_id': 'b'}, '질문')
    assert prompts.calls == 3


def test_plan_cache_does_not_suppress_failed_http_retry_or_model_retry(tmp_path):
    prompts, adapter = CountingPlans(), Adapter(fail=True)
    service = CollectionService(tmp_path / 'retry.sqlite3', adapter, prompts)
    poem = {'poem_id': 'a', 'title': '제목', 'author': '시인'}
    service.collect(poem, '질문')
    adapter.fail = False
    service.collect(poem, '질문')
    assert adapter.calls == 2
    assert prompts.calls == 1
    prompts.fail = True
    service.collect(poem, '새 질문')
    prompts.fail = False
    service.collect(poem, '새 질문')
    assert prompts.calls == 3


def test_new_sources_use_one_batch(corpus_dir, tmp_path, embeddings, monkeypatch):
    import sidam.service as module
    from sidam.data import load_corpus
    from sidam.store import VectorStore
    service = module.Service.__new__(module.Service)
    service.config = SimpleNamespace(root=tmp_path, data_dir=corpus_dir, wiki_contact='test@example.org')
    service.models = object()
    service.poems, service.docs = load_corpus(corpus_dir), []
    service.store = VectorStore(tmp_path / 'index', embeddings)
    service.store.sync_poems(service.poems)
    service.prompts = SimpleNamespace(answer=lambda *a, **k: '설명 [근거 1]')
    docs = [{'poem_id': 'a', 'source_id': str(i), 'source_url': 'https://encykorea.aks.ac.kr/a', 'text': f'확인 해설{i}', 'rights_status': 'verified'} for i in range(3)]
    collector = SimpleNamespace(collect=lambda *a: docs, manifest=lambda: [], warnings=[], timings={})
    monkeypatch.setattr(module, 'CollectionService', lambda *a: collector)
    calls=[]; sync=service.store.sync_sources
    def batch(items, *a, **kw):
        calls.append(len(items)); return sync(items,*a,**kw)
    service.store.sync_sources=batch
    service.ask('a','질문')
    assert calls == [3]


def test_invalid_json_fallback_is_not_cached_as_success(tmp_path):
    from sidam.prompts import Prompts
    class BadJSON:
        chat_model = 'test'
        calls = 0
        def complete(self, *args, **kwargs):
            self.calls += 1
            return 'invalid JSON'
    model = BadJSON()
    service = CollectionService(tmp_path / 'json.sqlite3', Adapter(), Prompts(model))
    poem = {'poem_id': 'a', 'title': '제목', 'author': '시인'}
    service.collect(poem, '질문')
    service.collect(poem, '질문')
    assert model.calls == 4  # 매 호출의 JSON 재시도 2번, HTTP empty 캐시는 별도 재사용
