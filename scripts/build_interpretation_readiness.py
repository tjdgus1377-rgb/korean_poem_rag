"""Summarize the *usable* interpretation coverage of each collected poem.

Bibliographic leads and publication/context notes remain in evidence_notes.jsonl,
but they must not inflate the count of interpretation evidence for a RAG answer.
"""

import collections
import csv
import json
import os
from pathlib import Path


DATA = Path(__file__).resolve().parents[1] / "data"


def read_csv(name):
    with (DATA / name).open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


# These records point to unread commentary. Their titles or tables of contents
# cannot support an answer about the poem's meaning.
ACCESS_LEAD_PREFIXES = (
    "RISS_JEONG_WORKS_",
    "SOWOL_DOJONGHWAN_COMMENTARY_",
    "SOWOL_YOOJONGHO_100_COMMENTARY_",
    "SANGHWA_BUMWOO_COMMENTARY_COLLECTION_",
    "EBS_YUKSA_JAYAGOK_",
)

# These contain relevant publication, textual, reception, or formal context,
# but no claim that directly explains a poem's passage or symbol.
CONTEXT_ONLY_IDS = {
    "KCI_SANGHWA_CENSORSHIP_9001014",
    "KCI_YEONGRANG_TEXT_9000347",
    "DBPIA_JEONG_TEXTBOOK_INTERPRETATION_9029848",
    "MUSEUM_SANGHWA_GRIEF_9030086",
    "GONGU_SANGHWA_GRIEF_9030086",
    "KCI_JEONG_LAKE_9029792",
}
CONTEXT_ONLY_PREFIXES = (
    "KAE_IM_CONCEPT_",
    "KCI_YEONGRANG_SEMANTIC_",
)


def role(note):
    explicit = note.get("evidence_role")
    if explicit:
        if explicit not in {"interpretation", "context_only", "access_lead"}:
            raise ValueError(f"Unknown evidence role: {explicit}")
        return explicit
    note_id = note["note_id"]
    if note_id.startswith(ACCESS_LEAD_PREFIXES):
        return "access_lead"
    if note_id in CONTEXT_ONLY_IDS or note_id.startswith(CONTEXT_ONLY_PREFIXES):
        return "context_only"
    return "interpretation"


def main():
    metadata = read_csv("poems_metadata.csv")
    sources = {row["source_id"]: row for row in read_csv("commentary_sources.csv")}
    notes = [json.loads(line) for line in (DATA / "evidence_notes.jsonl").read_text().splitlines()]
    by_poem = collections.defaultdict(list)
    for note in notes:
        by_poem[note["poem_id"]].append(note)

    rows = []
    for poem in metadata:
        poem_notes = by_poem[poem["id"]]
        usable = [note for note in poem_notes if role(note) == "interpretation"]
        context = [note for note in poem_notes if role(note) == "context_only"]
        leads = [note for note in poem_notes if role(note) == "access_lead"]
        if usable:
            # Prefer a source with the fullest *seen* interpretive claim. Source
            # prestige alone must not make an unread item representative.
            best = max(
                usable,
                key=lambda note: (
                    "공개 본문 확인" in note["access_status"],
                    "백과" in sources[note["source_id"]]["source_type"],
                    len(note["evidence_summary"]),
                ),
            )
            count = len(usable)
            readiness = "근거가 다룬 표현·주제에 한해 답변 가능"
            depth = f"해석 근거 {count}건"
            representative_id = best["note_id"]
            representative_evidence = best["evidence_summary"]
            boundary = "근거에 없는 구절의 뜻이나 시인의 실제 창작 의도는 단정할 수 없음"
            if all("초록" in note["access_status"] for note in usable):
                boundary = "공개 초록에 적힌 해석만 인용 가능; 세부 구절·창작 의도는 단정할 수 없음"
        else:
            count = 0
            readiness = "작품별 해석 근거 보강 필요"
            depth = "해석 근거 0건"
            representative_id = ""
            representative_evidence = ""
            boundary = "현재 자료만으로 작품의 구절·상징 해석 답변 불가"
        rows.append(
            dict(
                id=poem["id"],
                title=poem["title"],
                author=poem["author"],
                basic_readiness=readiness,
                evidence_depth=depth,
                work_specific_note_count=count,
                context_note_count=len(context),
                access_lead_count=len(leads),
                representative_note_id=representative_id,
                representative_evidence=representative_evidence,
                answer_boundary=boundary,
            )
        )

    destination = DATA / "interpretation_readiness.csv"
    temporary = destination.with_suffix(".csv.tmp")
    with temporary.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    os.replace(temporary, destination)
    print(collections.Counter(row["work_specific_note_count"] for row in rows))
    print(f"interpretation={sum(row['work_specific_note_count'] for row in rows)}")
    print(f"context={sum(row['context_note_count'] for row in rows)}")
    print(f"access_lead={sum(row['access_lead_count'] for row in rows)}")


if __name__ == "__main__":
    main()
