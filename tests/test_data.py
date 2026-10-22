import csv

import pytest


def test_corpus_preserves_ids_and_distinguishes_years(corpus_dir):
    from sidam.data import load_corpus, search_text
    poems = load_corpus(corpus_dir)
    assert set(poems) == {"a", "b", "c"}
    assert poems["a"]["first_publication_year"] == 1922
    assert poems["b"]["reported_year"] == 1949
    assert poems["b"].get("first_publication_year") is None
    assert poems["b"]["collection_publication_year"] == 1949
    assert poems["c"]["reported_year"] is None
    assert "미확인" in search_text(poems["b"])
    assert "이별" in search_text(poems["a"])
    assert poems["a"]["theme_evidence_ids"] == ["n1", "n2"]
    assert "해방" not in search_text(poems["b"])


def test_duplicate_ids_and_missing_full_text_are_rejected(corpus_dir):
    from sidam.data import load_corpus
    path = corpus_dir / "poems_metadata.csv"
    original = path.read_text(encoding="utf-8")
    path.write_text(original + original.splitlines()[1] + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match="중복"):
        load_corpus(corpus_dir)
    path.write_text(original, encoding="utf-8")
    (corpus_dir / "poems_text.jsonl").write_text("", encoding="utf-8")
    with pytest.raises(ValueError, match="전문"):
        load_corpus(corpus_dir)


def test_documents_exclude_unread_and_unlicensed_and_group_notes(corpus_dir):
    from sidam.data import load_corpus, load_documents
    docs, excluded = load_documents(corpus_dir, load_corpus(corpus_dir))
    source = [d for d in docs if d["source_id"] == "s1"]
    assert len(source) == 1
    assert "이별" in source[0]["text"] and "반복" in source[0]["text"]
    assert source[0]["content_origin"] == "curated_summary"
    assert source[0]["poem_id"] == "a"
    assert not any(d["source_id"] in {"lead", "restricted"} for d in docs)
    assert len([d for d in docs if d["document_type"] == "poem_text"]) == 3
    assert excluded


def test_actual_corpus_is_100_without_guessing_year():
    from pathlib import Path
    from sidam.data import load_corpus
    poems = load_corpus(Path(__file__).resolve().parents[1] / "data")
    assert len(poems) == 100
    assert poems["13313827"].get("first_publication_year") is None
    assert poems["13313827"]["reported_year"] == 1949
    assert poems["9001035"]["reported_year"] is None
