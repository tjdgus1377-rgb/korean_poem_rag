"""Check the active research corpus and its cross-file references.

These checks prove record consistency, not interpretive adequacy. Source and
passage quality still require reading the actual poem and external material.
"""

import collections
import csv
import hashlib
import json
from pathlib import Path

from build_interpretation_readiness import role

DATA = Path(__file__).resolve().parents[1] / "data"


def csv_rows(name):
    with (DATA / name).open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def json_rows(name):
    return [json.loads(line) for line in (DATA / name).read_text().splitlines() if line.strip()]


def audit():
    metadata = csv_rows("poems_metadata.csv")
    texts = json_rows("poems_text.jsonl")
    sources = csv_rows("commentary_sources.csv")
    notes = json_rows("evidence_notes.jsonl")
    contexts = json_rows("author_context_notes.jsonl")
    maps = csv_rows("poem_commentary_map.csv")
    readiness = csv_rows("interpretation_readiness.csv")
    reviews = csv_rows("question_coverage_review.csv")
    errors = []

    def require(condition, message):
        if not condition:
            errors.append(message)

    def unique(rows, key, label):
        counts = collections.Counter(row[key] for row in rows)
        require(all(count == 1 for count in counts.values()), f"{label}: duplicate {key}")
        return {row[key]: row for row in rows}

    poems = unique(metadata, "id", "metadata")
    source_by_id = unique(sources, "source_id", "sources")
    unique(notes, "note_id", "notes")
    unique(contexts, "author", "author contexts")
    require(len(metadata) == 100, f"Expected 100 poems, found {len(metadata)}")
    require(len({(row["author"], row["title"]) for row in metadata}) == 100,
            "Duplicate author/title pair")
    for label, rows in [("texts", texts), ("maps", maps), ("readiness", readiness), ("reviews", reviews)]:
        indexed = unique(rows, "id", label)
        require(set(indexed) == set(poems), f"{label}: poem IDs differ from metadata")
        for row in rows:
            if row["id"] not in poems:
                continue
            poem = poems[row["id"]]
            for field in ("title", "author"):
                if field in row:
                    require(row[field] == poem[field], f"{label}: {row['id']} {field} mismatch")

    map_by_id = {row["id"]: row for row in maps}
    by_poem = collections.defaultdict(list)
    for note in notes:
        require(note["poem_id"] in poems, f"Orphan note {note['note_id']}")
        require(note["source_id"] in source_by_id, f"Missing source for {note['note_id']}")
        if note["poem_id"] in poems:
            poem = poems[note["poem_id"]]
            require((note["title"], note["author"]) == (poem["title"], poem["author"]),
                    f"Note identity mismatch {note['note_id']}")
            linked = set(map_by_id.get(note["poem_id"], {}).get("source_ids", "").split(";"))
            require(note["source_id"] in linked, f"Note source absent from map {note['note_id']}")
        if note["source_id"] in source_by_id:
            source = source_by_id[note["source_id"]]
            require(note["source_url"] == source["url"], f"Source URL mismatch {note['note_id']}")
        by_poem[note["poem_id"]].append(note)

    for row in maps + reviews:
        field = "source_ids" if "source_ids" in row else "basis_source_ids"
        for source_id in filter(None, row[field].split(";")):
            require(source_id in source_by_id, f"Unknown linked source {source_id} for {row['id']}")
    for review in reviews:
        mapped = set(map_by_id.get(review["id"], {}).get("source_ids", "").split(";"))
        require(set(review["basis_source_ids"].split(";")) <= mapped,
                f"Review evidence absent from map {review['id']}")
        require(bool(review["sample_user_question"].strip()), f"No reviewed question {review['id']}")

    context_by_author = {row["author"]: row for row in contexts}
    for poem in metadata:
        require(poem["author"] in context_by_author, f"Missing author context {poem['author']}")
        if poem["author"] in context_by_author:
            context = context_by_author[poem["author"]]
            require(context["source_id"] in source_by_id, f"Missing author source {poem['author']}")
            require(context["source_id"] in map_by_id.get(poem["id"], {}).get("source_ids", "").split(";"),
                    f"Author context absent from map {poem['id']}")
        require(any(role(note) == "interpretation" for note in by_poem[poem["id"]]),
                f"No usable work interpretation {poem['id']}")
    for row in readiness:
        actual = collections.Counter(role(note) for note in by_poem[row["id"]])
        for field, category in [("work_specific_note_count", "interpretation"),
                                ("context_note_count", "context_only"),
                                ("access_lead_count", "access_lead")]:
            require(int(row[field]) == actual[category], f"Stale readiness {row['id']} {field}")
    for text in texts:
        require(set(text) == {"id", "text"}, f"Inconsistent full-text schema {text['id']}")
        require(bool(text["text"].strip()), f"Empty poem text {text['id']}")
        require(not any(token in text["text"] for token in (".mw-parser-output", "<script", "<style")),
                f"HTML or CSS in poem text {text['id']}")

    # These are authored, cited examples for a limited research review. Checking
    # their anchors and references does not grade their interpretive correctness.
    examples_path = DATA / "interpretation_examples.jsonl"
    examples = json_rows("interpretation_examples.jsonl") if examples_path.exists() else []
    unique(examples, "example_id", "answer examples")
    text_by_id = {row["id"]: row["text"] for row in texts}
    notes_by_id = {row["note_id"]: row for row in notes}
    examples_by_id = {row["example_id"]: row for row in examples}
    for review in reviews:
        if "answer_example_id" in review:
            example = examples_by_id.get(review["answer_example_id"])
            require(example is not None, f"Review missing example {review['id']}")
            if example:
                require(example["poem_id"] == review["id"], f"Review cross-poem example {review['id']}")
                require(review.get("scope_limit") == example["interpretive_limit"],
                        f"Review has stale example limit {review['id']}")
            require(bool(review.get("reviewed_interpretation_topics")), f"Review topics absent {review['id']}")
    for example in examples:
        pid = example["poem_id"]
        require(pid in poems, f"Orphan example {example['example_id']}")
        if pid not in poems:
            continue
        require((example["title"], example["author"]) == (poems[pid]["title"], poems[pid]["author"]),
                f"Example identity mismatch {example['example_id']}")
        require(example["passage"] in text_by_id.get(pid, ""), f"Example anchor absent {example['example_id']}")
        require(bool(example["evidence_note_ids"]), f"Example has no cited notes {example['example_id']}")
        for note_id in example["evidence_note_ids"]:
            require(note_id in notes_by_id, f"Example missing note {note_id}")
            if note_id in notes_by_id:
                require(notes_by_id[note_id]["poem_id"] == pid, f"Cross-poem example citation {note_id}")
        require(any(role(notes_by_id[nid]) == "interpretation"
                    for nid in example["evidence_note_ids"] if nid in notes_by_id),
                f"Example has no usable interpretation note {example['example_id']}")
        context = context_by_author.get(example["author"], {})
        require(example["author_context_source_id"] == context.get("source_id"),
                f"Example author context mismatch {example['example_id']}")

    source_review_path = DATA / "text_source_review.jsonl"
    if source_review_path.exists():
        source_reviews = json_rows("text_source_review.jsonl")
        indexed = unique(source_reviews, "id", "text source review")
        require(set(indexed) == set(poems), "Text source review IDs differ from metadata")
        for row in source_reviews:
            pid = row["id"]
            if pid in poems:
                require((row["title"], row["author"]) == (poems[pid]["title"], poems[pid]["author"]),
                        f"Text review identity mismatch {pid}")
                require(row["source_url"] == poems[pid]["text_source_url"], f"Stale text review URL {pid}")
                actual_hash = hashlib.sha256(text_by_id[pid].encode("utf-8")).hexdigest()
                require(row["stored_sha256"] == actual_hash, f"Stale text review hash {pid}")

    return {"counts": {"poems": len(metadata), "texts": len(texts), "sources": len(sources),
                        "evidence_notes": len(notes), "author_contexts": len(contexts),
                        "maps": len(maps), "reviews": len(reviews), "authored_answer_examples": len(examples)},
            "note_roles": dict(collections.Counter(role(note) for note in notes)),
            "errors": errors,
            "scope": "Record identity, references and derived counts only; no claim of complete passage coverage."}


if __name__ == "__main__":
    report = audit()
    print(json.dumps(report, ensure_ascii=False, indent=2))
    raise SystemExit(bool(report["errors"]))
