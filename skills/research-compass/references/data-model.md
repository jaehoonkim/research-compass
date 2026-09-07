# 데이터 모델

## 워크스페이스

```
compass.json            # schema_version 2, timezone, min_library
CLAUDE.md
profile.md              # 목표·자원·영역·교훈. 매 세션 읽음
roadmap.md              # 프로젝트 표, 역량 지도
journal/YYYY-MM-DD.md   # 연구 일지
inbox/                  # 새 파일 임시 보관 (git 제외)
signals/SIG-YYYYMMDD-NNN/   original.*, meta.json, analysis.md
library/LIB-YYYYMMDD-NNN/   original.*, meta.json, notes.md
projects/P-NNN-slug/
  project.md            # 머리글 + 단계별 절
  reading.md
  experiments/EXP-NNN.md
```

인덱스 파일은 없다. `check`가 매번 폴더를 훑어 센다. 백업과 이력은 git.

## 머리글

파일 맨 위부터 첫 빈 줄 전까지 `키: 값`. `skip`은 반복 가능.

`project.md`:
```
id: P-001
title: …
stage: reading            # direction reading reproduction question pilot plan active writeup release
status: active            # active paused completed dropped
approval: 미확인          # question·plan 단계 통과에 필요. 승인 시 "승인 YYYY-MM-DD"
created: 2026-09-07
skip: reproduction->question 2026-10-01 재현 대상 코드 비공개
```

`experiments/EXP-NNN.md`:
```
id: EXP-001
kind: reproduction        # reproduction pilot main
status: planned           # planned running completed blocked inconclusive
verdict:                  # pilot 전용: alive dead
```

EXP ID는 프로젝트 안에서만 유일하다. 다른 프로젝트의 실험을 가리킬 때는 `P-002/EXP-001`처럼 쓴다. 실험 카드는 Claude가 `assets/templates/experiment.md`를 복사해 만들고 머리글의 `{{ID}}`, `{{KIND}}`, `{{TITLE}}`을 채운다. 스크립트는 실험 카드를 만들지 않는다.

## meta.json (signals, library 공통)

`id`, `title`, `organization|null`, `source_url|null`, `published_date|null`, `collected_date`, `capture_scope`, `visibility`(public/private/unknown), `original_file`, `original_name`, `sha256`, `related_to|null`, `relation`(revision/repost/related/null), `analysis_status`(pending/partial/analyzed). signals에만 `demand_group`.

- 원문 바이트는 불변. 새 버전은 새 ID로 등록하고 `related_to`로 잇는다.
- signals의 수요 그룹은 처음엔 자기 ID. revision/repost는 관련 기록의 그룹을 물려받는다. 그룹 수는 중복 제거된 관찰 기록 수이지 확인된 기관 수가 아니다.
- 정확 중복은 같은 폴더 안 같은 해시 + 같은 organization. 문구가 바뀐 중복은 Claude가 판단해 `--relation repost`로 잇는다.

## 근거 링크

ID와 위치를 담은 상대 링크. `[SIG-20260907-001 REQ-02, original 12-15행](../../signals/SIG-20260907-001/analysis.md)`. 페이지·줄 번호를 지어내지 않는다. 원문 인용과 해석을 구분한다.

## check가 보는 것

| 대상 | 오류 | 경고 |
| --- | --- | --- |
| signals, library | 해시 불일치, meta 필수 키 누락, 파일명이 폴더 밖, related_to가 없는 ID, 순환 관계, 잘못된 수요 그룹 | analysis_status pending/partial, 중단된 staging 폴더 |
| project.md | 폴더명 형식, 머리글 id 불일치, stage·status 값, skip 줄 형식 | 아래 통과 조건 미충족 (`unmet`) |
| EXP-*.md | 머리글 id 불일치, kind·status 값, 게이트 위반 | skip으로 덮인 게이트 위반 |
| 모든 .md | SIG/LIB/P/EXP ID가 실제로 없음 | |

게이트: `reproduction`은 stage ≥ reading, `pilot`은 ≥ question, `main`은 ≥ plan. 프로젝트 stage가 그보다 앞이면 오류. 그 구간을 덮는 `skip` 줄이 있으면 경고.

`unmet`으로 세는 통과 조건: reading은 `reading.md`의 LIB 링크 수 ≥ `min_library`, reproduction은 reproduction 실험 status completed/blocked, pilot은 pilot 실험 completed + verdict, question·plan은 `approval:` 설정. 나머지 통과 조건은 Claude가 판단한다.

`check` 결과: `status`, `errors`, `warnings`, `counts{signals, library, demand_groups}`, `projects[{id, slug, title, stage, status, unmet}]`, `limits`.
