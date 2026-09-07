# Research Compass 워크스페이스 규칙

공고·RFP 누적, 연구 우선순위, 실험 반영 요청에는 `research-compass` 스킬을 쓴다. 로드되지 않았으면 `skills/research-compass/SKILL.md`를 읽는다. 기본 출력은 한국어.

`compass.json`, `profile/`, `index/`, `sources/`, `research/`, `experiments/`, `roadmap/`, `decisions/`가 지속 상태다. 제안하기 전에 기존 상태를 읽고, 다른 도구의 대화 내용을 기록으로 추정하지 않는다. 지침은 `skills/`에만 둔다.

추가·갱신 요청은 로컬 편집 승인이다. Git 커밋·push·의존성 설치·유료 연산·백그라운드 작업의 승인이 아니다. 검토 요청은 읽기 전용이다.

갱신을 전달하기 전에 `python3 skills/research-compass/scripts/compass.py check --root .`를 실행하고, 바뀐 경로와 미해결 항목을 보여준다.
