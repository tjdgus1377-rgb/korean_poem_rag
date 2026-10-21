"""Compare stored poems with their declared public source pages.

Matching a source transcribes that edition; it does not authenticate an original
manuscript. Differences are reported for human review and never auto-corrected.
"""

import csv
import hashlib
import json
import os
import re
import time
import unicodedata
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from html.parser import HTMLParser
from pathlib import Path
from zoneinfo import ZoneInfo

DATA = Path(__file__).resolve().parents[1] / "data"
CACHE = Path("/tmp/sidam_declared_text_sources")
VOID = {"br", "hr", "img", "input", "meta", "link", "wbr", "source", "area", "col", "embed", "param", "track"}


class PoemSection(HTMLParser):
    def __init__(self):
        super().__init__()
        self.depth = 0
        self.started = False
        self.parts = []
        self.ignored_at = None
        self.finished = False

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if self.started and tag == "h2" and attrs.get("id") in {"현대어", "라이선스", "저작권"}:
            self.finished = True
        if not self.depth and not self.finished and "poem" in attrs.get("class", "").split():
            if self.started:
                self.parts.append("\n")
            self.started = True
            self.depth = 1
            return
        if not self.depth:
            return
        if tag not in VOID:
            self.depth += 1
        if self.ignored_at is None and (tag in {"style", "script"} or "pagenum" in attrs.get("class", "")):
            self.ignored_at = self.depth
        if self.ignored_at is None and tag in {"br", "p"}:
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if self.depth and tag not in VOID:
            if self.ignored_at == self.depth:
                self.ignored_at = None
            self.depth -= 1

    def handle_data(self, data):
        if self.depth and self.ignored_at is None:
            self.parts.append(data)


def digest(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def letters(text):
    return "".join(c for c in unicodedata.normalize("NFC", text) if c.isalnum())


def extract(page, url):
    if "sihanjan.com" in url:
        for raw in re.findall(r'<script[^>]*type="application/ld\+json"[^>]*>(.*?)</script>', page, re.S):
            payload = json.loads(raw)
            for item in payload if isinstance(payload, list) else [payload]:
                if isinstance(item, dict) and item.get("text") and "Poem" in str(item.get("additionalType", "")):
                    return item["text"], item.get("name", ""), item.get("author", {}).get("name", ""), "공개 JSON-LD Poem.text"
    if "wikisource.org" in url:
        parser = PoemSection()
        parser.feed(page)
        text = "".join(parser.parts).replace("\u200b", "").strip()
        return text, "", "", "원문 poem 영역들을 이어 비교; 현대어·라이선스 이후 제외; 영역 밖 날짜·부기는 수동 확인"
    return "", "", "", "본문 경계를 수동으로 확인해야 하는 페이지"


def main():
    with (DATA / "poems_metadata.csv").open(encoding="utf-8-sig", newline="") as handle:
        metadata = list(csv.DictReader(handle))
    texts = {row["id"]: row["text"] for row in map(json.loads, (DATA / "poems_text.jsonl").read_text().splitlines())}
    CACHE.mkdir(exist_ok=True)
    checked = datetime.now(ZoneInfo("Asia/Seoul")).isoformat(timespec="seconds")
    destination = DATA / "text_source_review.jsonl"
    previous = {
        row["id"]: row for row in map(json.loads, destination.read_text().splitlines())
    } if destination.exists() else {}

    def compare(poem):
        pid, url = poem["id"], poem["text_source_url"]
        row = {"id": pid, "title": poem["title"], "author": poem["author"], "source_url": url,
               "checked_at": checked, "stored_sha256": digest(texts[pid]), "source_sha256": "",
               "page_sha256": "", "source_retrieved_at": "", "page_cache_used": False,
               "result": "", "comparison_scope": "", "source_title": "", "source_author": "", "detail": ""}
        try:
            cache = CACHE / (digest(url) + ".html")
            if cache.exists():
                page = cache.read_text()
                row["page_cache_used"] = True
            else:
                time.sleep(0.7)
                request = urllib.request.Request(urllib.parse.quote(url, safe=":/%?&=()"), headers={"User-Agent": "SidamResearch/1.0 public-poetry-source-check"})
                with urllib.request.urlopen(request, timeout=25) as response:
                    page = response.read().decode("utf-8")
                cache.write_text(page)
            row["page_sha256"] = digest(page)
            row["source_retrieved_at"] = datetime.fromtimestamp(
                cache.stat().st_mtime, ZoneInfo("Asia/Seoul")
            ).isoformat(timespec="seconds")
            reference, title, author, scope = extract(page, url)
            row.update(source_title=title, source_author=author, comparison_scope=scope)
            if not reference:
                row["result"] = "manual_extraction_required"
            else:
                row["source_sha256"] = digest(reference)
                if reference == texts[pid]:
                    row["result"] = "exact_match"
                elif letters(reference) == letters(texts[pid]):
                    row["result"] = "spacing_punctuation_only"
                else:
                    row["result"] = "difference_requires_review"
                if author and author != poem["author"]:
                    row["result"] = "identity_mismatch"
                row["detail"] = f"stored={len(texts[pid])}, extracted={len(reference)}; 출처 판본 대조이며 육필·초판의 정확성 인증은 아님"
                (CACHE / (pid + ".txt")).write_text(reference)
        except Exception as error:
            row.update(result="fetch_failed", detail=str(error))
        prior = previous.get(pid, {})
        # A manual decision belongs to this text, URL and fetched content only.
        # A changed poem or source invalidates it instead of silently reusing it.
        if prior.get("manual_review") and all(row.get(key) == prior.get(key) for key in (
            "stored_sha256", "source_url", "source_sha256", "page_sha256"
        )):
            row["automatic_result"] = row["result"]
            row["result"] = prior["result"]
            row["manual_review"] = prior["manual_review"]
        return row

    with ThreadPoolExecutor(max_workers=3) as executor:
        rows = list(executor.map(compare, metadata))
    temporary = destination.with_suffix(".jsonl.tmp")
    temporary.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows))
    os.replace(temporary, destination)
    from collections import Counter
    print(json.dumps(dict(Counter(row["result"] for row in rows)), ensure_ascii=False))
    for row in rows:
        if row["result"] not in {"exact_match", "spacing_punctuation_only"}:
            print(row["id"], row["title"], row["result"], row["detail"])


if __name__ == "__main__":
    main()
