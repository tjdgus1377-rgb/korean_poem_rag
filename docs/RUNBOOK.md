# 시담 실행·검증 안내

다른 PC의 동일 기준 설치는 [재현 안내](REPRODUCE.md)를 먼저 따른다. 공개 위키 보조 자료·문서 스냅샷과 잠금 의존성을 포함하며, 개인 키는 별도로 설정한다.

## 설치

Python 3.12 환경을 권장한다. PRD 고정 버전은 `requirements-app.txt`에 있다. 기존 `requirements.txt`의 사용자 편집은 별도로 보존한다.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --require-hashes -r requirements.lock
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe -X utf8 scripts/verify_repro.py
```

기존 Python 환경을 공유해야 하는 경우 `--system-site-packages`를 사용할 수 있으나, 버전 충돌 여부를 확인한다. 설치된 것만으로 인수 테스트가 통과한 것은 아니다.

## 환경변수

`.env.example`을 참고해 프로젝트 `.env`에 GMS_KEY와 WIKI_CONTACT를 설정한다. 키는 커밋·화면·스크린샷에 넣지 않는다. 모델은 기본 gpt-5.4-nano, 임베딩은 text-embedding-3-small이다. 실제 호출 시 작품 텍스트·해설 근거와 질문이 GMS로 전달된다. 이 프로젝트에서는 사용자가 해당 전송을 승인했다.

키 없이도 작품 목록과 원문은 열람할 수 있다. 의미 검색·색인·답변은 키 설정 후 사용할 수 있다. 추가 수집에는 식별 가능한 이메일/연락 URL이 필요하다.

## 데이터·색인 준비

```powershell
.\.venv\Scripts\python.exe -X utf8 scripts/index_sidam.py --baseline
```

데이터는 활성 `poems_metadata.csv`와 별도 전문에서 읽는다. 이전 8필드 자료와 자동 혼합하지 않는다. `data/curation/field_overrides.json`은 검증한 연도 종류와 근거만 보완한다. 근거 미확인 연도를 최초 발표로 추정하지 않는다.

`data/curation/source_policy.json`은 현재 확인한 원작·외부 텍스트의 이용 범위를 담는다. 허용되지 않은 자료를 재이용 가능하다고 자동 판정하지 않는다. 주제 설명도 색인 가능한 해석 요약만 사용한다. 추가 자료의 이용 조건을 확인한 뒤 정책·테스트·SPEC을 먼저 갱신한다.

색인은 `.sidam/chroma`, 수집 캐시는 `.sidam/collection.sqlite3`에 저장한다. 파생 작품·출처·제외 목록은 `data/derived/`에 생성한다. 두 폴더는 Git 제외다. 같은 텍스트·설정은 다시 임베딩하지 않으며, 청킹 변경 시 해당 출처의 남은 옛 청크를 제거한다. 임베딩 모델을 바꾸면 별도 색인 경로가 필요하다.

CLI 초기 색인은 앱을 시작하기 전에 완료한다. 앱 실행 중 같은 저장 경로를 별도 CLI 프로세스에서 변경하지 않는다. 실행 중 갱신은 화면의 준비 버튼으로 수행한다. 별도 프로세스로 색인한 경우 앱을 재시작하여 로컬 벡터 인덱스 상태를 다시 연다.

## 앱 실행

```powershell
.\.venv\Scripts\python.exe -m streamlit run step7_skeleton.py --server.address 127.0.0.1 --server.headless true
```

화면의 ‘검색 색인 준비·갱신’도 같은 준비 작업을 수행한다. 최초 색인은 임베딩 API 호출이 발생한다. 설정은 `sidam.toml`의 청크 크기·중복·Top-k로 조정한다.

1. 왼쪽 목록에서 작품을 고르거나 조건 검색을 사용한다.
2. ‘작품 읽기 · 질문’에서 원문·연도 종류·주제 설명을 확인한다.
3. 질문을 입력하거나 실제 구절을 지정해 해설 카드를 만든다.
4. 답변에 사용된 근거 번호·원문 링크·접근 범위를 확인한다.
5. 다른 작품으로 이동했다 돌아와 대화·출처가 유지되는지 확인한다.

최초 발표 미확인 작품은 발표 연도 조건 결과에서 제외된다. 일반 탐색에서는 열람할 수 있다. 주제 미확인은 주제 검색 결과에서 제외될 수 있다. 원문·작가 맥락만으로 구절의 의도를 확정하지 않는다.

## 테스트

```powershell
.\.venv\Scripts\python.exe -X utf8 -m pytest -q
```

pytest는 작업공간의 `tmp/pytest`를 사용하며 실제 GMS·위키백과를 호출하지 않는다. 실제 GMS/브라우저 결과는 `docs/validation/MVP-002.md`에 별도로 기록한다. CI는 PR·작업 브랜치 push 시 자동 실행한다. 미검증 항목을 자동 테스트 통과로 대체하지 않는다.

## 오류 대응

- GMS_KEY 누락: 키를 환경변수에 설정한 후 앱을 재시작한다.
- 색인 없음: 색인 명령이나 화면의 준비 버튼을 사용한다.
- 모델/임베딩 연결 불가: 사용 권한·모델·네트워크를 확인한다. 비밀값이 든 원본 예외를 공개 이슈에 올리지 않는다.
- 검색 결과 없음: 연도 종류와 주제 확인 범위를 살펴본다.
- WIKI_CONTACT 누락: 기존 자료만 사용하며 추가 수집 생략을 안내한다.
- 위키 수집 장애: 실패 캐시는 성공으로 저장하지 않으며 다음 질문에서 제한된 재시도를 허용한다.

상호 체크리스트는 실제 다른 사람이 점검한 뒤 작성한다. 현재 문헌 검토가 실제 챗봇의 모든 구절 정확성을 보장하지 않는다.
