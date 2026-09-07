# research-compass — 연구 방향 나침반

채용공고·과제 RFP·논문·실험 결과를 근거로 연구 로드맵을 로컬 파일에 누적 관리하는 Claude Code 플러그인이다. 새 공고가 들어와도 주 연구를 자동으로 바꾸지 않고, 기존 방향을 강화하는지·수정이 필요한지·관찰만 할지를 판단해 근거와 함께 기록한다.

스킬 본체는 `skills/research-compass/`에 있다. Codex의 `.agents/skills/`에도 그대로 쓸 수 있다.

## 설치

```bash
claude plugin marketplace add jaehoonkim/research-compass
claude plugin install research-compass@research-compass
```

설치 후 새 세션에서 `/research-compass`가 보인다. 로컬 클론에서 개발 중이라면 GitHub 경로 대신 `claude plugin marketplace add ./`를 쓴다.

## 워크스페이스 만들기

연구 기록은 플러그인이 아니라 별도 폴더에 쌓인다. 빈 폴더를 하나 만든다.

```bash
python3 ~/.claude/plugins/cache/research-compass/research-compass/*/skills/research-compass/scripts/compass.py init --root ./my-research
cd my-research && python3 setup.py
```

`init`은 폴더 구조와 스킬 사본을 만들고, `setup.py`는 `.claude/skills/`에 심링크를 건다. 그다음 `my-research`를 Claude Code로 연다.

```text
my-research/
├── profile/researcher.md   # 연구 목표·역량·시간·장비 (확인된 것만)
├── inbox/                  # 새 공고·RFP를 여기 넣는다
├── sources/                # 원문·메타데이터·개별 분석
├── index/research-map.md   # 누적 역량과 연구의 연결
├── research/               # 연구 후보 카드 RES-NNN
├── experiments/            # 실험 계획과 실제 결과 EXP-NNN
├── roadmap/current.md      # 현재 우선순위
└── decisions/              # 판단 변경 이력
```

## 사용

```text
/research-compass inbox/새공고.txt를 추가하고 기존 연구 방향에 미치는 영향을 반영해줘.
/research-compass 지금까지 기록으로 다음 실험을 추천해줘. 파일은 수정하지 마.
/research-compass inbox/실험결과.md를 관찰과 해석으로 나눠 기록하고 로드맵에 반영해줘.
```

원문 등록·중복 검사·구조 검증은 `compass.py`가 하고, 내용 해석과 실험 설계는 Claude가 한다. 상태 점검은 워크스페이스에서 다음 명령으로 한다.

```bash
python3 skills/research-compass/scripts/compass.py check --root .
```

## 스킬 수정 후 반영

플러그인 캐시는 버전이 같으면 갱신되지 않는다. `.claude-plugin/plugin.json`과 `.claude-plugin/marketplace.json`의 `version`을 올려 commit·push한 뒤 실행한다.

```bash
claude plugin marketplace update research-compass
claude plugin update research-compass@research-compass
```

## 테스트

```bash
python3 skills/research-compass/scripts/test_compass.py
claude plugin validate .
```

단위 테스트는 보조 스크립트만 검증한다. 스킬 행동 시나리오는 `skills/research-compass/references/evaluation-cases.md`에 있다.
