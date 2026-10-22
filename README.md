# 시담 — 한국 근대시 검색·해설

시 100편을 제목·시인·확인된 연도·주제로 검색하고, 원문과 외부 자료를 근거로 작품 질문·구절 해설 카드를 제공합니다. 답변에는 사용한 출처와 근거의 범위를 표시합니다.

## 다른 환경에서 실행

**[설치부터 기준 색인·앱 실행까지 전체 안내](docs/REPRODUCE.md)**

1. Python 3.12로 가상환경을 만듭니다.
2. `python -m pip install --require-hashes -r requirements.lock`으로 설치합니다.
3. `python scripts/verify_repro.py`로 고정 자료를 확인합니다.
4. `.env.example`을 참고해 본인 GMS_KEY를 로컬 `.env`에 설정합니다.
5. `python scripts/index_sidam.py --baseline`으로 기준 색인을 생성합니다.
6. `python -m streamlit run step7_skeleton.py --server.address 127.0.0.1 --server.headless true`로 앱을 실행합니다.

명령의 python은 생성한 가상환경의 인터프리터를 사용합니다. Windows/Linux 전체 경로 명령은 위 안내에 있습니다. 키 없이 작품 목록·전문과 오프라인 자료 검사는 가능합니다.

## 재현 기준

- 작품 100편 / 근거 343문서 / 474청크
- gpt-5.4-nano, text-embedding-3-small
- 청크 1000자 / 중복 200자 / Top-k 5
- 같은 커밋의 자료·설정·잠금 의존성을 기준으로 초기 상태를 생성합니다.
- 개인 키·연락처·질문·대화·Vector DB·가상환경은 저장소에 포함하지 않습니다.
- 실시간 외부 수집 이후의 상태와 AI 생성 문구까지 동일함을 보장하지 않습니다.

## 문서와 검증

- [서비스 SPEC](docs/SPEC.md), [MVP 계약](docs/specs/MVP-002.md), [재현 계약](docs/specs/REPRO-005.md)
- [작업 규칙](AGENTS.md), [실행 안내](docs/RUNBOOK.md)
- [공개 자료·출처·이용 조건](data/repro/README.md), [기준 매니페스트](data/repro/manifest.json)
- [MVP 검증 기록](docs/validation/MVP-002.md), [재현 검증 기록](docs/validation/REPRO-005.md)
- 테스트: `python -m pytest -q`
- 배포 파일 검사: `python scripts/check_release.py`

주제 설명은 31편, 최초 발표 연도는 2편이 검토된 상태입니다. 미확인 값은 추정하지 않으며, 생성 해설의 문학적 정확성은 별도 검증이 필요합니다. [후속 품질·자료 검증 이슈](https://github.com/tjdgus1377-rgb/korean_poem_rag/issues/4)에서 관리합니다.

이전 메타데이터 수집 README는 [보존 기록](docs/archive/DATA_COLLECTION_README.md)입니다. 현재 앱은 `data/poems_metadata.csv`와 `data/poems_text.jsonl`을 사용하며 이전 8필드 파일과 자동 혼합하지 않습니다.
