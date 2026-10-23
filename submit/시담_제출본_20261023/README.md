# 시담 한국 근대시 검색과 근거 기반 해설

시담은 시 100편을 제목·시인·연도·주제로 검색하고, 선택한 작품의 전문을 읽으며 구절·상징·배경을 질문하는 서비스입니다. 답변은 제공된 원문과 검색 근거를 사용하고, 실제 인용한 자료의 제목·원문 링크·열람 범위를 표시합니다. 확인되지 않는 사실과 시인의 의도를 지어내지 않도록 제약합니다.

작성 기준은 `rag_pjt.pdf` 23쪽과 2026-10-23 구현 커밋 `a1a551b`입니다. 아래 실행 명령은 **이 문서 폴더가 아닌 저장소 루트**에서 수행합니다.

## 제출 문서와 저장소

| 파일 | 내용 |
| --- | --- |
| [요구사항 정의서](요구사항%20정의서.docx) | 도메인 선정 근거, F2001~F2016/NF2001~NF2007, 인수 조건·현재 확인·제출 점검 |
| [RAG 파이프라인 설계서](RAG%20파이프라인%20설계서.docx) | 데이터·두 컬렉션·수집·색인·검색·세 프롬프트·그래프·설정 비교·문제 해결 |
| 이 README.md | 개요·실행·전체 기능·자료 준비·이용 조건·검증과 제출 안내 |

소스는 [프로젝트 저장소](https://github.com/tjdgus1377-rgb/korean_poem_rag)에 있습니다. 이 폴더는 문서 세트입니다. 실행 코드와 허용 데이터·설정·잠금 의존성·검증 증거는 저장소 전체를 함께 전달해야 합니다. 기존 `submit/`의 빈 Word 파일 2개는 덮어쓰지 않았습니다.

## 기능과 사용 흐름

1. ‘조건으로 작품 찾기’에서 제목·시인·최초 발표 연도·주제로 검색하거나 서가/왼쪽 목록에서 작품을 선택합니다.
2. ‘작품 읽기 · 질문’에서 전문·출처·연도 종류와 확인된 주제 설명을 읽습니다.
3. 작품의 구절·상징·배경을 질문하거나 실제 구절을 넣어 해설 카드를 만듭니다.
4. 답변의 `[근거 N]`과 펼침 목록에서 실제 인용한 원문 URL·접근 범위를 확인합니다.
5. 작품을 바꾸었다 돌아오면 해당 작품의 대화·당시 출처·검색 방식이 복원됩니다. 서버 재시작 이후 영구 대화 보존 기능은 제공하지 않습니다.

| 구분 | 요구사항 | 제공 내용 |
| --- | --- | --- |
| 필수 | F2001~F2002 | 100편 로드·검색 텍스트·작품 벡터 색인·멱등 갱신 |
| 필수 | F2003~F2005 | 검색어 JSON·후보 선별·기존 자료 우선/결손 수집·근거 청킹과 별도 색인 |
| 필수 | F2006~F2008 | 작품별 근거 검색·병합/중복 제거·두 노드 생성·실제 인용 출처 표시 |
| 필수 | F2009~F2012 | 작품별 채팅·선택 구절 해설 카드·자연어 조건 탐색·진행/오류 안내 |
| 선택 구현 | F2014 | 기본 유사도와 선택형 MMR의 동일 질문 근거 비교 |
| 선택 구현 | F2015 | 대표 12질문·24응답의 원문만/원문과 외부 해설 비교 CLI와 보고서 |
| 미선택 | F2013 | 별도 서버/API와 분리한 JavaScript 프론트엔드. 현재 문예지 디자인은 Streamlit HTML/CSS 개선입니다. |
| 독립 심화 미선택 | F2016 | 여러 자료를 이미 사용하지만 별도 심화의 출처별 비교·검증 완료로 계산하지 않습니다. |

정확 제목·시인, 일부 제목·원문 구절, 확인된 본명·한자 병기와 입력 줄임말을 지원합니다. 지정 시인의 4자 이상 제목에서 1글자 오탈자는 후보 안내로 표시합니다. 모든 별명/오탈자를 자동 인식한다고 보장하지 않습니다.

## Windows에서 설치하고 실행

PRD는 Python 3.10 이상을 제시하며, 이 저장소의 잠금·실검증 기준은 **Python 3.12**입니다. `requirements.txt` 대신 `requirements.lock`을 사용합니다.

```powershell
git clone https://github.com/tjdgus1377-rgb/korean_poem_rag.git
cd korean_poem_rag
python --version
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --require-hashes -r requirements.lock
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe -X utf8 scripts/verify_repro.py
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
notepad .env
```

로컬 `.env`의 `GMS_KEY`에 본인 키를 넣습니다. `WIKI_CONTACT`는 실시간 추가 수집이 필요할 때 본인의 영문 이메일/연락 URL을 설정합니다. 비워도 공개 고정 자료의 색인·검색·답변은 가능하며, 추가 수집은 생략 안내를 표시합니다. 기존 키 파일은 덮어쓰지 않습니다.

```dotenv
GMS_KEY=
WIKI_CONTACT=
SIDAM_BASE_URL=https://gms.ssafy.io/gmsapi/api.openai.com/v1/
SIDAM_CHAT_MODEL=gpt-5.4-nano
SIDAM_EMBEDDING_MODEL=text-embedding-3-small
```

```powershell
.\.venv\Scripts\python.exe -X utf8 scripts/index_sidam.py --baseline
.\.venv\Scripts\python.exe -m streamlit run step7_skeleton.py --server.address 127.0.0.1 --server.port 8501 --server.headless true
```

브라우저에서 [시담](http://127.0.0.1:8501/)을 엽니다. 초기 색인은 앱 실행 전에 완료합니다. 앱 실행 중 별도 CLI 프로세스로 같은 DB를 갱신하지 않습니다. 실행 중 갱신은 ‘검색·자료 설정’의 색인 버튼을 사용합니다.

키 없이 목록·전문과 오프라인 검사는 사용할 수 있습니다. 의미 검색·임베딩·AI 답변에는 유효한 키와 모델 사용 권한이 필요합니다. API 호출 시 작품 텍스트·허용 근거·질문이 GMS 서버로 전송되며 호출 비용이 발생할 수 있습니다. 키·개인 연락처·질문·대화·로컬 DB는 제출하지 않습니다.

Linux 명령은 [교차 환경 재현 안내](../../docs/REPRODUCE.md)를 따릅니다. Windows/Linux CI를 확인했고 macOS 실제 기기 검증은 완료로 표시하지 않습니다.

## 데이터 준비와 초기 색인

| 입력 | 역할 |
| --- | --- |
| `data/poems_metadata.csv` | 활성 작품 ID·제목·시인·원시 연도·출처 |
| `data/poems_text.jsonl` | 작품 전문 100건 |
| `data/commentary_sources.csv`, `poem_commentary_map.csv` | 외부 자료 목록과 작품 연결 |
| `data/evidence_notes.jsonl`, `author_context_notes.jsonl` | 확인한 해설 위치/요약과 시인 맥락 |
| `data/wiki_*`, `data/repro/public_documents.jsonl` | 위키 보조 자료와 공개 고정 본문 6건 |
| `data/curation/field_overrides.json`, `search_aliases.json` | 검증한 연도 종류·이름/제목 검색 표기 |
| `data/curation/source_policy.json` | 색인 가능한 이용 조건·권리 근거 |

- 고정 기준은 **100작품·12시인·343근거 문서·474근거 청크·228제외 기록**입니다. 근거 문서에는 시 전문이 포함됩니다. 문서 수는 작품별 연결 단위이며 전 세계 고유 URL 수를 뜻하지 않습니다.
- 확인된 주제 설명은 31편, 최초 발표 연도는 2편입니다. 미확인 연도를 추정하지 않고 최초 발표 검색에서 제외합니다.
- `verify_repro.py`는 입력 20개와 본문·출처·권리·설정 지문을 확인합니다. 입력 불일치를 숨기기 위해 매니페스트를 자동 갱신하지 않습니다.
- `--baseline`은 가변 수집 캐시를 제외해 초기 기준을 만듭니다. 기준 외 청크가 정리될 수 있으므로 개인 실험 DB를 보존하려면 별도 체크아웃에서 실행합니다.
- 임베딩은 본인 키로 재생성합니다. 초기 입력/설정을 맞출 수 있지만 외부 모델의 응답 문구까지 동일함을 보장하지 않습니다.
- 색인 DB는 `.sidam/chroma`, 수집 캐시는 `.sidam/collection.sqlite3`, 파생 기록은 `data/derived/`에 생성하며 Git에서 제외합니다.
- 이전 `poem_metadata_100.*`와 최신 활성 자료를 자동 혼합하지 않습니다. 평가 정답·생성 답변·검토표·설계/검증 문서는 근거에 재색인하지 않습니다.

기본 설정은 `sidam.toml`에 있습니다.

```toml
[search]
chunk_size = 1000
chunk_overlap = 200
top_k = 5
mmr_fetch_k = 20
mmr_lambda = 0.5
```

`top_k`는 메타데이터 1건 외의 원문/외부 근거 예산입니다. 기본 전체 근거는 최대 6건이고 선택 구절 원문도 5청크 예산에 포함됩니다. MMR은 UI 설정에서 선택하며 기본값은 similarity입니다. 모델·청킹을 바꾸면 SPEC·검증 후 별도 색인 기준을 준비합니다.

## 출처와 이용 조건

아래는 현재 프로젝트 정책 파일에 기록된 확인 범위입니다. 다른 국가·매체·추가 자료의 재이용 허가를 새로 판정하는 문서가 아닙니다.

| 자료 | 실제 사용과 이용 범위 |
| --- | --- |
| [공유마당](https://gongu.copyright.or.kr/) 및 작품별 원문 URL | 항목 출처와 한국어 원작. 원작의 이용 조건을 별도 확인하며 현대어 번역·이미지·녹음·외부 해설 권리를 함께 허용하지 않습니다. |
| [한국민족문화대백과](https://encykorea.aks.ac.kr/Guide/ContentUse) | 확인한 항목/초록·내용의 큐레이션 요약. 항목명·서비스명·원문 URL을 표시하고 미디어·미열람 전문을 제외합니다. |
| [한국어 위키백과](https://ko.wikipedia.org/wiki/위키백과:저작권) | CC BY-SA 4.0. 문서 URL·역사 보기의 기여자 귀속, 동일조건변경허락과 변경 여부를 보존합니다. |
| 문헌 목록의 그 밖의 해설·연구 자료 | 목록/접근 경로와 실제 열람 내용을 구별합니다. 권리 미확인·미열람·access_lead는 근거에 색인하지 않습니다. 일반 PDF 자동 수집기는 제공하지 않습니다. |

공개 고정 위키 본문은 마크업·미디어를 제거한 평문이며 작품 연결 필드는 프로젝트가 부여했습니다. 위키 요약은 `curated_summary`, 확인 본문은 `original_text`, 간접 맥락은 `context_only`로 구별합니다. 세부 저작자 표시·원문/이력 링크·변경 범위는 [공개 자료 안내](../../data/repro/README.md)와 [정책 파일](../../data/curation/source_policy.json)을 함께 보존합니다.

## 검증과 선택 기능 비교

다음 명령은 네트워크·유료 모델 없이 수행합니다.

```powershell
.\.venv\Scripts\python.exe -X utf8 -m pytest -q
.\.venv\Scripts\python.exe -X utf8 scripts/verify_repro.py
.\.venv\Scripts\python.exe -X utf8 scripts/verify_benchmark.py
.\.venv\Scripts\python.exe -X utf8 scripts/check_release.py
```

구현 기준의 오프라인 테스트는 **68개 통과**이고 Windows/Linux CI와 독립 에이전트 리뷰를 거쳤습니다. 실제 브라우저 검증과 문학적 내용 검토는 자동 테스트와 별개입니다.

| 확인 내용 | 증거 |
| --- | --- |
| 제목·시인·연도·주제·전문·답변/출처·근거 부족·작품 전환 | [E2E-007](../../docs/validation/E2E-007.md) |
| 한자·동명·본명·제한 오탈자 | [IDENTITY-009](../../docs/validation/IDENTITY-009.md) |
| 전체/단계별 시간과 정상 계획 캐시 | [PERF-010](../../docs/validation/PERF-010.md) |
| 관련성·다양성과 poem_id 격리 | [MMR-011](../../docs/validation/MMR-011.md) |
| 검색 137건·답변 12쌍의 실제 비교 | [COMPARE-012](../../docs/validation/COMPARE-012.md), [질문별 응답](../../docs/validation/comparison/COMPARE-012-answers.md), [수치/출처 결과](../../docs/validation/comparison/COMPARE-012-results.json) |
| 최신 디자인·모바일·원문 기호·실제 질문과 대화 복원 | [DESIGN-019](../../docs/validation/DESIGN-019.md) |

실제 모델·색인이 필요한 선택 비교 명령입니다. **본인 키·호출 비용이 필요**하며 문서 열람을 위해 다시 실행할 필요는 없습니다.

```powershell
.\.venv\Scripts\python.exe -X utf8 scripts/compare_retrieval.py
.\.venv\Scripts\python.exe -X utf8 scripts/evaluate_sidam.py
.\.venv\Scripts\python.exe -X utf8 scripts/profile_sidam.py --poem-id 9000320 --question "이별의 정한은 어떻게 표현되나요?" --repeat 3
```

MMR은 동일 질문/임베딩에서 source Recall@5 0.850→0.950, MRR 0.575→0.642를 기록했지만 일부 질문에서는 순위가 낮아졌습니다. 기본 검색을 자동으로 변경하지 않았습니다.

F2015는 양쪽에 같은 전문을 제공하고 외부 해설 유무를 비교합니다. 12질문에서 설명 충분성 평균은 1.417→1.667, 인용 정확성은 1.833→1.833이었습니다(만점 2). 작성 에이전트의 비맹검 근거 대조이며 인간/문학 전문가 평가·일반화 성능·통계적 유의성을 뜻하지 않습니다. 원본 실행은 `evaluation/runs/`에 저장되며 Git 제외입니다.

## 남은 확인과 제출 전 점검

- 기능·인용 번호가 동작해도 100편 전체 문학 해석 품질을 통과한 것은 아닙니다. 일부 무관한 맥락 자료와 판본·인용 문구 검토를 [ISSUE #4](https://github.com/tjdgus1377-rgb/korean_poem_rag/issues/4)에서 관리합니다.
- NF2001의 수치 지연 목표는 미확정입니다. 실제 반복 질문 9.66/14.06/15.11초를 기록했으며 모든 후속 질문이 빨라진다고 보장하지 않습니다.
- PRD 4장·6장의 기관 제공 셀프 체크리스트와 **실제 다른 교육생의 상호 점검**은 미확인입니다. 독립 에이전트 리뷰를 교육생/전문가 검토로 옮겨 적지 않습니다.
- 최종 제출에는 이 문서 세트뿐 아니라 소스·데이터 준비/색인 스크립트·허용 자료·검증 보고서/스크린샷·실제 체크리스트를 함께 포함합니다. `.env`, 인증값, 개인 연락처·질문·대화, `.venv`, `.sidam`, 민감 로그는 제외합니다.
- 제출 파일명은 PRD의 `AI 코어프로젝트 2_[주제명]_지역_반_성명.zip` 형식에 본인의 실제 정보를 넣어 작성합니다. 이 작업에서 ZIP 업로드나 사람의 점검 결과를 대신 수행하지 않았습니다.

## 개발 규칙과 오류 안내

ISSUE/SPEC → 작업 브랜치 → SPEC 커밋 → 인수 테스트 Red → 구현 Green → PR/CI → 독립 리뷰·수정 → 최신 검사/리뷰 통과 후 머지 → ISSUE 종료 순서를 따릅니다. [AGENTS.md](../../AGENTS.md)와 [서비스 SPEC](../../docs/SPEC.md)을 기준으로 합니다.

키 없음은 본인 `.env` 설정 후 재시작, 색인 없음은 앱 시작 전 기준 색인, 검색 없음은 연도 종류·확인 범위 점검, WIKI_CONTACT 없음은 기존 근거 사용으로 처리합니다. 내부 예외·프롬프트·키가 든 로그를 공개 이슈에 붙이지 않습니다. 자세한 절차는 [실행 안내](../../docs/RUNBOOK.md)를 확인합니다.
