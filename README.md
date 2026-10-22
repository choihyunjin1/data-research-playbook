# Data Research Playbook

다음 데이터 분석 대회에서 **비교 방법·검증 코드·실패 사례·적용 조건**을 찾아 쓰기 위한 저장소입니다. 이전 채팅을 읽지 않은 사람과 AI도 필요한 자료를 고르고, 어디까지 믿을 수 있는지 확인할 수 있게 정리합니다.

해양 수온 공백 보완은 **첫 사례**입니다. 해양 모델·수심·시간창·대회 조건을 다른 분야의 기본값으로 삼지 않습니다. 새 대회는 별도 프로젝트에서 진행하고, 대회 중의 기록은 그 프로젝트에 남깁니다. **종료 후 검증된 교훈을 일괄 검토**해 이 저장소에 반영합니다.

## 새 채팅에서 이 주소를 받았다면

1. 현재 요청에서 **대회·문제·원하는 산출물**을 확인합니다. 목적 없이 주소만 받았다면 저장소의 쓰임을 짧게 설명하고 “이번에는 어떤 대회나 작업에 쓰려 하나요?”만 묻습니다. 이미 알려준 내용은 다시 묻지 않습니다.
2. 아래 표에서 맞는 지침 **한 개부터** 읽고, 근거가 필요할 때 연결된 사례·코드로 이동합니다. 저장소 전체 열람이나 설치가 시작 조건은 아닙니다.
3. 이번 작업에 **가져올 방법 / 가져오지 않을 사례 조건**을 짧게 구분합니다. 실제 적용·인계에는 읽은 커밋이나 릴리스를 남깁니다. 최신 기본 브랜치에서 찾되, 계산을 시작할 때는 버전을 고정합니다.

웹 접근이 안 되면 README 첨부나 본문 제공을 요청합니다. README만 읽었다면 하위 문서를 읽었다고, 코드를 보았다면 실행했다고 보고하지 않습니다. **주소 전달은 읽기·참조의 출발점이며 공개·수정 권한의 위임이 아닙니다.**

대회 공고가 있다면 아래 문장을 함께 보내면 됩니다. 주소만 보내도 위 순서로 시작할 수 있지만, 어떤 대회인지는 주소에서 알아낼 수 없습니다.

> 이 저장소를 참고해 이번 대회를 시작하자. 공고는 [주소]다. 필요한 방법만 골라 적용하고, 대회가 끝나면 검증된 교훈을 저장소에 반영하자.

## 필요한 곳부터 읽기

| 언제 쓰나 / 시작점 | 얻는 것 | 가져오지 않을 조건 / 근거 |
|---|---|---|
| 처음 하는 분야·대회 → [새 대회 시작](playbooks/new-competition.md) | 공고·자료 권리·목표·첫 비교 정리 | 과거 대회의 권한·도구 요건은 재사용하지 않음. 문서에 실제 막힌 사례 연결 |
| 공백 처리 비교 → [결측 자료 분석](playbooks/missing-data.md) | 기준선·가림·같은 분모·선택기 손익 | 해양 수심·시간창을 기본값으로 쓰지 않음. 아홉 연구의 반례 연결 |
| 입력·평가 경계 검사 → [코드 계약](playbooks/code-contracts.md) | 작은 검증 함수와 실패 반례 | 모든 프로젝트에 모든 검사를 요구하지 않음. 코드·검사 연결 |
| 글·그림·발표 설명 → [결과 전달](playbooks/communicating-results.md) | 실제 개선·기능·제안 구분 | 연구 수치를 현장 효과로 바꾸지 않음. 실패 기록 연결 |
| 다른 작업자에게 넘김 → [인계](playbooks/handoff.md) | 현재본·실행 증거·미완료·다음 행동 | 과거 PASS를 새 환경의 PASS로 쓰지 않음. 재사용 시험 연결 |
| 대회 종료 후 새 교훈 반영 → [기여 절차](CONTRIBUTING.md) | 후보·확인된 범위·정정·공개 검토 | 작업마다 문서를 늘리지 않음. 새 근거를 기존 항목과 대조 |

첫 사례의 결론은 [해양 공백 보완](cases/ocean-gap-repair/README.md), 지침을 더 붙여도 추가 효과가 확인되지 않았던 결과는 [과거 평가](evals/history/README.md)에 있습니다. 문서 수나 테스트 수를 발전의 증거로 삼지 않습니다.

## 계산을 실제 실행할 때만

0.1 버전은 **Git checkout과 editable 설치**를 지원합니다. 사례 파일이 checkout에 있으므로 일반 wheel만 설치하는 배포 방식은 지원 범위가 아닙니다. Python **3.12**의 프로젝트 가상환경을 사용하며 원 작성자의 환경이나 개인 경로는 필요하지 않습니다.

```powershell
git clone https://github.com/choihyunjin1/data-research-playbook.git
cd data-research-playbook
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e .
python -m research_playbook demo
```

`demo`는 외부 원자료 없이 합성 입력으로 계산을 보여주는 경로입니다. [예제 안내](examples/README.md)에서 읽을 결과를 확인합니다. 설치에 필요한 패키지 취득과 예제 실행은 별개입니다. 실제 연구 재계산에는 [출처와 파일 식별자](cases/ocean-gap-repair/SOURCES.md)에 맞는 공개 원본을 별도로 준비하고 netCDF4가 포함된 replay 의존성을 설치합니다.

```powershell
python -m pip install -e ".[replay]"
python -m research_playbook replay --case ocean-gap-repair --input-root "<공개 원본을 둔 폴더>" --output "<새 결과 폴더>"
```

합성 예제 통과, raw부터 재계산, 저장 집계와의 대조는 서로 다른 결과입니다. [v0.1.0 연구 이관 검수](reports/VALIDATION.md)는 당시 기록이며 영구 PASS 표가 아닙니다. [v0.1.1 입구·기여 절차 검수](reports/VALIDATION-v0.1.1.md)와 실행별 receipt를 구분합니다. 과거 연구의 PASS를 새 환경의 PASS로 옮겨 적지 않습니다.

## 다른 AI와 오래 사용하는 법

공통 입구는 이 README와 일반 Markdown 링크입니다. 웹에서 URL을 읽는 것과 로컬 작업 폴더의 지침 자동 인식은 다릅니다. Codex는 프로젝트의 [AGENTS.md](AGENTS.md), Claude Code는 [공통 지침 연결](CLAUDE.md), Copilot은 [저장소 안내](.github/copilot-instructions.md)로 공통 규칙에 연결합니다. 지원 버전·설정에 따라 자동 인식이 달라지며, 모든 하위 문서를 자동으로 읽는다는 보장은 없습니다.

호환성 안내 확인일: 2026-10-23. [Codex 공식 문서](https://learn.chatgpt.com/docs/agent-configuration/agents-md), [Claude Code 공식 문서](https://code.claude.com/docs/en/memory), [Copilot 지원표](https://docs.github.com/en/copilot/reference/custom-instructions-support)를 확인했습니다. 제품별 실앱 동작 검증과 문서 확인은 별개입니다. 선택적 스킬을 폴더만 떼어 글로벌 설치하면 상대경로가 깨질 수 있으므로 설치를 권장하지 않습니다.

새 대회 공고·이용 조건은 사용할 때 다시 확인합니다. 과거 릴리스는 그대로 두고 새 판단은 후속 버전에 남깁니다. 구체적인 갱신·공개·버전 절차는 [기여 절차](CONTRIBUTING.md)에 있습니다.

## 저장하는 것과 저장하지 않는 것

- `src/`, `tests/`: 작은 계약 함수와 합성 반례. 해양 방법은 별도 domain 경계에 둡니다.
- `cases/ocean-gap-repair/`: 방법·입력 조건, 연구 이력, 요약 수치, 실패와 결론, 출처.
- `playbooks/`: 실제 사건에서 바뀐 작업 방식. 모든 작업에 다섯 문서를 읽으라는 뜻이 아닙니다.
- `.agents/skills/evidence-driven-workflow/`: 기존 공통 스킬을 이어받은 선택적 안내. 실행에 스킬 설치가 필요하지 않습니다.
- `evals/history/`: 과거 비교의 범위와 부정적 결과. 테스트 수·문서 수를 생산성 점수로 사용하지 않습니다.

원자료, 제한된 대회 자산, 제3자 코드·PDF, 계정 화면과 인증 정보는 포함하지 않습니다. 자료 취득 주소·버전·SHA와 가공 내용을 남깁니다. 로컬 원본 복구 패키지는 공개 저장소와 별개이며 다른 장치의 백업을 뜻하지 않습니다.

기여 시 [공통 작업 경계](AGENTS.md)와 [기여 절차](CONTRIBUTING.md)를 따릅니다. 직접 작성한 코드는 MIT, 문서는 CC BY 4.0이며 외부 자료의 권리를 대체하지 않습니다. 인용할 때는 사용한 커밋이나 release를 함께 적어 결과의 버전을 구분합니다.
