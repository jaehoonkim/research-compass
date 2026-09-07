# Research Compass — 연구 방향 나침반

채용공고·과제 RFP·연구자료·실험 결과를 근거로 연구 로드맵을 누적 관리하는 로컬 워크스페이스다. Claude Code와 Codex는 같은 파일을 읽으며, 대화 기록 대신 이 폴더가 지속되는 기록이 된다.

## 시작

macOS/Linux와 Python 3.9 이상을 기준으로 작성했다. 보조 스크립트에는 외부 Python 패키지나 API 키가 필요하지 않다. Claude Code 또는 Codex 자체는 별도로 사용할 수 있어야 한다.

압축을 풀고 이 폴더에서 실행한다.

```bash
python3 setup.py
python3 skills/research-compass/scripts/compass.py check --root .
```

설치는 이 저장소의 `.claude/skills/research-compass`와 `.agents/skills/research-compass`를 공통 `skills/research-compass` 폴더에 연결한다. 홈 디렉터리의 전역 설정은 변경하지 않는다. 기존의 다른 설치 파일이 있으면 덮어쓰지 않고 중단한다. 같은 설치를 재실행해도 같은 연결은 유지한다.

그다음 이 폴더를 Claude Code 또는 로컬 Codex 프로젝트로 연다. 스킬이 보이지 않으면 경로와 도구 정책을 확인하고 세션을 다시 연다.

## 요청 예시

Claude Code:

```text
/research-compass inbox/새공고.txt를 추가하고 기존 연구 방향에 미치는 영향을 반영해줘.
```

Codex:

```text
$research-compass inbox/새과제.pdf를 분석하고, 기존 연구를 유지할지 수정할지 정리해줘.
```

검토만 요청하기:

```text
$research-compass 지금까지의 기록을 읽고 다음 실험을 추천해줘. 파일은 수정하지 마.
```

결과 반영하기:

```text
/research-compass inbox/실험결과.md를 실제 관찰과 해석으로 나누어 기록하고 로드맵에 반영해줘.
```

호출 뒤의 문장은 자연어 요청이다. 별도 명령 파서나 예약 실행 작업이 아니다. 자료가 없으면 본문을 대화에 붙여 넣어도 된다. URL은 사용 중인 도구가 실제로 읽을 수 있는 범위만 처리하며, 접근 실패를 읽은 것처럼 분석하지 않는다.

## 무엇이 어디에 남는가

`profile/researcher.md`는 확인된 목표·역량·시간·장비 제약을 보관한다. `sources/`에는 원문과 메타데이터, 개별 분석이 있다. `index/research-map.md`는 누적 역량과 연구의 연결, `research/`는 연구 카드, `experiments/`는 계획과 관찰, `roadmap/current.md`는 현재 우선순위, `decisions/`는 변경 근거를 담는다.

원문 등록과 중복 검사는 Python 도구가 한다. 내용 해석, 선행연구 확인, 실험 설계, Markdown 갱신은 Claude Code/Codex가 수행한다. 보조 스크립트 실행만으로 분석까지 끝나는 것은 아니다.

## 안전한 갱신과 Git

두 도구는 번갈아 사용한다. 한 저장소를 동시에 수정하지 않는다. 스킬은 변경 전에 협조적 잠금과 스냅샷을 만들도록 지시하지만, 일반 편집기의 수정을 강제로 막지는 못한다. 중간 실패는 자동으로 모든 파일이 복구되는 트랜잭션이 아니다. 잠금과 복구 절차는 `skills/research-compass/references/operations.md`를 참고한다.

원한다면 로컬 이력부터 시작한다.

```bash
git init
git status
```

커밋·원격 저장소 생성·push는 자동으로 하지 않는다. `.gitignore`는 원문, 추출문, inbox, 스냅샷, 모델/데이터 파일을 기본 제외한다. 따라서 기본 Git 커밋만으로 원문이 백업되지는 않는다. 원문은 승인된 별도 저장소에 백업하거나, 공개 가능한 자료에 한해 제외 규칙을 직접 조정해야 한다.

분석문·메타데이터에도 기밀이 남을 수 있다. 비공개 저장소라도 공유 전에 확인한다. 로컬 파일 관리와 오프라인 AI 실행은 다르므로 기밀 RFP를 처리하기 전에 사용하는 AI 서비스와 조직 정책을 확인한다.

## 품질 확인

```bash
python3 skills/research-compass/scripts/compass.py check --root .
python3 -m unittest discover -s skills/research-compass/scripts -p 'test_*.py' -v
```

검사기는 원문 해시, 필수 구조, 출처 연결, 인덱스 일치, 기록 ID를 확인한다. 연구 해석의 진실성, 새로움, 기밀 정책 준수, 문서 추출의 완전성은 보장하지 않는다. 스킬 행동 평가 시나리오는 `references/evaluation-cases.md`에 있다.

초기 버전은 자동 공고 수집기, HWP/PDF 전용 파서, 실험 실행기, 데이터베이스 서버를 포함하지 않는다. 문서 파싱과 웹 접근은 해당 세션이 제공하는 도구를 이용하고, 불가능한 부분은 명시한다.

## 호환성 근거

2026-09-07 공식 문서 확인: [Codex skills](https://developers.openai.com/codex/skills/), [Claude Code skills](https://code.claude.com/docs/en/skills). 스킬 핵심 지침은 공통 `SKILL.md`에 있고, 도구별 연결만 다르다. 실제 설치된 제품 버전·정책에 따른 인식 여부는 로컬 세션에서 확인해야 한다.
