class Adapter:
    def __init__(self, fail=False):
        self.calls = 0
        self.fail = fail
    def search(self, query):
        self.calls += 1
        if self.fail:
            raise TimeoutError("외부 장애")
        return []
    def fetch(self, candidate, poem):
        raise AssertionError("빈 검색 결과의 본문 수집 금지")


class P:
    def queries(self, poem, question):
        return ["작품 검색"]
    def select_documents(self, poem, question, candidates):
        return []


def test_normal_empty_cache_prevents_recollection(tmp_path):
    from sidam.collectors import CollectionService
    adapter = Adapter()
    service = CollectionService(tmp_path / "cache.sqlite3", adapter, P())
    poem = {"poem_id": "a"}
    assert service.collect(poem, "질문") == []
    assert service.collect(poem, "같은 검색어") == []
    assert adapter.calls == 1
    assert set(service.timings) == {'p1_seconds', 'search_seconds', 'p2_seconds', 'fetch_seconds'}
    service.collect({"poem_id": "b"}, "다른 작품")
    assert adapter.calls == 2


def test_selection_audit_records_included_and_excluded(tmp_path):
    from sidam.collectors import CollectionService
    class CandidateAdapter(Adapter):
        def search(self, query):
            return [{"candidate_id": "own", "title": "진달래꽃", "snippet": "김소월의 작품"}, {"candidate_id": "other", "title": "다른 문서", "snippet": "무관"}]
        def fetch(self, candidate, poem):
            return {"source_id": candidate["candidate_id"], "text": "실제 작품 문서"}
    service = CollectionService(tmp_path / "cache.sqlite3", CandidateAdapter(), P())
    result = service.collect({"poem_id": "a", "title": "진달래꽃", "author": "김소월"}, "질문")
    assert [r["source_id"] for r in result] == ["own"]
    audit = service.manifest()
    assert audit[0]["selected_ids"] == ["own"]
    assert audit[0]["rejected_ids"] == ["other"]


def test_failed_collection_not_cached_as_success(tmp_path):
    from sidam.collectors import CollectionService
    adapter = Adapter(fail=True)
    service = CollectionService(tmp_path / "cache.sqlite3", adapter, P())
    service.collect({"poem_id": "a"}, "질문")
    adapter.fail = False
    service.collect({"poem_id": "a"}, "질문")
    assert adapter.calls == 2


def test_wiki_contact_required_before_network():
    import pytest
    from sidam.collectors import WikiAdapter
    with pytest.raises(ValueError, match="연락처"):
        WikiAdapter("")


def test_collection_model_failures_warn_and_can_retry(tmp_path):
    from sidam.collectors import CollectionService
    from sidam.models import ModelError
    class FailingP(P):
        def queries(self, poem, question):
            raise ModelError('모델 장애')
    service = CollectionService(tmp_path / 'model.sqlite3', Adapter(), FailingP())
    assert service.collect({'poem_id': 'a'}, '질문') == []
    assert service.warnings


def test_p2_model_failure_preserves_verified_work(tmp_path):
    from sidam.collectors import CollectionService
    from sidam.models import ModelError
    class FailingSelection(P):
        def select_documents(self, *args):
            raise ModelError('장애')
    class OwnAdapter(Adapter):
        def search(self, query):
            return [{'candidate_id': 'own', 'title': '향수', 'snippet': '정지용의 시'}]
        def fetch(self, candidate, poem):
            return {'poem_id': 'a', 'source_id': 'own', 'text': '향수는 정지용의 시이다.'}
    service = CollectionService(tmp_path / 'own.sqlite3', OwnAdapter(), FailingSelection())
    result = service.collect({'poem_id': 'a', 'title': '향수', 'author': '정지용'}, '질문')
    assert [d['source_id'] for d in result] == ['own']
    assert service.warnings
    class SelectFailure(P):
        def select_documents(self, poem, question, candidates):
            raise ModelError('모델 장애')
    class Candidates(Adapter):
        def search(self, query):
            return [{'candidate_id': 'x', 'title': '다른 문서', 'snippet': ''}]
    service = CollectionService(tmp_path / 'select.sqlite3', Candidates(), SelectFailure())
    assert service.collect({'poem_id': 'a', 'title': '향수', 'author': '정지용'}, '질문') == []
    assert service.warnings
