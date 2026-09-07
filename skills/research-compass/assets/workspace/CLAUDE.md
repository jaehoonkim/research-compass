# Research Compass 워크스페이스

공고·RFP 누적, 연구 우선순위, 실험 반영 요청에는 `research-compass` 스킬을 쓴다. 로드되지 않았으면 `/research-compass`를 호출한다. 기본 출력은 한국어.

`compass.json`, `profile/`, `index/`, `sources/`, `research/`, `experiments/`, `roadmap/`, `decisions/`가 지속 상태다. 제안하기 전에 기존 상태를 읽고, 이전 대화 내용을 기록으로 추정하지 않는다. 지침은 플러그인에 있다. 이 폴더에 스킬 사본이나 별도 로드맵을 만들지 않는다.

추가·갱신 요청은 로컬 편집 승인이다. Git 커밋·push·의존성 설치·유료 연산·백그라운드 작업의 승인이 아니다. 검토 요청은 읽기 전용이다.

갱신을 전달하기 전에 스킬 디렉터리의 `scripts/compass.py check --root .`를 실행하고, 바뀐 경로와 미해결 항목을 보여준다.
