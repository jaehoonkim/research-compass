# research-compass — 연구 방향 나침반

연구 초보자가 올바른 순서로 연구하도록 단계별로 안내하는 Claude Code 플러그인. 방향 → 읽기 → 재현 → 질문 → 파일럿 → 계획 → 실행 → 정리 → 공개·회고의 9단계를 밟게 하고, 앞 단계 기록이 없으면 다음 단계로 넘어가지 않는다. 기록은 로컬 폴더에 남고, 회고가 다음 연구의 입력이 된다.

## 설치

```bash
claude plugin marketplace add jaehoonkim/research-compass
claude plugin install research-compass@research-compass
```

로컬 클론에서 개발 중이면 `claude plugin marketplace add ./`.

## 워크스페이스 만들기

```bash
C=$(ls -d ~/.claude/plugins/cache/research-compass/research-compass/*/skills/research-compass)/scripts/compass.py
python3 $C init --root ./my-research
```

폴더 구조와 양식이 만들어지고 git 저장소로 초기화된다. 그 폴더를 Claude Code로 열고 `/research-compass 연구를 시작하고 싶어`라고 하면 프로필 면담부터 시작한다.

```text
my-research/
├── CLAUDE.md           # 이 폴더의 규칙
├── compass.json        # 워크스페이스 설정
├── profile.md          # 목표·자원·영역·교훈
├── roadmap.md          # 프로젝트 표와 역량 지도
├── journal/            # 날짜별 연구 일지
├── inbox/              # 새 공고·논문을 두는 곳
├── signals/            # 공고·RFP 원문과 분석
├── library/            # 논문 원문과 읽기 노트
└── projects/P-001-slug/
    ├── project.md      # 단계(stage)와 단계별 기록
    ├── reading.md
    └── experiments/
```

## 사용 예

```text
/research-compass 연구를 시작하고 싶어
/research-compass inbox/paper.pdf를 라이브러리에 추가하고 노트를 써줘
/research-compass 지금 단계에서 다음 할 일 알려줘
/research-compass 읽기 단계 통과 검토해줘
```

## 스킬 수정 후 반영

`.claude-plugin/plugin.json`과 `marketplace.json`의 `version`을 올려 commit·push한 뒤:

```bash
claude plugin marketplace update research-compass
claude plugin update research-compass@research-compass
```

## 테스트

```bash
python3 skills/research-compass/scripts/test_compass.py
claude plugin validate .
```
