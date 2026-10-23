"""비밀·네트워크·기존 DB 없이 배포 입력과 기준 색인을 대조한다."""
import hashlib
import json
import tomllib
from pathlib import Path

from .chunking import evidence_rows
from .config import Config
from .data import load_corpus, load_documents, read_json, search_text

INPUT_FILES = (
    'data/poems_metadata.csv', 'data/poems_text.jsonl', 'data/commentary_sources.csv',
    'data/poem_commentary_map.csv', 'data/evidence_notes.jsonl', 'data/author_context_notes.jsonl',
    'data/wiki_evidence_notes.jsonl', 'data/wiki_commentary_sources.csv',
    'data/wiki_collection_status.csv', 'data/wiki_uncollected_works.csv',
    'data/curation/field_overrides.json', 'data/curation/source_policy.json', 'data/curation/search_aliases.json',
    'data/repro/public_documents.jsonl', 'sidam.toml', '.python-version',
    '.env.example', 'requirements-app.txt', 'requirements-dev.txt', 'requirements.lock',
)
SOURCE_FIELDS = ('poem_id', 'source_id', 'source_title', 'source_url', 'author', 'poem_title',
                 'document_type', 'evidence_role', 'content_origin', 'access_scope', 'locator',
                 'usage_terms', 'rights_status', 'rights_evidence_url', 'source_type')


def fingerprint(rows, metadata=True):
    records = []
    for r in sorted(rows, key=lambda v: v['id']):
        item = {'id': r['id'], 'text': r['text']}
        if metadata:
            item['source'] = {k: r['metadata'].get(k) for k in SOURCE_FIELDS}
        records.append(item)
    raw = json.dumps(records, ensure_ascii=False, sort_keys=True, separators=(',', ':'))
    return hashlib.sha256(raw.encode('utf-8')).hexdigest()


def build_manifest(root, input_files=INPUT_FILES):
    root = Path(root)
    inputs = {}
    for name in input_files:
        path = root / name
        if not path.is_file():
            raise ValueError(f'재현 입력 누락: {name}')
        content = path.read_text(encoding='utf-8-sig').replace('\r\n', '\n')
        inputs[name] = hashlib.sha256(content.encode('utf-8')).hexdigest()
    options = tomllib.loads((root / 'sidam.toml').read_text(encoding='utf-8-sig')) if (root / 'sidam.toml').exists() else {}
    search = options.get('search', {})
    settings = {'base_url': Config.base_url, 'chat_model': Config.chat_model, 'embedding_model': Config.embedding_model,
                'chunk_size': search.get('chunk_size', 1000), 'chunk_overlap': search.get('chunk_overlap', 200),
                'top_k': search.get('top_k', 5), 'mmr_fetch_k': search.get('mmr_fetch_k',20), 'mmr_lambda': search.get('mmr_lambda',.5)}
    poems = load_corpus(root / 'data')
    docs, excluded = load_documents(root / 'data', poems)
    rows = evidence_rows(docs, settings['chunk_size'], settings['chunk_overlap'])
    return {'schema_version': 1, 'inputs': inputs, 'settings': settings,
            'counts': {'poems': len(poems), 'documents': len(docs), 'poem_evidence': len(rows), 'excluded_sources': len(excluded)},
            'poems_fingerprint': fingerprint([{'id': f'poem:{pid}', 'text': search_text(p)} for pid, p in poems.items()], False),
            'evidence_fingerprint': fingerprint(rows)}


def verify_manifest(root, required_inputs=INPUT_FILES):
    root = Path(root)
    expected = read_json(root / 'data/repro/manifest.json')
    if not expected or expected.get('schema_version') != 1 or not isinstance(expected.get('inputs'), dict):
        raise ValueError('재현 매니페스트가 없거나 형식이 잘못되었습니다.')
    if set(expected['inputs']) != set(required_inputs):
        raise ValueError('재현 매니페스트의 필수 입력 목록이 다릅니다.')
    # 매니페스트가 지정한 경로도 저장소 밖을 가리키지 못한다.
    for name in expected['inputs']:
        if Path(name).is_absolute() or '..' in Path(name).parts or not (root / name).resolve().is_relative_to(root.resolve()):
            raise ValueError('재현 입력 경로를 확인하세요.')
    actual = build_manifest(root, input_files=tuple(expected['inputs']))
    if actual != expected:
        raise ValueError('재현 기준과 입력·설정·청크가 다릅니다. 파일 변경·누락을 확인하세요.')
    return actual


def verify_settings(config, manifest):
    if any(getattr(config, k) != v for k, v in manifest['settings'].items()):
        raise ValueError('재현 기준과 모델·청킹 설정이 다릅니다.')


def verify_index(store, manifest):
    p = store.poems.get(include=['documents'])
    e = store.evidence.get(include=['documents', 'metadatas'])
    poem_hash = fingerprint([{'id': i, 'text': t} for i, t in zip(p['ids'], p['documents'])], False)
    evidence_hash = fingerprint([{'id': i, 'text': t, 'metadata': m} for i, t, m in zip(e['ids'], e['documents'], e['metadatas'])])
    if store.counts() != {k: manifest['counts'][k] for k in ('poems', 'poem_evidence')} or poem_hash != manifest['poems_fingerprint'] or evidence_hash != manifest['evidence_fingerprint']:
        raise ValueError('실제 색인의 본문·출처·건수가 재현 기준과 다릅니다.')
