"""UI와 파이프라인 사이의 응용 서비스."""
import time

from .collectors import CollectionService, WikiAdapter
from .data import load_corpus, load_documents, normalize, write_report
from .models import Models, ModelError
from .pipeline import build_graph
from .prompts import Prompts
from .search import matches_conditions
from .session import validate_quote
from .store import VectorStore


class UnavailableEmbeddings:
    def __init__(self, model):
        self.model = model
    def embed_documents(self, texts):
        raise ModelError("GMS_KEY가 없습니다. 환경변수를 설정하세요.")
    def embed_query(self, text):
        return self.embed_documents([text])[0]


class Service:
    def __init__(self, config):
        self.config = config
        self.poems = load_corpus(config.data_dir)
        self.docs, self.excluded = load_documents(config.data_dir, self.poems)
        self.models = Models(config) if config.api_key else None
        self.prompts = Prompts(self.models) if self.models else None
        self.store = VectorStore(config.index_path, self.models or UnavailableEmbeddings(config.embedding_model), config.chunk_size, config.chunk_overlap, config.top_k)

    def require_models(self):
        if self.models is None:
            raise ModelError("GMS_KEY가 없습니다. 환경변수를 설정하세요.")

    def index(self, status=lambda text: None):
        self.require_models()
        start = time.monotonic()
        status("작품 100편의 검색 텍스트를 색인합니다.")
        self.store.sync_poems(self.poems)
        status(f"근거 자료 {len(self.docs)}건을 배치 색인합니다.")
        self.store.sync_sources(self.docs)
        root = self.config.data_dir / "derived"
        write_report(root / "poem_search_records.jsonl", list(self.poems.values()))
        write_report(root / "source_manifest.jsonl", [{k: v for k, v in d.items() if k != "text"} for d in self.docs])
        write_report(root / "excluded_sources.jsonl", self.excluded)
        return {**self.store.counts(), "elapsed_seconds": round(time.monotonic() - start, 2), "excluded_sources": len(self.excluded)}

    def search(self, question):
        self.require_models()
        if not self.store.counts()["poems"]:
            raise ValueError("색인이 없습니다. 먼저 검색 색인을 준비하세요.")
        conditions = self.prompts.conditions(question, self.poems)
        ranked = self.store.search_poems(question, limit=len(self.poems))
        candidates = [self.poems[r["poem_id"]] for r in ranked if r["poem_id"] in self.poems and matches_conditions(self.poems[r["poem_id"]], conditions)][:20]
        selected = self.prompts.select_poems(question, candidates) if conditions.get("theme_query") and candidates else [p["poem_id"] for p in candidates[:10]]
        return [self.poems[pid] for pid in selected if matches_conditions(self.poems[pid], conditions)], conditions

    def needs_collection(self, poem_id, question, quote=""):
        direct = [d for d in self.docs if d["poem_id"] == poem_id and d["evidence_role"] == "interpretation"]
        if not direct:
            return True
        focus = quote or question
        # 긴 문장 전체 일치 대신 의미 있는 어절의 일부 대응을 확인한다. 충분성 보증은 아니다.
        terms = [normalize(t) for t in focus.split() if len(normalize(t)) >= 2]
        joined = normalize(" ".join(d["text"] for d in direct))
        return bool(terms) and not any(t in joined for t in terms)

    def ask(self, poem_id, question, mode="chat", quote="", messages=None, status=lambda text: None):
        self.require_models()
        if poem_id not in self.poems:
            raise ValueError("선택한 작품을 확인하세요.")
        if not question.strip() or len(question) > 3000:
            raise ValueError("질문은 1~3000자로 입력하세요.")
        poem = self.poems[poem_id]
        if mode == "card" and not validate_quote(poem["text"], quote):
            raise ValueError("표시된 작품에 있는 구절을 선택하세요.")
        if not self.store.poems.get(ids=[f"poem:{poem_id}"])["ids"]:
            raise ValueError("작품 색인이 없습니다. 먼저 검색 색인을 준비하세요.")
        started, timings, warnings = time.monotonic(), {}, []
        status("기존 자료와 수집 캐시를 확인합니다.")
        if self.needs_collection(poem_id, question, quote):
            if self.config.wiki_contact:
                status("검색어를 추출하고 외부 문서를 선별·수집합니다.")
                before = time.monotonic()
                collector = CollectionService(self.config.root / ".sidam/collection.sqlite3", WikiAdapter(self.config.wiki_contact), self.prompts)
                for doc in collector.collect(poem, question):
                    self.store.sync_source(doc)
                write_report(self.config.data_dir / "derived/collection_manifest.jsonl", collector.manifest())
                warnings.extend(collector.warnings)
                timings["collection_seconds"] = round(time.monotonic() - before, 2)
            else:
                warnings.append("WIKI_CONTACT가 없어 외부 추가 수집을 생략했습니다. 기존 근거만 사용합니다.")
        status("작품 범위 안에서 근거를 검색하고 답변을 생성합니다.")
        before = time.monotonic()
        result = build_graph(self.store, self.prompts).invoke({"poem": poem, "question": question, "mode": mode, "quote": quote, "messages": messages or []})
        timings["rag_seconds"] = round(time.monotonic() - before, 2)
        timings["total_seconds"] = round(time.monotonic() - started, 2)
        return {"answer": result["answer"], "sources": result["evidence"], "citation_error": result["citation_error"], "warnings": warnings, "timings": timings}
