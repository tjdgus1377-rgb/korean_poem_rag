"""Refresh derived research summaries without changing collected evidence.

Counts describe records. They are not scores for answering arbitrary questions.
"""

import collections
import csv
import hashlib
import json
import os
import re
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from build_interpretation_readiness import main as build_readiness, role

DATA = Path(__file__).resolve().parents[1] / "data"


def read_csv(name):
    with (DATA / name).open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def read_jsonl(name):
    path = DATA / name
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()] if path.exists() else []


def atomic_text(name, content):
    path = DATA / name
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(content, encoding="utf-8")
    os.replace(temporary, path)


def main():
    build_readiness()
    metadata = read_csv("poems_metadata.csv")
    notes = read_jsonl("evidence_notes.jsonl")
    maps = read_csv("poem_commentary_map.csv")
    readiness = {row["id"]: row for row in read_csv("interpretation_readiness.csv")}
    examples = read_jsonl("interpretation_examples.jsonl")
    reviews = read_csv("question_coverage_review.csv")
    example_by_poem = {}
    for example in examples:
        example_by_poem.setdefault(example["poem_id"], example)
    for review in reviews:
        example = example_by_poem.get(review["id"])
        if example and "answer_example_id" in review:
            review["answer_example_id"] = example["example_id"]
            review["scope_limit"] = example["interpretive_limit"]
    destination = DATA / "question_coverage_review.csv"
    temporary = destination.with_name(destination.name + ".tmp")
    with temporary.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(reviews[0]))
        writer.writeheader()
        writer.writerows(reviews)
    os.replace(temporary, destination)
    by_poem = collections.defaultdict(list)
    for note in notes:
        by_poem[note["poem_id"]].append(note)
    for row in maps:
        current = readiness[row["id"]]
        counts = collections.Counter(role(note) for note in by_poem[row["id"]])
        row["coverage_level"] = "작품별 해석 근거 노트 연결" if counts["interpretation"] else "해석 근거 보강 필요"
        row["evidence_note"] = (
            f"작품별 해석 노트 {counts['interpretation']}건; "
            f"맥락 {counts['context_only']}건; 접근 경로 {counts['access_lead']}건; "
            f"대표 근거: {current['representative_evidence']} "
            f"답변 경계: {current['answer_boundary']}"
        )
    destination = DATA / "poem_commentary_map.csv"
    temporary = destination.with_name(destination.name + ".tmp")
    with temporary.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(maps[0]))
        writer.writeheader()
        writer.writerows(maps)
    os.replace(temporary, destination)

    covered = {row["poem_id"] for row in examples}
    source_reviews = read_jsonl("text_source_review.jsonl")
    text_results = collections.Counter(row["result"] for row in source_reviews)
    status = {
        "updated_at": datetime.now(ZoneInfo("Asia/Seoul")).isoformat(timespec="seconds"),
        "counts": {
            "poems": len(metadata), "full_text_records": len(read_jsonl("poems_text.jsonl")),
            "sources": len(read_csv("commentary_sources.csv")), "evidence_notes": len(notes),
            "author_contexts": len(read_jsonl("author_context_notes.jsonl")),
            "representative_question_reviews": len(read_csv("question_coverage_review.csv")),
            "authored_answer_examples": len(examples), "poems_with_answer_examples": len(covered),
            "poems_with_topic_review": sum(bool(row.get("reviewed_interpretation_topics")) for row in reviews),
        },
        "text_source_review_results": dict(text_results),
        "text_source_review_pending_ids": [row["id"] for row in source_reviews if row["result"] in {
            "fetch_failed", "difference_requires_review", "manual_extraction_required", "identity_mismatch"
        }],
        "note_roles": dict(collections.Counter(role(note) for note in notes)),
        "interpretation_note_distribution": dict(collections.Counter(int(row["work_specific_note_count"]) for row in readiness.values())),
        "single_interpretation_works": [
            {key: row[key] for key in ("id", "title", "author", "representative_note_id")}
            for row in readiness.values() if int(row["work_specific_note_count"]) <= 1
        ],
        "poem_ids_without_answer_example": [row["id"] for row in metadata if row["id"] not in covered],
        "completion": "미완료: 100편 전체의 구절 해석 충분성이 입증된 것은 아님",
        "remaining_requirements": [
            *(["답변 예시가 없는 작품도 원문·작품 해설·시인 맥락을 연결한 실제 설명으로 검토"]
              if len(covered) < len(metadata) else []),
            "단일 해석 자료 또는 짧은 편집 해설에 기대는 작품의 범위를 재검토·보강",
            "근거가 끝내 부족한 작품은 같은 시기 작품으로 교체하고 전체 연결 갱신",
            "대표 질문 외 주요 시어·상징·연 전개의 공백과 판본 차이 검토",
            "표시한 전문 출처의 자동 대조 차이·접근 실패·수동 경계 확인 완료",
        ],
        "limits": [
            "자료·노트 수는 사용자 질문 대응률 또는 진행률이 아님",
            "작성한 답변 예시는 새로운 외부 근거가 아님",
            "참조 무결성 검사는 해석의 충분성이나 실제 RAG 응답 품질을 증명하지 않음",
        ],
    }
    assessment_path = DATA / "curation_assessment.json"
    if assessment_path.exists():
        assessment = json.loads(assessment_path.read_text())
        fingerprints = assessment.get("source_files_sha256", {})
        current = bool(fingerprints) and all(
            (DATA / name).exists()
            and hashlib.sha256((DATA / name).read_bytes()).hexdigest() == expected
            for name, expected in fingerprints.items()
        )
        status["curation_assessment"] = {
            "current": current,
            "judgement": assessment["judgement"] if current else "자료가 변경되어 문헌 검토 판정 갱신 필요",
            "scope": assessment["scope"],
            "report": "interpretation_assessment.md",
        }
        if current:
            # This is a recorded qualitative literature review, not a score
            # calculated from source counts or the existence of one example.
            status["completion"] = "자료 수집·정합성·주요 구절 문헌 검토 완료; 실제 RAG 실행 평가는 미실시"
            status["remaining_requirements"] = []
            status["follow_up_work"] = assessment["follow_up_work"]
    atomic_text("research_status.json", json.dumps(status, ensure_ascii=False, indent=2) + "\n")
    readme_path = DATA / "commentary_sources_README.md"
    if readme_path.exists():
        readme = readme_path.read_text()
        counts = status["counts"]
        roles = status["note_roles"]
        stats = (
            "<!-- CORPUS_STATS_START -->\n"
            f"2026-10-22 기준, {counts['poems']}편에 자료 레코드 {counts['sources']}건, "
            f"작품별 근거 노트 {counts['evidence_notes']}건, 시인별 맥락 노트 {counts['author_contexts']}건을 연결했다. "
            f"작품별 노트 중 해석 자료는 {roles.get('interpretation', 0)}건, "
            f"맥락 자료는 {roles.get('context_only', 0)}건, 읽지 않은 해설로 가는 접근 경로는 "
            f"{roles.get('access_lead', 0)}건이다. 전문 레코드는 100편 모두에 있으며, "
            "모든 작품에 최소 1건의 해석 노트가 있다. 이는 모든 구절의 해석 충분성이 입증되었다는 뜻이 아니다.\n"
            "<!-- CORPUS_STATS_END -->"
        )
        if "<!-- CORPUS_STATS_START -->" in readme:
            readme = re.sub(r"<!-- CORPUS_STATS_START -->.*?<!-- CORPUS_STATS_END -->", stats, readme, flags=re.S)
        else:
            readme = re.sub(r"2026-10-22 기준,.*?(?=\n\n)", stats, readme, count=1, flags=re.S)
        distribution = ", ".join(
            f"{count}건 {number}편" for count, number in sorted(
                status["interpretation_note_distribution"].items(), reverse=True
            )
        )
        readme = re.sub(r"해석 노트가 .*?이다\.", f"해석 노트 분포는 {distribution}이다.", readme, count=1)
        # Subsequent refreshes replace the generated distribution too.
        readme = re.sub(r"해석 노트 분포는 .*?이다\.", f"해석 노트 분포는 {distribution}이다.", readme, count=1)
        atomic_text("commentary_sources_README.md", readme)
    print(json.dumps(status["counts"], ensure_ascii=False))


if __name__ == "__main__":
    main()
