import pytest


class Responses:
    def __init__(self, *values):
        self.values = iter(values)
    def complete(self, system, payload, json_mode=False):
        return next(self.values)


def test_query_contract_repairs_json_and_includes_own_work():
    from sidam.prompts import Prompts
    p = Prompts(Responses("잘못된 응답", '{"poem_id":"a","search_queries":["이별 해설"]}'))
    result = p.queries({"poem_id": "a", "title": "진달래꽃", "author": "김소월"}, "화자의 태도")
    assert "김소월 진달래꽃 작품 해설" in result


def test_selection_rejects_invented_ids_but_preserves_verified_work():
    from sidam.prompts import Prompts
    p = Prompts(Responses('{"selected_documents":[{"candidate_id":"fake"}]}', '{"selected_documents":[{"candidate_id":"fake"}]}'))
    candidates = [{"candidate_id": "own", "is_work": True}, {"candidate_id": "other", "is_work": False}]
    assert p.select_documents({"poem_id": "a"}, "질문", candidates) == ["own"]


def test_citations_validate_numbers_and_deduplicate():
    from sidam.citations import citation_numbers, cited_sources, invalid_citations
    evidence = [{"source_id": "s1"}, {"source_id": "s2"}]
    assert citation_numbers("설명 [근거 1, 2] 반복 [근거 1]") == {1, 2}
    assert len(cited_sources("[근거 1]", evidence)) == 1
    assert invalid_citations("[근거 0] [근거 3]", evidence) == {0, 3}


def test_condition_validation_and_unknown_year_exclusion(corpus_dir):
    from sidam.data import load_corpus
    from sidam.search import matches_conditions, validate_conditions
    poems = load_corpus(corpus_dir)
    cond = validate_conditions({"year_kind": "first_publication", "year_from": 1920, "year_to": 1950}, poems)
    assert matches_conditions(poems["a"], cond)
    assert not matches_conditions(poems["b"], cond)
    with pytest.raises(ValueError):
        validate_conditions({"year_kind": "DROP TABLE"}, poems)
    with pytest.raises(ValueError):
        validate_conditions({"year_from": 1950, "year_to": 1920}, poems)


def test_quote_validation_and_history_isolation():
    from sidam.session import add_message, history, validate_quote
    state = {}
    add_message(state, "a", {"role": "user", "content": "A 질문"})
    add_message(state, "b", {"role": "user", "content": "B 질문"})
    assert history(state, "a")[0]["content"] == "A 질문"
    assert len(history(state, "a")) == 1
    assert validate_quote("첫 구절\n둘째 구절", "첫  구절")
    assert not validate_quote("첫 구절", "다른 작품")


def test_theme_expression_does_not_become_duplicate_title_filter(corpus_dir):
    from sidam.data import load_corpus
    from sidam.prompts import Prompts
    raw = '{"title_query":"이별","author":"김소월","theme_query":"이별을 다룬 시"}'
    p = Prompts(Responses(raw, raw))
    poems = load_corpus(corpus_dir)
    assert p.conditions('김소월의 이별을 다룬 시', poems)['title_query'] is None
    assert p.conditions('제목에 이별이 들어가고 이별을 다룬 시', poems)['title_query'] == '이별'
