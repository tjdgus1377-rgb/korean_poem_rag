from pathlib import Path

from sidam.data import load_corpus, read_json
from sidam.identity import lexical_search, title_forms


def test_title_forms_preserve_edition_number():
    assert {'서시', '序詩'} <= title_forms('서시(序詩)')
    assert {'病院', '병원'} <= title_forms('病院 (병원)')
    assert {'유리창1', '琉璃窓1'} <= title_forms('유리창(琉璃窓)1')  # NFKC의 한자 호환 문자 정규화
    assert not title_forms('유리창(琉璃窓)1') & title_forms('유리창(琉璃窓)2')


def test_known_alias_quote_typo_and_homonyms():
    root = Path(__file__).resolve().parents[1]
    poems = load_corpus(root / 'data')
    aliases = read_json(root / 'data/curation/search_aliases.json')
    for query, expected in [('윤동주 서시', {'9000779'}), ('윤동주 序詩', {'9000779'}), ('윤동주 병원', {'9000762'}), ('김해경 거울', {'9000910'}), ('김정식 진달래꽃', {'9000320'}), ('윤동주 별헤밤', {'9000761'}), ('김소월 진달레꽃', {'9000320'}), ('길', {'9000742', '9029196'}), ('윤동주 길', {'9000742'}), ('모란이 피기', {'9000350'}), ('나 보기가 역겨워', {'9000320'})]:
        result = lexical_search(query, poems, aliases)
        assert result is not None, query
        assert set(result[0]) == expected, query
    assert lexical_search('김소월의 이별을 다룬 시', poems, aliases) is None
    assert lexical_search('정지용 바다1', poems, aliases) is None


def test_exact_service_search_does_not_call_llm_or_embedding(corpus_dir):
    from types import SimpleNamespace
    from sidam.service import Service
    service = Service.__new__(Service)
    service.models = object()
    service.config = SimpleNamespace(data_dir=corpus_dir)
    service.poems = load_corpus(corpus_dir)
    service.store = SimpleNamespace(counts=lambda: {'poems': 3})
    result, conditions = service.search('김소월 진달래꽃')
    assert [p['poem_id'] for p in result] == ['a']
    assert conditions['author'] == '김소월'


def test_hanja_work_definition_accepts_correct_author_only():
    from sidam.collectors import WikiAdapter
    from test_http import HTTP, Response
    poem = {'poem_id': 'a', 'title': '서시(序詩)', 'author': '윤동주'}
    for body, accepted in [('서시는 윤동주가 지은 시이다.', True), ('서시는 김철수가 쓴 시이다. 윤동주의 시와 다르다.', False)]:
        http = HTTP([Response(200, {'query': {'pages': [{'pageid': 1, 'title': '서시', 'extract': body}]}})])
        adapter = WikiAdapter('test@example.org', session=http, sleep=lambda _: None)
        assert bool(adapter.fetch({'candidate_id': '1', 'is_work': True}, poem)) == accepted
