# 데이터 모델

## 진실의 원천

지침은 스킬에, 사용자 기록은 워크스페이스에 둔다. 배포되는 스킬은 개인 자료를 포함하지 않는다. `compass.json`이 워크스페이스를 식별한다. `index/sources.json`은 `sources/*/source.json`에서 파생되므로 손으로 고치지 말고 `reindex`로 다시 만든다. 나머지 Markdown은 사람이 관리하는 기록이지 자동 생성 요약이 아니다.

## 레이아웃

```
compass.json
AGENTS.md / CLAUDE.md
profile/researcher.md
inbox/
sources/SRC-YYYYMMDD-NNN/
  original.ext        # 불변
  source.json
  analysis.md
  extracted.md        # 선택, 원문을 대체하지 않음
index/sources.json    # 파생
index/research-map.md
research/RES-NNN.md
experiments/EXP-NNN.md
roadmap/current.md
decisions/YYYYMMDD-HHMMSS-설명.md
snapshots/            # Git 제외
skills/research-compass/
```

## source.json (schema_version 1)

필수 키: `id`, `kind`(job/rfp/reference/experiment), `title`, `organization`(문자열/null), `source_url`(문자열/null), `published_date`(ISO 날짜/null), `collected_date`(ISO 날짜), `capture_scope`, `visibility`(public/private/unknown), `original_file`, `original_name`, `sha256`, `related_to`(ID/null), `relation`(revision/repost/related/null), `demand_group`(ID/null), `analysis_status`(pending/partial/analyzed).

- job/rfp의 수요 그룹은 처음엔 자기 ID다. revision/repost는 관련 원문의 그룹을 물려받고, related는 별도 그룹이다. reference/experiment는 null.
- 그룹 수는 '중복 제거된 관찰 기록 수'다. 독립적으로 확인된 고용주·발주처 수가 아니다. SHA 일치는 진위·관련성·사용 허가를 뜻하지 않는다.
- 원문 바이트는 불변이다. 추출은 따로 고치고 위치 정보를 유지한다. 새 버전은 새 ID다. 메타데이터 수정에는 decision 로그가 필요하다. 철회·마감된 공고는 `analysis.md`에 적고 과거 근거는 지우지 않는다.

## 근거 링크

안정적인 ID와 요구·페이지·줄 위치를 담은 상대 링크를 쓴다.

`[SRC-20260907-001, REQ-02, original 12-15행](../sources/SRC-20260907-001/analysis.md)`

원문 인용과 해석을 구분한다. 줄 번호는 뷰어로 세고 원문을 수정하지 않는다. PDF는 페이지+제목/표, 웹은 URL+제목+수집일로 가리킨다. 페이지·줄 번호를 지어내지 않는다. 저장소 밖으로 공유할 때는 로컬 파일이 필요한 링크임을 표시한다.

## 연구 카드 RES-NNN.md

락 안에서 기존 파일명을 읽고 다음 번호를 배정한다. 최소 항목: 제목, 상태(candidate/active/paused/completed/rejected), 사용자 승인, 트랙 역할, 근거 링크, 질문, 가설, 선행 조건, 기준선/통제, 지표, 제약, 실험 ID, 새로움 상태, 완료·중단 기준, 산출물, 차단 요인, 검토일. 공고에 더 자주 나온다고 가설이 확인되는 건 아니다. 양식은 `assets/templates/research-card.md`.

## 실험 카드 EXP-NNN.md

연결 연구, 상태, 계획 vs 관찰, 버전·환경, 데이터 분할, 절차, 단위 있는 지표, 반복·불확실성, 원시 결과, 해석, 타당성 위협, 다음 결정. 기본 상태는 planned. 예시로 측정값을 만들지 않는다. 양식은 `assets/templates/experiment-card.md`.

## 프로필과 로드맵

`profile/researcher.md`에는 사용자가 확인한 제약만 둔다: 목표 역할, 연구 선호, 보유 기술, 주당 시간, 장비, 연산 예산, 데이터 접근, 마감, 개인정보. 없으면 '미확인'. 공고에서 사용자 자격을 추론하지 않는다. 이미 확인된 항목과 날짜는 다시 묻지 말고 보존한다.

`roadmap/current.md`는 승인된 활성 트랙과 제안 우선순위를 분리한다. 다음 관찰 가능한 마일스톤을 정하되 마감이나 가용 시간을 지어내지 않는다. decision에는 바뀐 것/유지한 것, 근거, 불확실성, 승인 상태를 적는다.

## check가 보는 것과 못 보는 것

본다: 구조, 원문 해시, 파일이 루트 안에 있는지, 알려진 관계, 파생 인덱스 일치, Markdown 안의 SRC/RES/EXP ID가 실제 존재하는지.

못 본다: 문장의 진실성, PDF 추출 완전성, 연구 새로움, 개인정보 준수, 에이전트가 지침을 따랐는지. 이것은 `evaluation-cases.md`로 따로 본다.
