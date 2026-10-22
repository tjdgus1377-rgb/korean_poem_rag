# 공개 재현 자료와 출처

`public_documents.jsonl`은 2026-10-22에 실제 열람한 한국어 위키백과 문서 6건의 API 평문 추출이다. 작품 ID·문서 ID·제목·URL·수집 시점·접근 범위·이용 조건을 보존했다. 개인 검색어·질문·대화·연락처·키는 내보내지 않았다. 가변 SQLite나 생성 답변의 복제본이 아니다.

마크업·미디어를 제외한 평문이며 본문을 별도 개작하지 않았다. 작품·시인 연결 필드는 프로젝트가 부여했다. 모든 행은 `context_only`이고 간접 배경 문서도 포함한다. 개별 구절의 의미나 시인의 의도를 직접 입증한다는 뜻이 아니다.

`../wiki_evidence_notes.jsonl`은 기존에 확인한 문단의 발췌·요약/정리이며 `curated_summary`로 표시한다. 위키 보조 CSV/JSONL 4개는 수집·미수집과 실제 열람 범위를 보존한다. 전문이나 개별 작품 해석으로 확대하지 않는다.

## 라이선스·기여자·변경

위키 텍스트는 [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/deed.ko) 및 [위키백과 저작권 안내](https://ko.wikipedia.org/wiki/위키백과:저작권)에 따른다. 각 행의 source_url 또는 위키 보조 목록 url이 원문·기여자 귀속 경로다. 문서의 ‘역사 보기’에서 기여자와 수정 이력을 확인한다. 고정한 6개 본문의 직접 이력 링크:

- [TV쇼 진품명품](https://ko.wikipedia.org/w/index.php?curid=578348&action=history)
- [이광수](https://ko.wikipedia.org/w/index.php?curid=3330&action=history)
- [안성현](https://ko.wikipedia.org/w/index.php?curid=125585&action=history)
- [별 헤는 밤](https://ko.wikipedia.org/w/index.php?curid=2962512&action=history)
- [내를건너서숲으로도서관](https://ko.wikipedia.org/w/index.php?curid=2378606&action=history)
- [쉽게 씌어진 시](https://ko.wikipedia.org/w/index.php?curid=3326946&action=history)

텍스트를 재배포·변경하면 출처·라이선스·변경 여부를 보존하고 동일조건변경허락을 적용한다. 이미지·녹음·번역 등 별도 매체 권리를 포함하지 않으며, 이 안내로 전체 앱 소스의 라이선스를 새로 정하지 않는다.

## 기준 해시

`manifest.json`의 입력 해시는 UTF-8 BOM 제거·CRLF→LF 정규화 후 SHA-256이다. 작품/청크 ID로 정렬한 본문·출처 지문에서 현재 시각·개인 경로는 제외한다. 실제 색인과 같은 청킹 함수를 사용한다. 기준은 100작품/343문서/474청크다.

스냅샷도 현재 `../curation/source_policy.json`의 도메인·권리를 검사한다. 정책에서 빠진 자료는 자동 허용하지 않는다. 정책 변경은 불일치로 드러나며 검토 후 새 기준을 작성해야 한다.
