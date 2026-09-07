# 운영

## 환경

macOS/Linux, Python 3.9 이상, 표준 라이브러리만. 스크립트는 네트워크를 쓰지 않는다. `git`이 PATH에 있어야 `init`이 저장소를 만든다. PDF/HWP 파서는 포함하지 않으니 세션이 제공하는 도구를 쓰고 못 읽은 부분은 밝힌다.

스킬은 Claude Code 플러그인으로 설치되어 플러그인 캐시에서 로드된다. 워크스페이스에는 스킬 사본이 없다. 아래 `$C`는 이 `SKILL.md`와 같은 디렉터리의 `scripts/compass.py`다.

## 명령

```bash
python3 $C init --root ./my-research                 # 구조 생성 + git init + 첫 커밋
python3 $C ingest --root . --file inbox/x.pdf --into library --title "논문 제목" \
    [--organization --source-url --published-date --collected-date --visibility --related-to LIB-… --relation revision|repost|related]
python3 $C ingest --root . --file inbox/y.txt --into signals --title "공고 제목" [--organization …]
python3 $C new-project --root . --slug rvv-quant --title "프로젝트 제목"
python3 $C check --root .
```

`init`은 빈 디렉터리에만 동작한다. 이미 `compass.json`이 있으면 아무것도 바꾸지 않는다. `ingest`는 원문을 바이트 그대로 보존하고 SHA-256을 기록하며, 같은 폴더의 같은 해시(signals는 같은 organization까지)면 기존 ID를 돌려준다. `new-project`는 다음 번호를 배정하고 `project.md`(stage direction)와 `reading.md`, `experiments/`를 만든다. `check`는 읽기 전용이고 오류가 있으면 종료 코드 1이다.

## 갱신 절차

1. `check`로 현재 상태를 본다.
2. 필요한 파일을 편집한다. 원문(`original.*`)은 절대 수정하지 않는다.
3. 일지에 항목을 덧붙인다.
4. `check`. 실패하면 "저장됐지만 불일치"로 보고하고 오류를 그대로 보여준다.
5. 커밋은 사용자가 요청할 때. `git add -A && git commit -m "…"`.

같은 워크스페이스를 두 세션이 동시에 편집하지 않는다. 충돌은 git이 알려준다.

## 원문 버전

개정본은 `--relation revision`, 재게시는 `repost`, 관련 자료는 `related`. 해시 불일치를 해시 교체로 고치지 않는다. 원문을 git에서 복구하거나 새 버전으로 등록한다.

## 개인정보와 한계

- 워크스페이스 `.gitignore`는 inbox와 모델·데이터 폴더만 제외한다. 원문과 분석문은 커밋된다. 원격 저장소에 올리기 전에 기밀 여부를 확인한다.
- 자동 커밋·push·원격 생성·원문 업로드·예약 작업은 하지 않는다.
- Claude Code는 컨텍스트를 Anthropic 서비스로 보낸다. 기밀 RFP는 조직 정책을 먼저 확인한다.
- 크롤러, DB, 벡터 검색, 자동 실험 실행기는 없다.

## 테스트

```bash
python3 <skill-dir>/scripts/test_compass.py
```
