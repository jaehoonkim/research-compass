# Research Compass — 연구 방향 나침반

채용공고·과제 RFP·연구자료·실험 결과를 근거로 연구 로드맵을 누적 관리하는 로컬 워크스페이스다. 대화 기록 대신 이 폴더가 지속되는 기록이 된다. 스킬 자체는 Claude Code 플러그인 `research-compass`에 있고, 이 폴더에는 연구 기록만 남는다.

## 시작

이 폴더를 Claude Code로 열고 `/research-compass`를 호출한다.

```text
/research-compass inbox/새공고.txt를 추가하고 기존 연구 방향에 미치는 영향을 반영해줘.
/research-compass 지금까지의 기록을 읽고 다음 실험을 추천해줘. 파일은 수정하지 마.
/research-compass inbox/실험결과.md를 실제 관찰과 해석으로 나누어 기록하고 로드맵에 반영해줘.
```

자료가 없으면 본문을 대화에 붙여 넣어도 된다. URL은 세션이 실제로 읽을 수 있는 범위만 처리하며, 접근 실패를 읽은 것처럼 분석하지 않는다.

## 무엇이 어디에 남는가

- `profile/researcher.md`: 확인된 목표·역량·시간·장비 제약
- `sources/`: 원문, 메타데이터, 개별 분석
- `index/research-map.md`: 누적 역량과 연구의 연결
- `research/`: 연구 카드, `experiments/`: 계획과 관찰
- `roadmap/current.md`: 현재 우선순위, `decisions/`: 변경 근거

원문 등록과 중복 검사는 플러그인의 `compass.py`가 하고, 내용 해석·선행연구 확인·실험 설계·Markdown 갱신은 Claude가 한다. 스크립트만 돌려서는 분석이 끝나지 않는다.

## 상태 점검

```bash
C=$(ls -d ~/.claude/plugins/cache/research-compass/research-compass/*/skills/research-compass)/scripts/compass.py
python3 $C check --root .
```

검사기는 원문 해시, 필수 구조, 출처 연결, 인덱스 일치, 기록 ID를 확인한다. 연구 해석의 진실성, 새로움, 기밀 정책 준수, 문서 추출의 완전성은 보장하지 않는다.

## Git과 기밀

```bash
git init
```

커밋·원격 생성·push는 자동으로 하지 않는다. `.gitignore`는 원문, 추출문, inbox, 스냅샷, 모델/데이터 파일을 기본 제외하므로 기본 커밋만으로 원문은 백업되지 않는다. 분석문과 메타데이터에도 기밀이 남을 수 있으니 공유 전에 확인한다. 로컬 파일 관리와 오프라인 AI 실행은 다르므로 기밀 RFP를 처리하기 전에 조직 정책을 확인한다.
