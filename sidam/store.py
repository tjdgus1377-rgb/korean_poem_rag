"""명시적 임베딩과 작품 범위 필터를 사용하는 두 컬렉션."""
import hashlib
import json
from pathlib import Path

import chromadb
from chromadb.config import Settings
from langchain_text_splitters import RecursiveCharacterTextSplitter

from .data import search_text


def scalar_metadata(record):
    return {k: v if isinstance(v, (str, int, float, bool)) else json.dumps(v, ensure_ascii=False)
            for k, v in record.items() if v is not None and k not in {"text", "id", "publication_year"}}


class VectorStore:
    def __init__(self, path, embeddings, chunk_size=1000, overlap=200, top_k=5):
        if not 0 <= overlap < chunk_size or top_k < 1:
            raise ValueError("청크 크기·중복·근거 수 설정이 잘못되었습니다.")
        self.embeddings, self.chunk_size, self.overlap, self.top_k = embeddings, chunk_size, overlap, top_k
        Path(path).mkdir(parents=True, exist_ok=True)
        self.client = chromadb.PersistentClient(path=str(path), settings=Settings(anonymized_telemetry=False))
        self.poems = self.client.get_or_create_collection("poems", metadata={"embedding_model": embeddings.model}, embedding_function=None)
        self.evidence = self.client.get_or_create_collection("poem_evidence", metadata={"embedding_model": embeddings.model}, embedding_function=None)
        for c in (self.poems, self.evidence):
            if (c.metadata or {}).get("embedding_model") != embeddings.model:
                raise ValueError("임베딩 모델이 다른 색인입니다. 별도 경로로 재색인하세요.")

    def counts(self):
        return {"poems": self.poems.count(), "poem_evidence": self.evidence.count()}

    def _upsert(self, collection, rows):
        if not rows:
            return
        old = collection.get(ids=[r["id"] for r in rows], include=["metadatas", "documents"])
        existing = dict(zip(old["ids"], zip(old["documents"], old["metadatas"])))
        changed, metadata_updates = [], []
        for row in rows:
            meta = scalar_metadata(row["metadata"])
            meta["content_hash"] = hashlib.sha256(row["text"].encode()).hexdigest()
            meta["index_hash"] = hashlib.sha256((self.embeddings.model + row["text"]).encode()).hexdigest()
            previous = existing.get(row["id"])
            if not previous or previous[0] != row["text"]:
                changed.append({**row, "metadata": meta})
            elif previous[1] != meta:
                metadata_updates.append({**row, "metadata": meta})
        vectors = []
        for start in range(0, len(changed), 48):
            vectors.extend(self.embeddings.embed_documents([r["text"] for r in changed[start:start + 48]]))
        if len(vectors) != len(changed):
            raise ValueError("임베딩 응답 수가 일치하지 않습니다.")
        for start in range(0, len(changed), 48):
            batch = changed[start:start + 48]
            collection.upsert(ids=[r["id"] for r in batch], documents=[r["text"] for r in batch], metadatas=[r["metadata"] for r in batch], embeddings=vectors[start:start + 48])
        for start in range(0, len(metadata_updates), 48):
            batch = metadata_updates[start:start + 48]
            collection.update(ids=[r["id"] for r in batch], metadatas=[r["metadata"] for r in batch])

    def sync_poems(self, poems):
        rows = [{"id": f"poem:{pid}", "text": search_text(p), "metadata": {**p, "document_type": "metadata", "source_type": "작품 메타데이터", "source_title": f"{p['title']} 작품 정보", "source_url": p["metadata_source_url"], "content_origin": "metadata", "schema_version": 1}} for pid, p in poems.items()]
        self._upsert(self.poems, rows)
        stale = set(self.poems.get()["ids"]) - {r["id"] for r in rows}
        if stale:
            self.poems.delete(ids=sorted(stale))

    def sync_source(self, doc):
        self.sync_sources([doc])

    def sync_sources(self, docs, replace_all=False):
        splitter = RecursiveCharacterTextSplitter(chunk_size=self.chunk_size, chunk_overlap=self.overlap, separators=["\n\n", "\n", ". ", " ", ""])
        rows, old_ids = [], set(self.evidence.get()['ids']) if replace_all else set()
        for doc in docs:
            if doc.get("rights_status") != "verified":
                raise ValueError("이용 조건이 확인된 자료만 색인할 수 있습니다.")
            where = {"$and": [{"poem_id": doc["poem_id"]}, {"source_id": doc["source_id"]}]}
            old_ids.update(self.evidence.get(where=where)["ids"])
            if not doc.get("text", "").strip():
                continue
            chunks = splitter.split_text(doc["text"])
            rows.extend({"id": f"{doc['poem_id']}:{doc['source_id']}:{i:04d}", "text": text,
                         "metadata": {**doc, "chunk_index": i, "chunk_size": self.chunk_size, "chunk_overlap": self.overlap, "schema_version": 1}}
                        for i, text in enumerate(chunks, 1))
        self._upsert(self.evidence, rows)
        stale = old_ids - {r["id"] for r in rows}
        if stale:
            self.evidence.delete(ids=sorted(stale))

    @staticmethod
    def unpack(result):
        return [{**m, "chunk_id": ident, "text": text} for ident, text, m in zip(result["ids"], result["documents"], result["metadatas"])]

    def retrieve(self, poem_id, question, quote=""):
        meta = self.poems.get(ids=[f"poem:{poem_id}"], include=["documents", "metadatas"])
        if not meta["ids"]:
            return []
        result = self.unpack(meta)
        all_rows = self.evidence.get(where={"poem_id": poem_id}, include=["documents", "metadatas"])
        if not all_rows["ids"]:
            return result
        reserved = []
        if quote:
            needle = "".join(quote.split())
            reserved = [r for r in self.unpack(all_rows) if r.get("document_type") == "poem_text" and needle in "".join(r["text"].split())][:1]
        found = self.evidence.query(query_embeddings=[self.embeddings.embed_query(question)], where={"poem_id": poem_id}, n_results=min(len(all_rows["ids"]), self.top_k + 1), include=["documents", "metadatas"])
        candidates = self.unpack({k: found[k][0] for k in ("ids", "documents", "metadatas")})
        seen, selected = set(), []
        for row in reserved + candidates:
            identity = (row.get("source_id"), row.get("locator"), row["text"])
            if identity not in seen:
                seen.add(identity)
                selected.append(row)
        return result + selected[:self.top_k]

    def search_poems(self, query, limit=30):
        if not self.poems.count():
            return []
        result = self.poems.query(query_embeddings=[self.embeddings.embed_query(query)], n_results=min(limit, self.poems.count()), include=["documents", "metadatas"])
        return self.unpack({k: result[k][0] for k in ("ids", "documents", "metadatas")})
