def test_index_is_idempotent_and_filters_poems(tmp_path, corpus_dir, embeddings):
    from sidam.data import load_corpus, load_documents
    from sidam.store import VectorStore
    poems = load_corpus(corpus_dir)
    docs, _ = load_documents(corpus_dir, poems)
    store = VectorStore(tmp_path / "db", embeddings, chunk_size=80, overlap=10)
    store.sync_poems(poems)
    for d in docs:
        store.sync_source(d)
    before = store.counts()
    store.sync_poems(poems)
    for d in docs:
        store.sync_source(d)
    assert store.counts() == before
    assert before["poems"] == 3
    hits = store.retrieve("a", "이별", quote="첫 구절")
    assert hits[0]["document_type"] == "metadata"
    assert all(x["poem_id"] == "a" for x in hits)
    assert all(x.get("content_hash") for x in hits)
    assert any("첫 구절" in x["text"] for x in hits[1:])


def test_rechunk_removes_only_own_stale_chunks(tmp_path, embeddings):
    from sidam.store import VectorStore
    store = VectorStore(tmp_path / "db", embeddings, chunk_size=40, overlap=5)
    doc = dict(poem_id="a", source_id="shared", source_title="문서", source_url="https://example.org/a", text="긴 해설 문장입니다. " * 30,
               document_type="commentary", evidence_role="interpretation", rights_status="verified", content_origin="curated_summary")
    store.sync_source(doc)
    store.sync_source({**doc, "poem_id": "b"})
    other = store.evidence.get(where={"poem_id": "b"})["ids"]
    store.sync_source({**doc, "text": "짧은 해설"})
    assert len(store.evidence.get(where={"poem_id": "a"})["ids"]) == 1
    assert store.evidence.get(where={"poem_id": "b"})["ids"] == other


def test_empty_lookup_and_embedding_mismatch(tmp_path, embeddings):
    import pytest
    from sidam.store import VectorStore
    store = VectorStore(tmp_path / "db", embeddings)
    assert store.retrieve("missing", "질문") == []
    embeddings.model = "different-model"
    with pytest.raises(ValueError, match="임베딩"):
        VectorStore(tmp_path / "db", embeddings)


def test_unverified_doc_never_indexed(tmp_path, embeddings):
    import pytest
    from sidam.store import VectorStore
    store = VectorStore(tmp_path / "db", embeddings)
    with pytest.raises(ValueError, match="이용"):
        store.sync_source({"poem_id": "a", "source_id": "x", "text": "금지", "rights_status": "pending"})


def test_bulk_index_embeds_together_and_skips_unchanged(tmp_path, embeddings):
    from sidam.store import VectorStore
    calls = []
    original = embeddings.embed_documents
    def counting(texts):
        calls.append(len(texts))
        return original(texts)
    embeddings.embed_documents = counting
    store = VectorStore(tmp_path / "bulk", embeddings)
    docs = [{"poem_id": "a", "source_id": str(i), "text": f"해설 {i}", "rights_status": "verified"} for i in range(4)]
    store.sync_sources(docs)
    assert calls == [4]
    store.sync_sources(docs)
    assert calls == [4]


def test_full_sync_removes_revoked_sources_and_empty_update(tmp_path, embeddings):
    from sidam.store import VectorStore
    store = VectorStore(tmp_path / 'reconcile', embeddings)
    a = {'poem_id': 'a', 'source_id': 'allowed', 'text': '허용 해설', 'rights_status': 'verified'}
    b = {**a, 'source_id': 'revoked', 'text': '이용 중단 해설'}
    store.sync_sources([a, b])
    store.sync_sources([a], replace_all=True)
    assert set(store.evidence.get()['ids']) == {'a:allowed:0001'}
    store.sync_source({**a, 'text': ''})
    assert store.evidence.count() == 0
