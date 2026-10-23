from pathlib import Path
import copy

import pytest

from sidam.data import load_corpus, load_documents, read_jsonl
from sidam.evaluation import filter_accuracy, ranking_metrics, validate_benchmark


def test_ranking_counts_duplicate_once_without_refilling_cutoff():
    assert ranking_metrics(['x', 'a', 'a', 'b'], ['a', 'b'], 3) == {'recall': .5, 'mrr': .5, 'empty_correct': None}
    assert ranking_metrics(['a', 'a'], ['a', 'a'], 2)['recall'] == 1
    assert ranking_metrics([], [], 5) == {'recall': None, 'mrr': None, 'empty_correct': True}
    assert ranking_metrics(['x'], [], 5)['empty_correct'] is False
    assert ranking_metrics([], ['a'], 5)['recall'] == 0
    for k in [0, -1, True, 1.5]:
        with pytest.raises(ValueError):
            ranking_metrics([], [], k)


def test_frozen_cases_validate_actual_links_and_reject_corruption():
    root = Path(__file__).resolve().parents[1]
    poems = load_corpus(root / 'data')
    docs, _ = load_documents(root / 'data', poems)
    search = read_jsonl(root / 'evaluation/search_v1.jsonl')
    answers = read_jsonl(root / 'evaluation/answers_v1.jsonl')
    result = validate_benchmark(search, answers, poems, docs)
    assert result == {'search': 137, 'answers': 12}
    for mutation in ['poem', 'source', 'duplicate', 'rubric']:
        changed = copy.deepcopy(answers)
        if mutation == 'poem': changed[0]['poem_id'] = 'missing'
        if mutation == 'source': changed[0]['gold_source_ids'] = ['TEXT_9000779']
        if mutation == 'duplicate': changed[1]['case_id'] = changed[0]['case_id']
        if mutation == 'rubric': changed[0]['forbidden_claims'] = []
        with pytest.raises(ValueError):
            validate_benchmark(search, changed, poems, docs)


def test_unknown_first_year_cannot_pass_filter(corpus_dir):
    poems = load_corpus(corpus_dir)
    assert filter_accuracy([poems['a'], poems['b']], {'year_kind': 'first_publication', 'year_from': 1920, 'year_to': 1950}) == .5
    assert filter_accuracy([], {'author': '김소월'}) is None


def test_homonym_gold_carries_explicit_author_filter():
    root = Path(__file__).resolve().parents[1]
    cases = read_jsonl(root / 'evaluation/search_v1.jsonl')
    case = next(c for c in cases if c['query'] == '윤동주 길' and c['category'] == 'homonym')
    poems = load_corpus(root / 'data')
    assert filter_accuracy([poems['9029196']], case['conditions']) == 0
    broken = copy.deepcopy(cases)
    broken[116]['conditions'] = {}
    docs, _ = load_documents(root / 'data', poems)
    with pytest.raises(ValueError, match='시인 조건'):
        validate_benchmark(broken, read_jsonl(root / 'evaluation/answers_v1.jsonl'), poems, docs)


def test_evaluation_and_generated_reports_do_not_enter_ingest(corpus_dir):
    from sidam.chunking import evidence_rows
    from sidam.repro import fingerprint
    poems = load_corpus(corpus_dir)
    before, _ = load_documents(corpus_dir, poems)
    target = corpus_dir.parent / 'evaluation/runs'
    target.mkdir(parents=True)
    (target / 'answers.jsonl').write_text('{"poem_id":"a","text":"오염된 정답"}', encoding='utf-8')
    after, _ = load_documents(corpus_dir, poems)
    assert fingerprint(evidence_rows(before, 1000, 200)) == fingerprint(evidence_rows(after, 1000, 200))
