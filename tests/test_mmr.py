import pytest

from sidam.ranking import mmr_select


def test_mmr_balances_relevance_and_redundancy_and_ties():
    rows = [('a', [1., 0.]), ('b', [.999, .001]), ('c', [.8, .6])]
    assert mmr_select([1., 0.], rows, 2, .3) == ['a', 'c']
    assert mmr_select([1., 0.], rows, 2, 1.) == ['a', 'b']
    assert mmr_select([1., 0.], rows[1:], 1, .3, seeds=[[1.,0.]]) == ['c']
    assert mmr_select([0., 0.], [('b',[0.,0.]),('a',[0.,0.])], 2) == ['a', 'b']
    assert mmr_select([1.,0.], rows + rows, 4) == ['a','b','c'] or len(mmr_select([1.,0.],rows+rows,4)) == 3
    for weight in [-1, 2, float('nan')]:
        with pytest.raises(ValueError): mmr_select([1.,0.], rows, 2, weight)


def test_mmr_store_keeps_metadata_poem_filter_and_reserved_quote(tmp_path, corpus_dir, embeddings):
    from sidam.data import load_corpus, load_documents
    from sidam.store import VectorStore
    store = VectorStore(tmp_path/'db', embeddings, chunk_size=80, overlap=10, top_k=2)
    poems=load_corpus(corpus_dir); docs,_=load_documents(corpus_dir, poems)
    store.sync_poems(poems); store.sync_sources(docs)
    hits=store.retrieve('a','이별','첫 구절',search_type='mmr')
    assert hits[0]['document_type']=='metadata'
    assert len(hits)<=3
    assert all(h['poem_id']=='a' for h in hits)
    assert any(h.get('document_type')=='poem_text' and '첫 구절' in h['text'] for h in hits[1:])
    assert store.retrieve('a','이별') == store.retrieve('a','이별',search_type='similarity')
    with pytest.raises(ValueError): store.retrieve('a','이별',search_type='bad')
