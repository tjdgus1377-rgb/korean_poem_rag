import pytest
import requests


class Response:
    def __init__(self, status=200, data=None, retry=None):
        self.status_code, self.data = status, data
        self.headers = {"Retry-After": str(retry)} if retry else {}
    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.RequestException("失敗")
    def json(self):
        return self.data


class HTTP:
    def __init__(self, responses):
        self.responses, self.headers, self.calls = iter(responses), {}, []
    def get(self, url, **kwargs):
        self.calls.append((url, kwargs))
        return next(self.responses)


def test_wiki_honors_retry_after_and_fixed_host():
    from sidam.collectors import WikiAdapter
    http = HTTP([Response(429, retry=2), Response(200, {"query": {"search": []}})])
    sleeps = []
    adapter = WikiAdapter("test@example.org", session=http, sleep=sleeps.append)
    assert adapter.search("진달래꽃") == []
    assert 2 in sleeps
    assert len(http.calls) == 2
    assert all(url == adapter.API for url, _ in http.calls)
    assert "test@example.org" in http.headers["User-Agent"]


def test_wiki_refuses_unbounded_wait_and_wrong_work():
    from sidam.collectors import WikiAdapter
    adapter = WikiAdapter("test@example.org", session=HTTP([Response(429, retry=600)]), sleep=lambda _: None)
    with pytest.raises(requests.RequestException):
        adapter.search("질문")
    http = HTTP([Response(200, {"query": {"pages": [{"pageid": 1, "title": "황혼", "extract": "다른 작가의 작품"}]}})])
    adapter = WikiAdapter("test@example.org", session=http, sleep=lambda _: None)
    assert adapter.fetch({"candidate_id": "1", "is_work": True}, {"poem_id": "a", "title": "황혼", "author": "이육사"}) is None


def test_p2_selected_homonym_still_requires_author():
    from sidam.collectors import WikiAdapter
    http = HTTP([Response(200, {'query': {'pages': [{'pageid': 1, 'title': '향수', 'extract': '다른 작가의 작품이다.'}]}})])
    adapter = WikiAdapter('test@example.org', session=http, sleep=lambda _: None)
    assert adapter.fetch({'candidate_id': '1', 'is_work': False}, {'poem_id': 'a', 'title': '향수', 'author': '정지용'}) is None
