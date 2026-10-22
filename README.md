# Data Research Playbook

데이터를 더 많이 채우거나 검사를 더 많이 만들었다고 결과가 좋아지는 것은 아니었습니다. 이 저장소에는 **무엇을 비교했고, 어떤 조건에서 실패했으며, 다음 작업에서는 무엇을 바꿀지**를 실행 예제와 함께 남깁니다.

첫 사례는 공개 해양 수온 자료의 공백 보완 연구입니다. 같은 보정식이 한 지점에서는 시간 보간보다 좋았고 다른 지점에서는 나빴습니다. 주변 관측으로 두 방법을 선택하는 규칙도 모든 기준선을 이기지는 못했습니다. 성공한 표만 모으지 않고 이 판단에 이른 아홉 단계를 보존합니다.

## 필요한 곳부터 읽기

| 하려는 일 | 시작점 |
|---|---|
| 연구의 결론과 실패 조건 이해 | [해양 공백 보완 사례](cases/ocean-gap-repair/README.md) |
| 공백 처리 방법을 같은 조건에서 비교 | [결측 자료 분석](playbooks/missing-data.md) |
| 코드의 잘못된 입력·거짓 PASS 차단 | [코드 계약](playbooks/code-contracts.md) |
| 결과를 글·그림·발표로 설명 | [결과 전달](playbooks/communicating-results.md) |
| 다른 대회에 이전 연구를 연결 | [새 대회 검토](playbooks/new-competition.md) |
| 정본·검증·미완료 상태 인계 | [인계](playbooks/handoff.md) |
| 스킬을 더 붙이는 것이 도움이 됐는지 확인 | [효과가 없었던 평가도 포함한 이력](evals/history/README.md) |

## 실행 입구

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

합성 예제 통과, raw부터 재계산, 저장 집계와의 대조는 서로 다른 결과입니다. 이 저장소에서 실제로 실행한 상태는 [검수 기록](reports/VALIDATION.md)과 각 실행의 receipt로 확인합니다. 같은 PC의 깨끗한 clone 재현은 다른 운영체제·장비 재현과 구분합니다. 과거 연구의 PASS를 새 환경의 PASS로 옮겨 적지 않습니다.

## 저장하는 것과 저장하지 않는 것

- `src/`, `tests/`: 작은 계약 함수와 합성 반례. 해양 방법은 별도 domain 경계에 둡니다.
- `cases/ocean-gap-repair/`: 방법·입력 조건, 연구 이력, 요약 수치, 실패와 결론, 출처.
- `playbooks/`: 실제 사건에서 바뀐 작업 방식. 모든 작업에 다섯 문서를 읽으라는 뜻이 아닙니다.
- `.agents/skills/evidence-driven-workflow/`: 기존 공통 스킬을 이어받은 선택적 안내. 실행에 스킬 설치가 필요하지 않습니다.
- `evals/history/`: 과거 비교의 범위와 부정적 결과. 테스트 수·문서 수를 생산성 점수로 사용하지 않습니다.

원자료, 제한된 대회 자산, 제3자 코드·PDF, 계정 화면과 인증 정보는 포함하지 않습니다. 자료 취득 주소·버전·SHA와 가공 내용을 남깁니다. 로컬 원본 복구 패키지는 공개 저장소와 별개이며 다른 장치의 백업을 뜻하지 않습니다.

기여 시 [AGENTS.md](AGENTS.md)를 따릅니다. 직접 작성한 코드는 MIT, 문서는 CC BY 4.0이며 외부 자료의 권리를 대체하지 않습니다. 인용할 때는 사용한 커밋이나 release를 함께 적어 결과의 버전을 구분합니다.
