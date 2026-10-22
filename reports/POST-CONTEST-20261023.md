# 합성 대회 종료 후 반영·인계 — 2026-10-23

범위: 사본 저장소만 변경. 기준 HEAD는 `c0551597b5998f73a1c3368d707ae33ac289c311`, 패키지 버전은 0.1.1, 작업 브랜치는 `codex/post-contest-return-test`입니다. 시작 시 추적·미추적 변경은 없었습니다. **새 commit·tag·release·원격 게시를 하지 않았습니다.** 아래는 당시 릴리스 검수의 갱신이 아니라 이번 작업의 별도 기록입니다.

## 반영한 판단

[새 사례](../cases/bike-rental-synthetic/README.md)의 고정 합성 입력에서 같은 4일의 4시간 대여 총계를 평가했습니다. time MSE 50, neighbor MSE 200, 저장 choice MSE 25건²가 재현됐습니다. 놓친 이득 25, 피한 손해 200의 전체 4일 분모 분해도 일치했습니다. 이는 **해당 고정 합성 출력의 산술에 한정한 supported**이며 선택기 알고리즘의 성능 입증이 아닙니다.

[결측 자료 지침](../playbooks/missing-data.md)에 이 사례의 링크와 해석 경계만 연결했습니다. 기존 동일분모 원칙을 복제하지 않았고, 4시간·정수 건수 계약은 사례 코드에 두었습니다. 공통 `src/`, README 입구, AGENTS, 스킬, 패키지 버전과 과거 릴리스 설명은 변경하지 않았습니다. 새 사례를 릴리스할 경우 기여 절차상 후속 minor 범위이며, 이번에는 릴리스하지 않았습니다.

## 보류와 대조

- 보편 선택기 기본값: 일반화·상류 무누출성 근거가 없어 채택하지 않았습니다. 정답을 보고 후보나 choice를 바꾸지 않았습니다.
- 준비시간 40% 단축: 동일조건 시간 측정이 없는 체감이므로 candidate로만 구분하고 성과 지표로 반영하지 않았습니다.
- 기존 자전거 시험: 제공 checkout에서 관련 자료를 찾지 못했습니다. 그 수치와의 직접 비교는 미확인입니다. 전력계·수온 재사용 시험으로 대체하지 않았습니다.
- Ocean: 새 사례와 목표·자료·단위·선택 근거가 달라 이전 부정적 결과를 정정할 근거가 아닙니다. 기존 결론은 문서로 대조했으며 raw 재계산은 하지 않았습니다.
- 권리 보류 첨부: `rights-pending/source-excerpt.txt` 내용은 열람·복사·요약·인용·stage하지 않았습니다. 원 패킷 README에 허용된 처리 상태와 사유만 사례에 남겼습니다. 원자료는 이동·삭제하지 않았습니다.

## 실행 증거와 한계

Python 3.12.10, Windows에서 실행했습니다. 새 계산은 표준 라이브러리만 쓰며 설치·학습·네트워크 요청은 하지 않았습니다. 필요한 회귀에서는 `PYTHONPATH`를 사본 `src`로, 임시 디렉터리를 사본 `.runs/tmp`로 **실행 프로세스에만** 지정했습니다. 전역 설정 변경은 없습니다.

| 실제 실행 | 결과 | 확인한 범위 |
|---|---|---|
| `python -B cases/bike-rental-synthetic/evaluate.py` | 종료 0 | 고정 입력 재계산, 날짜별 총계와 전체분모 손익 |
| `python -B cases/bike-rental-synthetic/evaluate.py --verify` | 종료 0, PASS | 입력 SHA와 저장 JSON 전체 값의 동등성 |
| `python -B -m unittest discover -s tests -p test_bike_rental_synthetic.py -v` | 종료 0, 8개 통과 | 정상 총계, 관측 0, 행순서, 정답 변이, 빈·중복·누락·잘못된 입력 |
| 독립 검산 | 종료 0, 수치 일치 | 다른 작업자가 원 패킷 CSV를 별도 표준 라이브러리 코드로 재합산; 이관 계산 함수를 공유하지 않음 |
| 원 CSV와 이관본 대조 | 일치 | 원본은 이관본 뒤에 LF 한 개가 더 있는 것뿐; 실제 데이터 값 동일 |
| `python -B -m unittest discover -s tests -v` | 종료 1, 전체 FAIL | 18개 실제 검사 통과, 모듈 로딩 오류 2개. `test_contracts`, `test_replay`가 `pandas` 부재로 실행되지 못함 |
| `python -B -m research_playbook demo` | 종료 1 | `ModuleNotFoundError: No module named 'pandas'`; demo 결과 미검증 |

실행 시 NumPy는 발견됐지만 pandas와 netCDF4는 없었습니다. 설치 금지를 지켰습니다. 위 20개 항목을 “전체 20개 검사 통과”로 기록하지 않으며, 과거 PASS를 현재 환경에 적용하지 않습니다. raw replay, 실제 대회 성능, 생산성, 사람 재사용, 제품별 AI 동작, 원격 공개 및 화면 렌더 검수는 이번 범위에서 확인하지 않았습니다.

## 공개 선택·보존 확인

검토한 파일의 명시적 경로만 stage했습니다. 신규 6개 파일, 기존 지침 1개와 공개 메타데이터 2개로 **총 9개 경로**이며 `git add .`는 사용하지 않았습니다. 새 파일의 목적·권리·선정 이유·개인정보 검토를 파일별 inventory에 기록하고 수정한 기존 3개 경로도 재검토했습니다. 이 공개 가능성 검토는 실제 외부 게시나 법률 인증이 아닙니다.

| 검사 | 결과 |
|---|---|
| 시작 시 `check_public_inventory.py --list-pending` | 기존 추적 133개 모두 등재, 미추적 후보 없음 |
| 선정 후·stage 전 동일 검사 | 새 6개가 미추적이라 일시 FAIL. 검토된 경로를 stage한 뒤 재검사 |
| `python -B scripts/check_public_inventory.py` | 종료 0, PASS; 추적 139개와 inventory 139개 일치 |
| `python -B scripts/check_public.py` | 종료 0, PASS; 139개 파일의 제한 패턴·크기·로컬 Markdown 링크 검사, 오류 0 |
| `python -B scripts/package_manifest.py` 및 `--verify` | 각각 종료 0; manifest 자신을 뺀 138개 파일의 현재 SHA·크기 일치 |
| `git diff --cached --stat` 및 `git diff --cached` | 9개 의도한 경로를 직접 검토; 제한 첨부 없음 |
| `git -c core.whitespace=cr-at-eol diff --cached --check` | 종료 0; 기존 JSON의 CRLF를 보존한 검사. 기본 검사에서 나온 CR-at-EOL 표시는 문장 끝 공백 수정으로 오인하지 않음 |
| 기존 manifest의 SHA와 변경 제외 파일 직접 대조 | 기존 132개 해시 항목 중 지침·inventory 2개를 제외한 **130개 전부 일치** |

Ocean 연구·동결 코드·기존 `evals/`·과거 `reports/`·`RELEASE_NOTES.md`는 위 130개 보존 대상에 포함됩니다. 새 인계 파일만 `reports/`에 추가했습니다. 기존 이력과 태그·릴리스 자산은 덮어쓰지 않았고 기준 HEAD도 그대로입니다. 검사 후 이 기록을 고치고 다시 stage·manifest 생성·검증하여 마지막 파일 변경을 지문에 반영했습니다.

## 다음 작업자가 받을 파일

- [사례 설명](../cases/bike-rental-synthetic/README.md): 판단·적용 조건·기존 결과 대조·보류·출처·라이선스.
- [고정 입력](../cases/bike-rental-synthetic/results-input.csv), [검산 코드](../cases/bike-rental-synthetic/evaluate.py), [저장 결과](../cases/bike-rental-synthetic/results.json), [정상·실패 검사](../tests/test_bike_rental_synthetic.py).
- [지침의 사례 연결](../playbooks/missing-data.md), [파일별 공개 검토](../provenance/PUBLIC_FILES.json), [현재 파일 SHA 목록](../PUBLIC_MANIFEST.json), 이 인계 기록.

다음의 미완료는 기존 의존성이 준비된 승인 환경에서 전체 회귀와 demo를 다시 실행하는 일입니다. 이전 자전거 근거가 제공되면 동일 목표·분모·후보·선택 조건인지 대조할 수 있습니다. 원격 게시·릴리스는 이번 권한에 포함되지 않았습니다.
