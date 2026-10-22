"""실제 색인과 재현 검사가 공유하는 청크 규칙."""
from langchain_text_splitters import RecursiveCharacterTextSplitter


def evidence_rows(docs, chunk_size=1000, overlap=200):
    splitter = RecursiveCharacterTextSplitter(chunk_size=chunk_size, chunk_overlap=overlap, separators=['\n\n', '\n', '. ', ' ', ''])
    rows = []
    for doc in docs:
        if doc.get('rights_status') != 'verified':
            raise ValueError('이용 조건이 확인된 자료만 색인할 수 있습니다.')
        for i, text in enumerate(splitter.split_text(doc.get('text', '')), 1):
            rows.append({'id': f"{doc['poem_id']}:{doc['source_id']}:{i:04d}", 'text': text,
                         'metadata': {**doc, 'chunk_index': i, 'chunk_size': chunk_size, 'chunk_overlap': overlap, 'schema_version': 1}})
    return rows
