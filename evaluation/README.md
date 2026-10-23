# 시담 평가 데이터 v1

구현 전 고정한 개발용 공개 벤치마크다. `search_v1.jsonl` 137건, `answers_v1.jsonl` 12건이며 계약은 [BENCH-008](../docs/specs/BENCH-008.md)을 따른다. 모델에 정답/판정 기준을 전달하지 않는다. 모든 사례를 통과한다고 미리 가정하지 않는다.

검색의 골드는 정확 작품·동명 목록·연도 확인값을 기준으로 한다. 주제 범주는 확인된 양성 작품의 회수 여부이며 모든 작품의 관련성을 완전히 판정한 세트가 아니다. 본명 근거는 이상=김해경(`author_context_notes.jsonl` KAE_YI_SANG), 김소월=김정식(`wiki_evidence_notes.jsonl` WIKI_6647_9000320_3)이다. ‘별헤밤’·‘빼들봄’은 예상 입력 줄임말이며 역사적 이칭이 아니다. 한자 병기는 활성 제목의 원문을 따른다. 별도의 확인된 역사적 이칭은 현재 자료에서 미확인으로 남긴다.

답변 평가는 minimum_points(최소 설명), allowed_interpretations(허용 독법), forbidden_claims(단정 금지), gold_source_ids(작품에 연결된 허용 문서), expected_abstention(확인 불가 여부)로 검토한다. 채점 0/1/2·검토자·이유·위치를 기록하며 미검토를 0점/통과로 처리하지 않는다.

검증: `python scripts/verify_benchmark.py`. 고정 데이터 해시와 개수를 출력한다. 개인 질문을 덮어써 공개하지 않는다. 실행 산출물은 Git 제외된 `evaluation/runs/`로 보낸다. 이 폴더·답변 예시·정답·보고서는 근거 색인 입력이 아니다.
