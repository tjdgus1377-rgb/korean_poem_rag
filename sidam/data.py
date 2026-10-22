"""활성 자료를 읽고 원시 파일은 보존한다."""
import csv
import json
import re
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

PUBLIC_DOCUMENT_FIELDS = {'poem_id', 'poem_title', 'author', 'source_id', 'source_title', 'source_url', 'text',
                          'source_type', 'document_type', 'evidence_role', 'content_origin', 'access_scope', 'locator',
                          'rights_status', 'usage_terms', 'collected_at', 'rights_evidence_url', 'transformation'}


def normalize(value):
    return re.sub(r"[^\w가-힣]", "", unicodedata.normalize("NFKC", value or "").casefold())


def read_jsonl(path):
    path = Path(path)
    return [json.loads(s) for s in path.read_text(encoding="utf-8-sig").splitlines() if s.strip()] if path.exists() else []


def read_json(path, default=None):
    return json.loads(Path(path).read_text(encoding="utf-8-sig")) if Path(path).exists() else default


def load_corpus(data_dir):
    root = Path(data_dir)
    raw_texts = read_jsonl(root / "poems_text.jsonl")
    texts = {str(t["id"]): t["text"] for t in raw_texts}
    if len(texts) != len(raw_texts):
        raise ValueError("전문 ID 중복이 있습니다.")
    notes = read_jsonl(root / "evidence_notes.jsonl")
    overrides = read_json(root / "curation/field_overrides.json", {})
    policy = read_json(root / "curation/source_policy.json", {})
    poems = {}
    with (root / "poems_metadata.csv").open(encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            pid = str(row["id"])
            if pid in poems:
                raise ValueError("작품 ID 중복이 있습니다.")
            if not texts.get(pid, "").strip():
                raise ValueError("작품 전문이 누락되었습니다.")
            checked = overrides.get(pid, {})
            fields = {}
            for key in ("first_publication_year", "collection_publication_year", "written_year"):
                value = checked.get(key)
                if value is not None:
                    if type(value) is not int or not 1000 <= value <= 2100 or not checked.get("year_evidence_ids"):
                        raise ValueError("연도 값과 근거를 확인하세요.")
                    fields[key] = value
            direct = [n for n in notes if n.get("poem_id") == pid and n.get("evidence_role") == "interpretation" and n.get("evidence_summary") and n.get("access_status") and urlparse(n.get("source_url", "")).hostname in policy.get("allowed_domains", {})]
            summary = "\n".join(dict.fromkeys(n["evidence_summary"] for n in direct))
            poems[pid] = {**row, "poem_id": pid, "text": texts[pid],
                          "reported_year": int(row["publication_year"]) if row.get("publication_year") else None,
                          "reported_year_kind": checked.get("reported_year_kind", "unknown"),
                          "theme_summary": summary, "theme_review_status": "source_linked_summary" if summary else "unconfirmed",
                          "theme_evidence_ids": [n["note_id"] for n in direct],
                          "year_evidence_ids": checked.get("year_evidence_ids", []), **fields}
    return poems


def search_text(poem):
    value = poem.get("first_publication_year")
    lines = [f"제목: {poem['title']}", f"시인: {poem['author']}", f"최초 발표 연도: {str(value) + '년' if value else '미확인'}"]
    if poem.get("collection_publication_year"):
        lines.append(f"시집 간행 연도: {poem['collection_publication_year']}년")
    if poem.get("written_year"):
        lines.append(f"창작 연도: {poem['written_year']}년")
    lines.append("해설 기반 주제 설명: " + (poem.get("theme_summary") or "미확인"))
    return "\n".join(lines)


def load_documents(data_dir, poems):
    root = Path(data_dir)
    policy = read_json(root / "curation/source_policy.json", {})
    now = datetime.now(timezone.utc).isoformat()
    docs, excluded = [], []
    for pid, poem in poems.items():
        terms = policy.get("poem_authors", {}).get(poem["author"])
        if not terms:
            excluded.append({"poem_id": pid, "reason": "시 원작 이용 조건 미확인"})
            continue
        docs.append({"poem_id": pid, "poem_title": poem["title"], "author": poem["author"],
                     "source_id": f"TEXT_{pid}", "source_title": f"{poem['author']} 「{poem['title']}」 전문",
                     "source_url": poem["text_source_url"], "text": poem["text"], "locator": "표시 판본 전문",
                     "source_type": "시 원문", "document_type": "poem_text", "evidence_role": "context_only",
                     "content_origin": "original_text", "access_scope": "프로젝트에 저장된 대조 원문",
                     "rights_status": "verified", "usage_terms": terms["usage_terms"], "rights_evidence_url": terms.get("evidence_url", ""), "ingested_at": now})
    notes = read_jsonl(root / "evidence_notes.jsonl") + read_jsonl(root / "wiki_evidence_notes.jsonl")
    for n in read_jsonl(root / "author_context_notes.jsonl"):
        for pid, p in poems.items():
            if p["author"] == n["author"]:
                notes.append({**n, "poem_id": pid, "note_id": f"{n['source_id']}_{pid}_context", "evidence_summary": n.get("context_summary", ""), "evidence_role": "context_only", "document_type": "author_context"})
    grouped = {}
    for n in notes:
        if n.get("poem_id") not in poems:
            raise ValueError("근거 노트가 없는 작품을 참조합니다.")
        domain = urlparse(n.get("source_url", "")).hostname
        terms = policy.get("allowed_domains", {}).get(domain)
        if n.get("evidence_role") not in {"interpretation", "context_only"} or not terms or not n.get("access_status"):
            excluded.append({"poem_id": n["poem_id"], "note_id": n.get("note_id"), "reason": "미열람 또는 원출처 이용 조건 미확인"})
            continue
        grouped.setdefault((n["poem_id"], n["source_id"]), []).append(n)
    for (pid, sid), group in grouped.items():
        n, poem = group[0], poems[pid]
        terms = policy["allowed_domains"][urlparse(n["source_url"]).hostname]
        docs.append({"poem_id": pid, "poem_title": poem["title"], "author": poem["author"],
                     "source_id": sid, "source_title": n.get("source_title", sid), "source_url": n["source_url"],
                     "text": "\n\n".join(f"{g.get('locator', '')}\n{g['evidence_summary']}" for g in group),
                     "locator": "; ".join(dict.fromkeys(g.get("locator", "") for g in group)),
                     "source_type": "위키백과" if urlparse(n["source_url"]).hostname == "ko.wikipedia.org" else "백과사전",
                     "document_type": n.get("document_type", "commentary"),
                     "evidence_role": "interpretation" if any(g["evidence_role"] == "interpretation" for g in group) else "context_only",
                     "content_origin": "curated_summary", "access_scope": "; ".join(dict.fromkeys(g["access_status"] for g in group)),
                     "usage_terms": terms["usage_terms"], "rights_status": "verified", "rights_evidence_url": terms.get("policy_url", ""),
                     "note_ids": json.dumps([g["note_id"] for g in group], ensure_ascii=False), "ingested_at": now})
    known = {(d['poem_id'], d['source_id']) for d in docs}
    snapshot_keys = set()
    for d in read_jsonl(root / 'repro/public_documents.jsonl'):
        pid = d.get('poem_id')
        if set(d) - PUBLIC_DOCUMENT_FIELDS or not PUBLIC_DOCUMENT_FIELDS.difference({'rights_evidence_url', 'transformation'}) <= set(d):
            raise ValueError('공개 스냅샷의 누락·허용되지 않은 필드를 확인하세요.')
        if pid not in poems or d['author'] != poems[pid]['author'] or d['poem_title'] != poems[pid]['title']:
            raise ValueError('공개 스냅샷의 작품 연결을 확인하세요.')
        url = urlparse(d['source_url'])
        if url.scheme != 'https' or url.username or url.password or not d['text'].strip() or d['document_type'] != 'commentary' or d['evidence_role'] != 'context_only' or d['content_origin'] != 'original_text':
            raise ValueError('공개 스냅샷의 본문·출처·역할을 확인하세요.')
        key = (pid, d['source_id'])
        if key in snapshot_keys:
            raise ValueError('공개 스냅샷 출처가 중복됩니다.')
        snapshot_keys.add(key)
        terms = policy.get('allowed_domains', {}).get(url.hostname)
        if d['rights_status'] != 'verified' or not terms:
            excluded.append({'poem_id': pid, 'source_id': d['source_id'], 'reason': '스냅샷의 현재 이용 정책 미확인'})
            continue
        if key not in known:
            docs.append({**d, 'usage_terms': terms['usage_terms'], 'rights_evidence_url': terms.get('policy_url', ''), 'ingested_at': now})
            known.add(key)
    return docs, excluded


def write_report(path, records):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(x, ensure_ascii=False) for x in records) + "\n", encoding="utf-8")
