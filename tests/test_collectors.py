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
    service.collect({"poem_id": "b"}, "다른 작품")
    assert adapter.calls == 2


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
