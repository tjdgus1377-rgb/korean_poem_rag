import json
from pathlib import Path

import pytest


def test_public_snapshot_preserves_source_but_rejects_private_fields(corpus_dir):
    from sidam.data import load_corpus, load_documents
    poem = load_corpus(corpus_dir)['a']
    directory = corpus_dir / 'repro'
    directory.mkdir()
    path = directory / 'public_documents.jsonl'
    doc = dict(poem_id='a', poem_title=poem['title'], author=poem['author'], source_id='WIKI_123', source_title='공개 문서', source_url='https://encykorea.aks.ac.kr/c', text='확인한 공개 맥락', source_type='위키백과', document_type='commentary', evidence_role='context_only', content_origin='original_text', access_scope='API 본문 확인', locator='본문', rights_status='verified', usage_terms='CC BY-SA 4.0', collected_at='2026-10-22T00:00:00Z')
    path.write_text(json.dumps(doc, ensure_ascii=False), encoding='utf-8')
    docs, _ = load_documents(corpus_dir, load_corpus(corpus_dir))
    assert any(d['source_id'] == 'WIKI_123' and d['text'] == doc['text'] for d in docs)
    path.write_text(json.dumps({**doc, 'search_query': '개인 질문'}), encoding='utf-8')
    with pytest.raises(ValueError, match='스냅샷'):
        load_documents(corpus_dir, load_corpus(corpus_dir))


def test_manifest_detects_changed_source_and_config_without_key(corpus_dir, monkeypatch):
    from sidam.repro import build_manifest, verify_manifest
    monkeypatch.setenv('GMS_KEY', '')
    root = corpus_dir.parent
    paths = ['data/poems_metadata.csv', 'data/poems_text.jsonl', 'data/evidence_notes.jsonl', 'data/curation/source_policy.json']
    directory = corpus_dir / 'repro'
    directory.mkdir()
    manifest = build_manifest(root, input_files=paths)
    assert manifest['counts']['poems'] == 3
    path = directory / 'manifest.json'
    path.write_text(json.dumps(manifest), encoding='utf-8')
    assert verify_manifest(root, required_inputs=paths)['counts'] == manifest['counts']
    notes = corpus_dir / 'evidence_notes.jsonl'
    notes.write_text(notes.read_text(encoding='utf-8') + '\n', encoding='utf-8')
    with pytest.raises(ValueError, match='재현'):
        verify_manifest(root, required_inputs=paths)
    notes.write_text(notes.read_text(encoding='utf-8').rstrip() + '\n', encoding='utf-8')


def test_repro_file_hash_ignores_git_newlines_but_requires_inputs(corpus_dir):
    from sidam.repro import build_manifest, verify_manifest
    root = corpus_dir.parent
    files = ['data/poems_metadata.csv']
    before = build_manifest(root, input_files=files)
    csv = corpus_dir / 'poems_metadata.csv'
    csv.write_bytes(csv.read_bytes().replace(b'\r\n', b'\n').replace(b'\n', b'\r\n'))
    assert build_manifest(root, input_files=files) == before
    (corpus_dir / 'repro').mkdir()
    (corpus_dir / 'repro/manifest.json').write_text(json.dumps(before))
    with pytest.raises(ValueError, match='필수'):
        verify_manifest(root)


def test_manifest_chunk_fingerprint_matches_real_store(corpus_dir, tmp_path, embeddings):
    from sidam.repro import build_manifest, verify_index
    from sidam.data import load_corpus, load_documents
    from sidam.store import VectorStore
    poems = load_corpus(corpus_dir)
    docs, _ = load_documents(corpus_dir, poems)
    report = build_manifest(corpus_dir.parent, input_files=['data/poems_text.jsonl'])
    store = VectorStore(tmp_path / 'db', embeddings)
    store.sync_poems(poems)
    store.sync_sources(docs, replace_all=True)
    verify_index(store, report)
    store.evidence.update(ids=[store.evidence.get()['ids'][0]], documents=['잘못 바뀐 본문'], embeddings=embeddings.embed_documents(['잘못 바뀐 본문']))
    with pytest.raises(ValueError, match='색인'):
        verify_index(store, report)


def test_release_baseline_and_lock_are_complete():
    from sidam.repro import verify_manifest
    root = Path(__file__).resolve().parents[1]
    report = verify_manifest(root)
    assert report['counts']['poems'] == 100
    assert report['counts']['documents'] >= 337
    assert report['counts']['poem_evidence'] >= 341
    assert '.env' not in report['inputs']
    assert 'requirements.lock' in report['inputs']
    assert all(not line.split('=', 1)[1].strip() for line in (root / '.env.example').read_text().splitlines() if line.startswith(('GMS_KEY=', 'WIKI_CONTACT=')))


def test_baseline_rejects_different_provider_or_model(corpus_dir):
    from dataclasses import replace
    from sidam.config import Config
    from sidam.repro import build_manifest, verify_settings
    config = Config(corpus_dir.parent)
    report = build_manifest(config.root, input_files=['data/poems_text.jsonl'])
    verify_settings(config, report)
    with pytest.raises(ValueError, match='모델'):
        verify_settings(replace(config, embedding_model='different-model'), report)
    with pytest.raises(ValueError, match='모델'):
        verify_settings(replace(config, base_url='https://other.invalid/v1/'), report)
