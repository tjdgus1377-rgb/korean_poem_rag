def test_reindex_reloads_policy_and_preserves_only_allowed_cache(tmp_path, corpus_dir, embeddings):
    import json
    from types import SimpleNamespace
    from sidam.collectors import CollectionService
    from sidam.data import load_corpus, load_documents
    from sidam.service import Service
    from sidam.store import VectorStore
    service = Service.__new__(Service)
    service.config = SimpleNamespace(root=tmp_path, data_dir=corpus_dir)
    service.models = object()
    service.store = VectorStore(tmp_path / 'index', embeddings)
    service.poems = load_corpus(corpus_dir)
    service.docs, service.excluded = load_documents(corpus_dir, service.poems)
    cache = CollectionService(tmp_path / '.sidam/collection.sqlite3', None, None)
    import sqlite3
    cached = {'poem_id': 'a', 'source_id': 'cached', 'source_url': 'https://encykorea.aks.ac.kr/c', 'text': '수집한 해설', 'rights_status': 'verified'}
    with sqlite3.connect(cache.path) as db:
        db.execute('INSERT INTO queries VALUES (?,?,?)', ('x', 'success', json.dumps([cached, {**cached, 'source_id': 's1'}])))
    service.index()
    assert service.store.evidence.get(where={'source_id': 'cached'})['ids']
    summaries = service.store.evidence.get(where={'source_id': 's1'}, include=['documents'])['documents']
    assert summaries and all('수집한 해설' not in text for text in summaries)
    service.index(include_cache=False)
    assert not service.store.evidence.get(where={'source_id': 'cached'})['ids']
    path = corpus_dir / 'curation/source_policy.json'
    policy = json.loads(path.read_text())
    policy['allowed_domains'] = {}
    path.write_text(json.dumps(policy))
    service.index()
    metadata = service.store.evidence.get(include=['metadatas'])['metadatas']
    assert all(m['document_type'] == 'poem_text' for m in metadata)
    assert all(not p['theme_summary'] for p in service.poems.values())


def test_question_cannot_reintroduce_revoked_cached_sources(tmp_path, corpus_dir, embeddings, monkeypatch):
    import json
    from types import SimpleNamespace
    import sidam.service as module
    from sidam.data import load_corpus
    from sidam.store import VectorStore
    service = module.Service.__new__(module.Service)
    service.config = SimpleNamespace(root=tmp_path, data_dir=corpus_dir, wiki_contact='test@example.org')
    service.models = object()
    service.poems, service.docs = load_corpus(corpus_dir), []
    service.store = VectorStore(tmp_path / 'ask', embeddings)
    service.store.sync_poems(service.poems)
    service.prompts = SimpleNamespace(answer=lambda *a, **k: '작품 정보입니다. [근거 1]')
    cached = {'poem_id': 'a', 'source_id': 'revoked', 'source_url': 'https://encykorea.aks.ac.kr/c', 'text': '금지된 해설', 'rights_status': 'verified'}
    collector = SimpleNamespace(collect=lambda *a: [cached], manifest=lambda: [], warnings=[], timings={})
    monkeypatch.setattr(module, 'CollectionService', lambda *a: collector)
    path = corpus_dir / 'curation/source_policy.json'
    policy = json.loads(path.read_text())
    policy['allowed_domains'] = {}
    path.write_text(json.dumps(policy))
    result = service.ask('a', '질문')
    assert not service.store.evidence.get(where={'source_id': 'revoked'})['ids']
    assert result['warnings']
