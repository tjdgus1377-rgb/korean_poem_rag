"""유료 API와 무관한 인수 테스트용 작은 자료."""
import csv
import hashlib
import json
import math
import tempfile
from pathlib import Path

import pytest

# Streamlit도 sandbox 밖의 Windows 임시 폴더를 쓰지 않게 한다.
_runtime_tmp = Path(__file__).resolve().parents[1] / "tmp/runtime"
_runtime_tmp.mkdir(parents=True, exist_ok=True)
tempfile.tempdir = str(_runtime_tmp)


class FakeEmbeddings:
    """테스트 전용. 서비스의 의미 임베딩 대체물이 아니다."""

    model = "test-only-hash-v1"

    def embed_documents(self, texts):
        result = []
        for text in texts:
            vec = [0.0] * 32
            for char in text:
                vec[hashlib.sha256(char.encode()).digest()[0] % 32] += 1
            length = math.sqrt(sum(v * v for v in vec)) or 1
            result.append([v / length for v in vec])
        return result

    def embed_query(self, text):
        return self.embed_documents([text])[0]


@pytest.fixture
def embeddings():
    return FakeEmbeddings()


@pytest.fixture
def corpus_dir(tmp_path):
    root = tmp_path / "data"
    root.mkdir()
    (root / "curation").mkdir()
    rows = [
        {"id": "a", "title": "진달래꽃", "author": "김소월", "publication_year": "1922"},
        {"id": "b", "title": "그날이 오면", "author": "심훈", "publication_year": "1949"},
        {"id": "c", "title": "황혼", "author": "이육사", "publication_year": ""},
    ]
    for row in rows:
        row.update(metadata_source_url="https://encykorea.aks.ac.kr/a", text_source_url="https://ko.wikisource.org/a")
    with (root / "poems_metadata.csv").open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
    texts = [{"id": r["id"], "text": f"{r['title']}의 첫 구절\n둘째 구절"} for r in rows]
    notes = [
        {"poem_id": "a", "note_id": "n1", "source_id": "s1", "source_title": "작품 해설", "source_url": "https://encykorea.aks.ac.kr/a", "locator": "내용", "evidence_summary": "이별의 슬픔과 정한을 설명한다.", "evidence_role": "interpretation", "access_status": "공개 본문 확인"},
        {"poem_id": "a", "note_id": "n2", "source_id": "s1", "source_title": "작품 해설", "source_url": "https://encykorea.aks.ac.kr/a", "locator": "특징", "evidence_summary": "반복되는 표현을 설명한다.", "evidence_role": "interpretation", "access_status": "공개 본문 확인"},
        {"poem_id": "b", "note_id": "lead", "source_id": "lead", "source_url": "https://encykorea.aks.ac.kr/b", "evidence_summary": "열람하지 않은 해방 해설", "evidence_role": "access_lead"},
        {"poem_id": "c", "note_id": "blocked", "source_id": "restricted", "source_url": "https://example.org/c", "evidence_summary": "허가 미확인", "evidence_role": "interpretation", "access_status": "공개 본문 확인"},
    ]
    for name, records in [("poems_text.jsonl", texts), ("evidence_notes.jsonl", notes)]:
        (root / name).write_text("\n".join(json.dumps(x, ensure_ascii=False) for x in records), encoding="utf-8")
    (root / "curation/field_overrides.json").write_text(json.dumps({
        "a": {"first_publication_year": 1922, "year_evidence_ids": ["n1"]},
        "b": {"collection_publication_year": 1949, "year_evidence_ids": ["reviewed-b"]},
    }), encoding="utf-8")
    policy = {"allowed_domains": {"encykorea.aks.ac.kr": {"usage_terms": "공식 본문 이용 안내", "policy_url": "https://encykorea.aks.ac.kr/Guide/ContentUse"}},
              "poem_authors": {r["author"]: {"usage_terms": "만료 원작", "evidence_url": r["metadata_source_url"]} for r in rows}}
    (root / "curation/source_policy.json").write_text(json.dumps(policy), encoding="utf-8")
    return root
