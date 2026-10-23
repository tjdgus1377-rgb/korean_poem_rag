"""실패와 정상 빈 결과를 구분하는 수집 캐시 및 고정 호스트 어댑터."""
import hashlib
import html
import json
import re
import sqlite3
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

from .data import normalize
from .models import ModelError
from .identity import same_title, title_forms


def core_title(title):
    outside = re.sub(r"[（(][^）)]*[）)]", "", title).strip()
    return normalize(outside or title)


def own_work(candidate, poem):
    return bool(poem.get("title") and same_title(candidate.get("title", ""), poem["title"]) and normalize(poem.get("author", "")) in normalize(candidate.get("snippet", "")))


class CollectionService:
    def __init__(self, cache_path, adapter, prompts):
        self.path, self.adapter, self.prompts = str(cache_path), adapter, prompts
        self.warnings = []
        self.timings = {}
        Path(cache_path).parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.path) as db:
            db.execute("CREATE TABLE IF NOT EXISTS queries (key TEXT PRIMARY KEY, status TEXT NOT NULL, docs TEXT NOT NULL)")
            db.execute("CREATE TABLE IF NOT EXISTS audits (key TEXT PRIMARY KEY, payload TEXT NOT NULL)")

    def manifest(self):
        with sqlite3.connect(self.path) as db:
            return [json.loads(row[0]) for row in db.execute("SELECT payload FROM audits ORDER BY key")]

    def cached_documents(self):
        documents = {}
        with sqlite3.connect(self.path) as db:
            for row in db.execute("SELECT docs FROM queries WHERE status='success'"):
                for doc in json.loads(row[0]):
                    documents[(doc['poem_id'], doc['source_id'])] = doc
        return list(documents.values())

    def collect(self, poem, question):
        self.warnings = []
        self.timings = {k: 0.0 for k in ('p1_seconds', 'search_seconds', 'p2_seconds', 'fetch_seconds')}
        def timed(key, operation, *args):
            start = time.monotonic()
            try:
                return operation(*args)
            finally:
                self.timings[key] += time.monotonic() - start
        documents = {}
        try:
            queries = timed('p1_seconds', self.prompts.queries, poem, question)
        except ModelError:
            self.warnings.append("외부 검색어 생성에 실패했습니다. 확보한 근거 범위에서 답변합니다.")
            return []
        for query in queries:
            candidates, selected = [], set()
            key = hashlib.sha256(json.dumps(["wiki-v1", poem["poem_id"], normalize(query)], ensure_ascii=False).encode()).hexdigest()
            with sqlite3.connect(self.path) as db:
                cached = db.execute("SELECT status, docs FROM queries WHERE key=?", (key,)).fetchone()
            if cached and cached[0] in {"success", "empty"}:
                for d in json.loads(cached[1]):
                    documents[d["source_id"]] = d
                continue
            try:
                candidates = timed('search_seconds', self.adapter.search, query)
                for c in candidates:
                    c["is_work"] = own_work(c, poem)
                try:
                    selected = timed('p2_seconds', self.prompts.select_documents, poem, question, candidates) if candidates else []
                except ModelError:
                    selected = [c['candidate_id'] for c in candidates if c['is_work']]
                    self.warnings.append('후보 선별 모델에 연결하지 못해 확인된 작품 문서만 수집합니다.')
                # 모델이 제외하더라도 확인된 작품 문서는 유지한다.
                selected = set(selected) | {c["candidate_id"] for c in candidates if c["is_work"]}
                docs = []
                for c in candidates:
                    if c["candidate_id"] in selected:
                        doc = timed('fetch_seconds', self.adapter.fetch, c, poem)
                        if doc:
                            doc["search_query"] = query
                            docs.append(doc)
                status = "success" if docs else "empty"
            except (requests.RequestException, TimeoutError, ValueError, KeyError, ModelError):
                status, docs = "failed", []
                self.warnings.append("일부 외부 자료를 가져오지 못했습니다. 확보한 근거 범위에서 답변합니다.")
            with sqlite3.connect(self.path) as db:
                db.execute("INSERT OR REPLACE INTO queries VALUES (?,?,?)", (key, status, json.dumps(docs, ensure_ascii=False)))
                audit = {"poem_id": poem["poem_id"], "search_query": query, "status": status, "selected_ids": sorted(selected), "rejected_ids": sorted(c["candidate_id"] for c in candidates if c["candidate_id"] not in selected), "collected_at": datetime.now(timezone.utc).isoformat()}
                db.execute("INSERT OR REPLACE INTO audits VALUES (?,?)", (key, json.dumps(audit, ensure_ascii=False)))
            for d in docs:
                documents[d["source_id"]] = d
        return list(documents.values())


class WikiAdapter:
    API = "https://ko.wikipedia.org/w/api.php"

    def __init__(self, contact, session=None, sleep=time.sleep, interval=0.5, attempts=3):
        if not contact or not ("@" in contact or contact.startswith("https://")) or "\n" in contact or "\r" in contact:
            raise ValueError("외부 수집에 사용할 연락처 WIKI_CONTACT를 설정하세요.")
        try:
            contact.encode("ascii")
        except UnicodeEncodeError as e:
            raise ValueError("연락처에는 영문 이메일 또는 URL을 사용하세요.") from e
        self.session = session or requests.Session()
        self.session.headers.update({"User-Agent": f"Sidam/0.1 ({contact}) python-requests"})
        self.sleep, self.interval, self.attempts, self.last = sleep, interval, attempts, 0.0

    def request(self, params):
        for attempt in range(self.attempts):
            self.sleep(max(0, self.interval - (time.monotonic() - self.last)))
            self.last = time.monotonic()
            response = self.session.get(self.API, params={"format": "json", "formatversion": 2, **params}, timeout=30)
            if response.status_code in {429, 503}:
                try:
                    delay = max(0, float(response.headers.get("Retry-After", 2 ** attempt)))
                except ValueError:
                    delay = 2 ** attempt
                if attempt + 1 >= self.attempts or delay > 30:
                    raise requests.RequestException("외부 호출 대기 한도 초과")
                self.sleep(delay)
                continue
            response.raise_for_status()
            data = response.json()
            if "error" in data:
                raise requests.RequestException("외부 API 응답 오류")
            return data
        raise requests.RequestException("외부 호출 실패")

    def search(self, query):
        data = self.request({"action": "query", "list": "search", "srsearch": query, "srlimit": 5})
        return [{"candidate_id": str(r["pageid"]), "title": r["title"], "snippet": html.unescape(re.sub(r"<[^>]+>", "", r.get("snippet", ""))), "url": "https://ko.wikipedia.org/?curid=" + str(r["pageid"])} for r in data.get("query", {}).get("search", [])]

    def fetch(self, candidate, poem):
        pid = candidate["candidate_id"]
        if not str(pid).isdigit():
            raise ValueError("위키 문서 ID를 확인하세요.")
        data = self.request({"action": "query", "pageids": pid, "prop": "extracts|info", "explaintext": 1, "inprop": "url"})
        page = data.get("query", {}).get("pages", [{}])[0]
        text = page.get("extract", "").strip()
        if page.get("missing") or not text:
            return None
        # 강제 보존 후보가 실제로 다른 저자의 동명 문서라면 색인하지 않는다.
        matches_title = same_title(page.get("title", ""), poem["title"])
        definition_text = re.sub(r'[（(][^）)]*[）)]', '', re.split(r'[.!?。\n]', text, maxsplit=1)[0])
        definition_raw = normalize(definition_text)
        page_titles = '|'.join(re.escape(t) for t in title_forms(page.get('title', '')))
        annotations = {normalize(t) for t in re.findall(r'[（(]([^）)]*)[）)]', poem['title'])}
        defines_page = page_titles and re.search(rf'^(?:{page_titles})(?:은|는)', definition_raw)
        work_type = re.search(r'(?:^|\s)(?:시|작품)(?:이다|다|로|이며|이고|였다|이자|으로|입니다)', definition_text)
        if not matches_title and (normalize(page.get('title','')) in annotations or (defines_page and work_type)):
            return None
        if candidate.get('is_work') or matches_title:
            definition = re.split(r'[.!?。\n]', text, maxsplit=1)[0]
            definition = normalize(re.sub(r'[（(][^）)]*[）)]', '', definition))
            titles = '|'.join(re.escape(t) for t in title_forms(poem['title']))
            relation = rf"^(?:{titles})(?:은|는)(?:\d{{4}}년(?:\d{{1,2}}월)?(?:에)?)?(?:대한민국의|한국의)?(?:시인)?{re.escape(normalize(poem['author']))}(?:의|이|가)"
            if not matches_title or not re.search(relation, definition):
                return None
        now = datetime.now(timezone.utc).isoformat()
        return {"poem_id": poem["poem_id"], "poem_title": poem["title"], "author": poem["author"],
                "source_id": f"WIKI_{page['pageid']}", "source_title": page["title"], "source_url": f"https://ko.wikipedia.org/?curid={page['pageid']}",
                "text": text, "source_type": "위키백과", "document_type": "commentary", "evidence_role": "context_only",
                "content_origin": "original_text", "access_scope": "API 본문 확인", "locator": "문서 본문",
                "rights_status": "verified", "usage_terms": "CC BY-SA 4.0; 문서 URL·편집 이력으로 기여자 귀속, 동일조건변경허락",
                "collected_at": now, "ingested_at": now}
