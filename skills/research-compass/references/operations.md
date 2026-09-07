# 운영과 설치

## 지원 환경

macOS/Linux, Python 3.9 이상, 표준 라이브러리만 사용한다. 보조 스크립트는 네트워크를 쓰지 않는다. 추론과 승인된 웹 조회는 AI 호스트가 한다. HWP/PDF/DOCX 파서는 포함하지 않으니 세션이 제공하는 도구를 쓰고, 못 읽은 부분은 밝힌다. 파서를 몰래 설치하거나 시스템 설정을 바꾸지 않는다.

Codex는 `.agents/skills/`, Claude Code는 `.claude/skills/`에서 스킬을 찾고 둘 다 심링크를 지원한다 (2026-09-07 공식 문서 기준: [Codex](https://developers.openai.com/codex/skills/), [Claude Code](https://code.claude.com/docs/en/skills)). 워크스페이스는 `skills/research-compass/`를 원본으로 두고 두 위치에서 상대 심링크로 연결한다. Claude Code 플러그인으로 설치한 경우 스킬은 플러그인 캐시에서 로드되며, 워크스페이스 안의 복사본은 Codex와 스크립트 경로용이다.

## 새 워크스페이스

```bash
python3 <skill-dir>/scripts/compass.py init --root ./my-research
cd my-research && python3 setup.py
```

`init`은 빈 디렉터리에만 동작하고 스킬 디렉터리 안에는 만들지 않는다. `setup.py`는 프로젝트 안에 심링크만 만든다. 홈 설정, Git 원격, 제품 설치는 건드리지 않고, 충돌하는 파일이 있으면 덮어쓰지 않고 중단한다. 재실행은 안전하다.

읽기 전용 샌드박스에서는 저장이 안 된다. 갱신했다고 하지 말고 그 사실을 보고한다.

## 다중 파일 갱신 절차

명령은 워크스페이스 루트 기준이다.

```bash
C=skills/research-compass/scripts/compass.py
python3 $C check --root .
python3 $C lock-acquire --root . --owner claude-session     # 토큰을 받는다
python3 $C snapshot --root . --lock-token TOKEN
python3 $C ingest --root . --lock-token TOKEN --file inbox/new.txt --kind job --title "제목"
# analysis.md 작성 → source.json의 analysis_status 갱신 → 카드·지도·로드맵 대조 → decisions/ 추가
python3 $C reindex --root . --lock-token TOKEN
python3 $C check --root .
python3 $C lock-release --root . --lock-token TOKEN
```

- 토큰은 `--lock-token` 또는 환경변수 `COMPASS_LOCK_TOKEN`으로 넘긴다. 남의 락 토큰을 읽어 쓰지 않는다.
- 실패해도 자기 락은 해제하되, 실패와 부분 쓰기 상태는 그대로 보이게 둔다.
- 락은 나이나 PID로 자동 만료시키지 않는다. `lock-status`로 소유자와 시각을 본다. 버려진 락은 사용자가 토큰과 함께 명시적으로 제거를 승인할 때만 지운다.
- 스냅샷은 복구용 사본이지 자동 롤백이 아니다. 차이를 비교한 뒤 필요한 파일만 되돌린다.
- 락은 협조하는 에이전트끼리의 약속이다. 편집기 쓰기는 못 막으니 Claude Code와 Codex를 같은 워크스페이스에서 동시에 쓰지 않는다. 병렬이 필요하면 worktree를 나누고 명시적으로 합친다.
- 검토만 했고 바뀐 게 없으면 로그를 채우려고 변경을 지어내지 않는다.

## 원문 버전과 검증

- 개정본은 `--related-to SRC-ID --relation revision`, 재게시는 `repost`, 관련 자료는 `related`. 스크립트는 revision/repost를 같은 수요 그룹으로 묶지만, 문장이 바뀐 중복 판단은 에이전트 몫이다.
- 정확 중복 검사는 기록된 kind·organization으로만 한다. 나중에 알게 된 기관명은 decision 로그와 함께 명시적으로 고친 뒤 다시 묶는다.
- `check`는 읽기 전용이고 구조 오류에 0이 아닌 코드를 낸다. pending/partial은 경고이지 분석 완료가 아니다.
- 해시 불일치를 해시 교체로 '고치지' 않는다. 승인된 백업에서 원문을 복구하거나 새 버전으로 등록한다.

```bash
python3 -m unittest discover -s skills/research-compass/scripts -p 'test_*.py' -v
```

## 개인정보·버전 관리·한계

- 제공된 `.gitignore`는 inbox, 원문/추출문, 스냅샷, 모델/데이터, env 파일을 제외한다. 분석문과 메타데이터는 제외하지 않으므로 공유 전에 확인한다. 기본 커밋만으로 원문은 백업되지 않는다.
- 자동 커밋·push·원격 저장소 생성·RFP 업로드·예약 작업은 하지 않는다.
- 로컬 저장이 오프라인 추론을 뜻하지 않는다. 호스트 AI는 컨텍스트를 자기 서비스로 보낸다. 기밀 자료는 조직 정책을 먼저 확인한다.
- 이 버전에는 크롤러, DB 서버, 벡터 검색, 자동 실험 실행기가 없다.
