# 시담을 다른 환경에서 재현하기

동일 커밋, Python 3.12, `requirements.lock`이 기준이다. 개인 키·연락처는 환경마다 설정한다. 자료 재수집이나 개발자의 DB 복사는 필요하지 않다.

## Windows PowerShell

```powershell
git clone https://github.com/tjdgus1377-rgb/korean_poem_rag.git
cd korean_poem_rag
python --version # 3.12 확인
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --require-hashes -r requirements.lock
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe -X utf8 scripts/verify_repro.py
.\.venv\Scripts\python.exe -X utf8 -m pytest -q
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
notepad .env
```

`.env`의 GMS_KEY에 본인 키를 넣는다. WIKI_CONTACT는 추가 수집을 사용할 때만 본인 영문 이메일/연락 URL을 넣는다. 비워도 저장소 자료의 초기 색인·검색·답변은 가능하다. 공개 API 주소·모델 기본값은 유지한다. 기존 `.env`를 덮어쓰지 않는다.

```powershell
.\.venv\Scripts\python.exe -X utf8 scripts/index_sidam.py --baseline
.\.venv\Scripts\python.exe -m streamlit run step7_skeleton.py --server.address 127.0.0.1 --server.headless true
```

브라우저에서 `http://127.0.0.1:8501`을 연다. 키 없이도 목록·전문은 읽을 수 있다. 의미 검색·임베딩·AI 답변은 유효한 GMS 키와 모델 사용 권한이 필요하다.

## Linux / macOS

```bash
git clone https://github.com/tjdgus1377-rgb/korean_poem_rag.git
cd korean_poem_rag
python3.12 -m venv .venv
.venv/bin/python -m pip install --require-hashes -r requirements.lock
.venv/bin/python -m pip check
.venv/bin/python scripts/verify_repro.py
.venv/bin/python -m pytest -q
test -f .env || cp .env.example .env
# 편집기로 .env에 본인 GMS_KEY를 설정한다.
.venv/bin/python scripts/index_sidam.py --baseline
.venv/bin/python -m streamlit run step7_skeleton.py --server.address 127.0.0.1 --server.headless true
```

CI는 Windows와 Linux를 검사한다. macOS용 의존성 조건도 잠금 파일에 있으나 실제 macOS 기기 검증 완료를 주장하지 않는다. Linux에서 venv가 없으면 배포판의 Python 3.12 venv 지원 패키지를 먼저 설치한다.

## 동일 상태의 기준

- 작품 100편·근거 문서 343건·근거 청크 474건이 초기 기준이다. 최근 공개 수집 문서 6건도 고정 자료로 포함한다.
- gpt-5.4-nano / text-embedding-3-small, 청크 1000자·중복 200자·Top-k 5를 사용한다.
- `verify_repro.py`는 비밀·네트워크·기존 DB 없이 입력 20개 파일의 정규화 SHA-256, 검색 텍스트/청크의 본문·출처·권리 지문과 설정을 검사한다.
- `--baseline`은 개인 실행 캐시의 추가 자료를 제외한다. 입력·모델·청킹이 다르면 시작 전에 실패하고 실제 색인 후 내용·건수를 다시 검사한다. 기존 DB의 기준 외 청크는 정리되므로 별도 실험을 보존하려면 다른 폴더에서 실행한다.
- 초기 임베딩을 API로 재생성하므로 외부 전송·호출 비용이 발생할 수 있다. 원문·허용 근거·질문이 예제 GMS 주소로 전달된다.
- 실시간 추가 수집·자료 변경 이후에는 기준 상태와 달라질 수 있다. LLM 문구·원격 모델 내부·유사도 동점 순서까지 동일한 것은 보장하지 않는다.
- CLI 색인 완료 후 앱을 시작한다. 앱 실행 중 별도 CLI로 같은 DB를 바꾸지 않는다. 화면 갱신 버튼은 성공 수집 캐시를 함께 재사용한다.

## 포함 자료와 제외 자료

활성 작품·전문·해설 노트, 위키 보조 자료, 이용 정책·연도 보정, 공개 문서 스냅샷을 포함한다. 출처·CC BY-SA·변경 범위는 [공개 자료 안내](../data/repro/README.md)에 있다.

`.env`, API 키·개인 연락처, 사용자 검색어·질문·대화, SQLite/Vector DB, 가상환경, HTML 캐시는 업로드하지 않는다. `scripts/check_release.py`는 Git 추적 파일의 금지 경로·현재 개인 설정값·예제 비밀값을 검사하며 값 자체를 출력하지 않는다.

| GitHub에 포함 | 기본 Git 추가에서 제외 |
| --- | --- |
| 앱 코드·검증 스크립트·테스트·문서·제출본 | `.venv/`, `tmp/`, 로그 |
| `requirements.lock`, `sidam.toml`, 값이 빈 `.env.example` | `.env`, `.env.local` 등 `.env.*`, Streamlit secrets, 개인 키 파일 |
| 활성 작품·전문·허용 해설·공개 스냅샷·출처/이용 조건·재현 매니페스트 | `.sidam/`, SQLite/DB 및 부속 파일, `data/cache/`, `data/derived/`, `evaluation/runs/` |

따라서 clone한 사람은 본인 키를 설정하고 위 초기 색인 명령으로 자신의 DB를 만든다. 필수 공개 자료를 다시 크롤링하거나 개발자의 DB·캐시를 복사할 필요는 없다. 무시 규칙은 이미 추적된 파일·과거 커밋을 지우거나 일반 문서 안의 비밀값을 자동 판별하지 않으므로 배포 검사와 변경 검토를 함께 수행한다.

앱 실행은 `requirements.lock`과 `poems_metadata.csv`/`poems_text.jsonl`을 사용한다. 기존 `requirements.txt`, 구 스키마 `poem_metadata_100.*`, 이전 수집기·미완성 제출물은 앱 재현의 입력이 아니다. 이전 README는 `docs/archive/DATA_COLLECTION_README.md`에 역사적 기록으로 보존한다.

## 검토한 자료를 변경할 때

ISSUE·SPEC→테스트→자료/코드 검토 후 `python scripts/verify_repro.py --write`로 새 기준을 명시적으로 기록하고 일반 검사를 다시 실행한다. 실패를 숨기려고 자동 갱신하지 않는다.

의존성도 SPEC·검증 후 갱신한다. 현재 잠금 파일 생성 명령은 `uv pip compile requirements-app.txt requirements-dev.txt --python-version 3.12 --universal --generate-hashes --output-file requirements.lock --no-annotate`다. 설치에는 uv가 필요하지 않다.

주제 31편·최초 발표 연도 2편의 검토 범위와 문학적 해석의 기존 한계는 유지한다. 재현 성공은 문학적 품질 통과가 아니다. 후속 [ISSUE #4](https://github.com/tjdgus1377-rgb/korean_poem_rag/issues/4)에서 추적한다.
