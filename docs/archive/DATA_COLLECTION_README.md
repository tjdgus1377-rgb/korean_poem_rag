# 한국 시 작품 메타데이터 100편

공유마당의 작품별 서지·만료 표시를 조회하고 위키문헌 원문·시집 목차, 한국민족문화대백과사전의 서지 기록을 대조한 RAG용 초기 데이터입니다.

## 결과와 스키마

`data/poem_metadata_100.json`과 `data/poem_metadata_100.csv`는 같은 100건이며 다음 **8개 필드만** 포함합니다.

| 필드 | 타입 | 의미 |
| --- | --- | --- |
| `poem_id` | string | 유지된 작품은 기존 ID 보존. 추가 작품은 시인·정규화 제목 해시로 생성 |
| `title` | string | 작품 제목 |
| `poet_name` | string | 시인 이름 |
| `written_year` | integer | 출처의 창작 연도. 아래 처리 원칙 참고 |
| `published_year` | integer | 출처의 발표 연도. 시집의 발간 연도와 구분하여 처리 |
| `collection` | string | 수록을 확인한 시집. 반드시 최초 수록 판본을 의미하지 않음 |
| `source_url` | string | 원문 파일·뷰어를 제공하는 공유마당 작품 상세 페이지. 저자 목록 URL 제외 |
| `copyright_status` | string | `public_domain_kr`: 공유마당의 자유이용 만료 표시 확인. 대한민국 기준 원문 표시 가능 |

이용조건은 작품 상세 화면의 `img_license97.png` 표시와 [공유마당 만료저작물 안내](https://gongu.copyright.or.kr/gongu/main/contents.do?menuNo=200091)를 근거로 합니다. 별도 번역·해설·녹음물 등의 권리까지 포함하는 값은 아닙니다.

## 연도와 작품 선별

공유마당의 `창작년도`와 `공표년도`를 조회합니다. 등록일·현재 연도로 빈칸을 채우거나 시집 간행 연도를 일괄적으로 초출 연도로 옮기지 않습니다.

공유마당에도 오류가 있습니다. 윤동주 「서시」·「자화상」 일부 등록본은 사후인 1948년이 창작 연도로 표시됩니다. 윤동주는 원문의 집필 시기, 생전 『문우』 발표와 1948년 유고시집 간행을 대조해 보정했습니다. 「자화상」·「새로운 길」의 생전 발표를 별도로 반영했습니다. 원 연도와 보정 이유·출처는 `data/provenance/field_evidence.json`에 기록합니다.

『님의 침묵』 수록 시는 한국민족문화대백과사전의 시집 집필 기록에 따라 창작 연도를 1925년으로 보정합니다. 이는 개별 시의 작성일이 아닌 시집 집필 연도 기준입니다. 이육사 「황혼」의 발표 연도는 『신조선』의 1935년 발표 기록으로 보정합니다. 김소월 「먼 후일」의 1920년 초출은 국립국어원 『새국어생활』의 『학생계』 1호 발표 기록과도 대조했습니다.

나머지는 공유마당의 명시 연도를 사용하되 사후 창작, 창작·발표 연도 역전, 상세 요약의 더 이른 발표 기록과 충돌하는 자료는 제외합니다. 모든 작품의 초출 문헌을 독립적으로 실물 검증하거나 외부 데이터의 편찬 오류를 모두 해소했다는 뜻은 아닙니다.

연도·시집·원문을 확보하지 못한 작품은 정보가 확인되는 작품으로 교체합니다. 백석은 이번 공유마당 검색에서 본인의 시 원문과 이용조건을 확인하지 못해 제외했습니다. 제목 번호만으로 판본 간 식별이 어려운 정지용의 「바다 1」·「바다 2」도 제외합니다. 대표작과 기존 작품을 우선하고, 나머지는 정보 완전성과 시인별 순환 순서에 따라 보충합니다.

## 검증

- JSON·CSV 각 100건, 모든 행에 동일한 8개 필드
- ID, 시인+정규화 제목, 공유마당 URL, 정규화 시 본문 해시 각각 중복 0건
- 같은 시인의 다른 제목 사이 본문 유사도 0.9 이상인 쌍 검사
- `null`·빈 문자열 없음, 연도 정수 타입 및 시간 순서 확인
- 위키문헌 작품 페이지의 저자·시 본문과 공유마당 작품별 만료 표시 확인

제목은 유니코드·띄어쓰기·문장부호·한자 병기를 정규화합니다. 본문도 정규화해 해시를 비교합니다. 모든 이본·개작 관계를 문헌학적으로 판정했다는 뜻은 아닙니다. 시 본문은 최종 JSON·CSV에 넣지 않습니다.

## 별도 근거 파일

- `data/provenance/final_audit.json`: 최종 수량·중복·결측·시인별 집계
- `data/provenance/field_evidence.json`: 작품별 원 연도, 보정 근거, 시집·원문 URL, 본문 해시, 이용조건 근거
- `data/provenance/selection_exclusions.json`: 후보 제외 사유
- `data/provenance/original_audit.json`: 수정 전 100건 검사. 기존 7건은 작품 URL이 없어 본문 대조 불가
- `data/provenance/original_metadata_100.json`: 수정 전 원본
- `data/provenance/gongu_search_index.json`, `gongu_details.json`, `featured_details.json`: 검색·상세 조회 기록
- `data/provenance/collection_membership.json`: 시집 목차 대조 기록
- `data/poem_candidates.csv`: 초기 위키문헌 후보

화면과 RAG 색인은 8개 필드의 최종 JSON을 사용하면 됩니다. 내부 수집·검증 기록은 최종 스키마와 분리했습니다.

## 재실행

```powershell
python -m pip install -r requirements.txt
python -X utf8 enrich_poem_metadata.py --harvest
python -X utf8 enrich_poem_metadata.py --featured
python -X utf8 enrich_poem_metadata.py --finalize

# 저장된 캐시를 이용한 재생성과 검증
python -X utf8 enrich_poem_metadata.py --finalize --offline
python -X utf8 validate_poem_metadata.py
```

`data/cache/`는 HTML 캐시이며 Git에서 제외됩니다. 오프라인 재생성·본문 검증에는 이 캐시가 필요합니다. 온라인 실행도 캐시를 재사용합니다. 초기 수집기 `collect_poem_metadata.py`는 최종 파일을 덮어쓰지 않고 `data/provenance/wikisource_metadata_raw.*`에 원시 결과를 저장합니다. robots.txt와 요청 간격을 준수합니다.
