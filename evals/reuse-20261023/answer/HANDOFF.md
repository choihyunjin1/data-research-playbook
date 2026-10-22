# 독립 재사용 시험 인계 — 2026-10-23

## 결론과 현재본

요청서 → 공개 저장소 README → 해당 플레이북/코드 경로로 들어와 실제로 실행했다. 이전 채팅, 메모리, 원 연구 폴더, 부모 작업자의 기대답은 읽지 않았다. 모든 새 파일은 이 `answer/`에 `apply_patch`로만 작성했다. 공개 저장소와 입력 파일은 수정 대상으로 삼지 않았다.

- `meter_fixed.py`: 원본 `meter_candidate.py`를 보존한 별도 최소 수정안. ID와 clip은 저장소 계약 함수를 재사용하고, 평균은 기존 pandas 시간 창을 블록 안에서만 계산한다.
- `test_reuse.py`: 수정 전 결함 관찰값을 출력하고, 수정 후 반례 차단/정상 회귀를 실제 assertion으로 검사한다. 11개 unittest 메서드 실행, 모두 통과.
- `compare_gap.py`: 합성 CSV의 중앙 6시간(09~14시)을 선가림한 후 고정 방법을 호출한다. 시간 보간의 일평균 오차 0, 경계잔차 보정의 절대오차 0.25. 두 방법 모두 같은 24시간/동일 공백/남은 관측을 사용한다.
- 이 문서: 읽은 경로, 실행 명령과 실제 결과, 실행하지 않은 항목, 불필요했던 작업을 한 파일에 모았다.

실행 환경은 제공된 기존 Python 3.12.10, NumPy 2.3.5, pandas 3.0.1이다. 설치나 환경 변경은 하지 않았다. Python 명령은 모두 `-B`를 사용해 import에 따른 `__pycache__` 생성을 막았다. 기존 `.pyc` 파일이 있는 사실은 파일명 목록에서 관찰했지만 이번 실행이 만든 파일로 주장하지 않는다.

## 1. 전력계 코드에서 확인하고 바꾼 것

### ID 및 clip

실제 수정 전 출력은 다음과 같다.

| 입력/대상 | 원본에서 관찰한 출력 | 수정안 정책 |
|---|---|---|
| ID `2.9` | `2` | ValueError |
| ID `"2.000000000000000000001"` | `2` | 정밀 소수부를 float 변환 전에 검사하여 ValueError |
| ID `0`, `1000` | `0`, `1000` | 1~999 범위 밖이므로 ValueError |
| 예측 `+Inf`, `-Inf` | `100`, `0` | clip 전에 ValueError |
| 예측 NaN | NaN 반환 | clip 전에 ValueError |

`exact_integer(value, name="device_id", minimum=1, maximum=999)`와 `finite_clip(values, 0, 100)`를 그대로 재사용한다. 정상 ID `1`, `999`, `2`, `2.0`, `"2"`, `"2.0"`, Decimal, NumPy 정수의 원본 동등성을 확인했다. 정상 clip `[-2,20,150] → [0,20,100]`, 2차원 배열 모양, 입력 불변성도 검사했다. 이미 upstream float가 잃은 자릿수를 복원하는 기능은 아니다.

### 시간 평균

00:00/00:10/00:20/00:30, 값 `[10,12,100,102]`, 블록 `[a,a,b,b]`에 대해 실제 결과:

- 원본: `[56,56,56,71.33333333333333]` — 블록 인자를 무시해 섞임.
- 수정안: `[11,11,101,101]`.
- b 값만 바꿔도 a 결과 불변, a 값만 바꿔도 b 결과 불변을 각각 assertion으로 검사했다.

저장소의 `boundary_mean`을 무조건 래핑하지 않았다. 원본의 중앙 60분 rolling은 `(t−30분, t+30분]`이고, 저장소 함수는 양끝을 포함한다. 00:00/00:30, 값 `[10,20]`, 같은 블록에서 원본과 수정안은 `[15,20]`, 저장소 함수는 `[15,15]`임을 실제로 확인했다. 따라서 기존 `rolling("60min", center=True, min_periods=1, closed="right")`을 각 블록에 적용하고 원래 위치에 돌려놓았다.

정상 회귀에는 상승/하강 시간순, 중복 시각, 빈 입력, 하루 떨어진 두 시각, 같은 블록의 기존 출력 동등성이 포함된다. 불필요하게 중복 시각·하강 시간순을 금지하지 않았다. 누락 시각을 새로 채우지도 않는다. 반환 API는 원본처럼 평균 배열 하나다.

추가로 정한 명시적 오류 정책: 값/블록의 길이·차원 불일치, 비유한 평균 입력/출력, 누락·빈 블록, NaT와 비단조 시각, `a,b,a`처럼 다시 나타나는 블록 이름은 거부한다. 마지막 정책은 저장소의 연속 평가 블록 계약을 따른 것이며, 요청에 문자 그대로 있던 조건은 아니다. 별도 구간이라면 서로 다른 블록 이름을 줘야 한다. 중앙 평균은 이후 시각도 사용하는 사후 변환이며 인과적 미래예측으로 바뀐 것이 아니다.

## 2. 합성 공백 비교의 설정과 실제 결과

- CSV의 hour -1,24는 양옆 문맥, 평가 일자는 hour 0~23의 24개다. 실제 날짜·단위·지점은 주어지지 않았다.
- `가운데 6시간`은 시간 09,10,11,12,13,14로 고정했다. 가림 직전 전체 목표층의 24시간 평균은 평가용 정답으로만 별도 보관했다.
- `predict`에 넘기는 배열은 먼저 해당 target 6개를 NaN으로 바꾼 복사본이다. 경계 관측은 08시와 15시이고 둘 다 10이다.
- 공개 저장소의 `cases/ocean-gap-repair/frozen/method.py::predict`를 수정 없이 직접 불러왔다. 모델 fit·임계값 변경·선택기 실행 없음.
- 깊이가 주어지지 않아 고정 함수 기본값 `(20,60,63)`을 사용했다. 이를 이 합성 전력계/지점의 실제 수심으로 해석하면 안 된다. 여기서는 bottom = top + 2가 모든 행에서 성립하므로 이웃층 가중값은 top에 상수만 더한 모양이다. `S−L(S)`에서는 그 상수가 소거되어 해당 보정 비교가 가중치 선택에 의존하지 않는다.

| 방법 | 복원 후 일평균 | 부호 있는 오차 | 절대오차 | 일평균 제곱오차 |
|---|---:|---:|---:|---:|
| 합성 정답 | 10 | — | — | — |
| 남은 18개 평균(참고 기준선) | 10 | 0 | 0 | 0 |
| 시간 보간 | 10 | 0 | 0 | 0 |
| 고정 경계잔차 보정 | 9.75 | -0.25 | 0.25 | 0.0625 |

시간 보간의 공백 복원값은 `[10,10,10,10,10,10]`이다. 실제 float 출력 첫 값은 `10.000000000000002`이며 일평균 출력은 정확히 `10.0`이었다.

경계잔차 보정의 실제 복원값:

`[10.857142857142861, 9.714285714285714, 8.571428571428573, 7.428571428571429, 8.285714285714285, 9.142857142857142]`

고정식은 `L(T) + S − L(S)`이다. 목표층은 하루 내내 10이지만 이웃층은 위아래로 변한다. 이 예의 공백 안 이웃층 곡선이 양쪽 경계 직선에서 벗어난 잔차 합은 -6이다. 따라서 공백 합이 시간 보간의 60에서 54로 내려가고 `(남은 합 180 + 54)/24 = 9.75`가 된다. `bridge_supported=True`여서 이 결과는 입력 부족에 의한 시간 보간 fallback이 아니라 실제 보정을 적용한 결과다. 이 사례에서는 시간 보간이 더 정확하다.

누출 검사는 두 개를 실행했다.

1. 가리지 않은 배열을 고정 함수에 넘기면 `ValueError("Mask hidden target first")`로 거부됨.
2. 숨길 정답 6개를 `[12345,-9999,1000000,-1000000,6789,-4321]`로 바꾼 뒤 다시 가렸을 때, 전달 배열·모든 방법의 복원값·일평균·지원 여부가 원 실행과 완전히 같음.

이는 합성 1일과 지정 공백에서의 계산/누출 방지 확인이다. 실제 지점의 성능, 통계적 우위, 새 미관찰 자료의 독립 일반화 검증이 아니다. 이웃층 정보를 더 사용했다는 이유만으로 보정을 채택할 수 없다는 사례로 이해했다.

## 3. 읽은 경로와 탐색 순서

파일 본문을 읽은 경로(두 허용 디렉터리 밖은 열지 않음):

1. `evals/reuse-20261023/request.md`
2. `<checkout>/README.md`
3. `<checkout>/AGENTS.md`
4. `<checkout>/playbooks/code-contracts.md`
5. `<checkout>/playbooks/missing-data.md`
6. `evals/reuse-20261023/meter_candidate.py`
7. `evals/reuse-20261023/gap-example.csv`
8. `<checkout>/playbooks/handoff.md`
9. `<checkout>/cases/ocean-gap-repair/README.md`
10. `<checkout>/examples/README.md`
11. `<checkout>/src/research_playbook/contracts.py`
12. `<checkout>/tests/test_contracts.py`
13. `<checkout>/cases/ocean-gap-repair/frozen/method.py`
14. `<checkout>/src/research_playbook/demo.py`

`Get-Content -LiteralPath '<위 경로>'`로 위 본문을 각각 읽었고, 아래 명령으로 파일명/크기 목록만 확인했다.

```powershell
Get-ChildItem -LiteralPath 'evals/reuse-20261023' -Force | Select-Object Name, Length, Mode
rg --files '<checkout>/src' '<checkout>/tests'
```

별도 보조 작업자에게도 README에서 시작하는 읽기 전용 정적 코드 검토만 맡겼다. 그 작업자는 위 목록 중 README, code-contracts, contracts.py, test_contracts.py, request.md, meter_candidate.py와 src/tests 파일명 목록만 확인했다. 주 작업자의 동일 관찰과 창 경계 함정을 교차 확인했으며, 보조 작업자의 검토를 실제 실행으로 집계하지 않았다. 실행과 최종 판단은 아래 명령의 결과를 사용했다.

## 4. 실제 실행 명령과 결과

모두 PowerShell에서 호출했으며 작업 위치는 `<original working directory>`였다. 아래 경로가 절대 경로라 작업 위치에 의존하지 않는다. 읽기 전용 조회 명령은 전부 종료 코드 0이었다.

### 환경과 기존 계약 검사

```powershell
& '<checkout>/.venv/Scripts/python.exe' -B -c "import sys, numpy, pandas; print('python=' + sys.version); print('executable=' + sys.executable); print('numpy=' + numpy.__version__); print('pandas=' + pandas.__version__)"
& '<checkout>/.venv/Scripts/python.exe' -B -m unittest discover -s '<checkout>/tests' -p 'test_contracts.py' -v
```

실제 출력: Python `3.12.10`, 실행 파일은 지정 `.venv/Scripts/python.exe`, NumPy `2.3.5`, pandas `3.0.1`. 기존 계약은 `Ran 8 tests in 0.044s`, `OK`. 이 호출 묶음 종료 코드 0. 다른 저장소 테스트 파일은 실행하지 않았다.

### 별도 수정안 검사

```powershell
& '<checkout>/.venv/Scripts/python.exe' -B 'evals/reuse-20261023/answer/test_reuse.py'
```

수정 전 관찰 JSON은 1절 표와 일치했다. 실제 unittest 결과는 다음 11개 모두 `ok`, `Ran 11 tests in 0.085s`, `OK`, 프로세스 종료 코드 0이었다.

```text
test_actual_distance_no_timestamp_fill
test_average_bad_time_and_no_mutation
test_average_invalid_values_and_blocks
test_block_isolation
test_exact_window_edge_not_blind_wrapper
test_finite_clipping_regression_and_no_mutation
test_identity_invalid_before_cast
test_identity_valid_regression
test_nonfinite_clipping_rejected
test_other_block_mutation_both_directions
test_single_block_regression
```

### 공백 비교와 정답 변이 검사

```powershell
& '<checkout>/.venv/Scripts/python.exe' -B 'evals/reuse-20261023/answer/compare_gap.py'
```

별도 프로세스 종료 코드 0. 실제 JSON에서 `truth_daily_mean=10.0`, `remaining_count=18`, `remaining_daily_mean=10.0`, `bridge_supported=true`, `unmasked_input_rejected=true`, `hidden_truth_mutation_invariance=true`; 방법별 수치는 2절에 그대로 기록했다. 스크립트에는 10.0과 9.75에 대한 절대허용오차 1e-12 assertion도 있다. 스크립트는 파일을 쓰지 않고 stdout만 출력했다.

### 파일 식별

아래 7개 파일을 `Get-FileHash -Algorithm SHA256 -LiteralPath <7개 절대경로> | Format-List Path, Hash`로 읽어 실제 해시를 얻었다. 이 해시는 실행 뒤 식별자이며, 실행 전후 해시 대조를 했다는 뜻은 아니다. 원본/공개 저장소 보존 판단은 쓰기 도구의 대상 제한과 Python `-B`에 근거한다.

| 파일(위 경로 또는 answer/ 상대) | 실행 후 SHA256 |
|---|---|
| meter_candidate.py | `0059B54035D77BB2C38B5A87815FFD312D4639427DAC416B7FFA4BA57BBF0649` |
| gap-example.csv | `1C6A718475DABAEE519B48FCBD1C378FE2BE1FE37C19CE1D6A2B1F8078E9155E` |
| src/research_playbook/contracts.py | `61E71A1468F9D87C4729018E94787C5AEE0B73BB5AC3EBD488CF99EC5F7C861D` |
| cases/ocean-gap-repair/frozen/method.py | `6AE98FEB21786C52CCC15D7F344E2F340B2C3A2A1BBD5AD18E7D9FA5A7F3A5F0` |
| answer/meter_fixed.py | `047219081EE135151D860FD3F279E07C425056B69B5A740EE8659FA65CA6E897` |
| answer/test_reuse.py | `36B7F5A80342A0AEAB5ED2C4BB2457A2D3F6C57B95DB275E8B73E94FC4AC5540` |
| answer/compare_gap.py | `1E4F908C13514D482DE7B2BB50DB96475353979389DD0A7703262695C7D4ADE8` |

`Get-ChildItem -LiteralPath 'evals/reuse-20261023/answer' -Force | Select-Object Name, Length, Mode`도 실행했고, 당시 세 코드 파일은 각각 1757, 5555, 3039바이트였다. 인계 문서는 그 이후 추가했다.

## 5. 미실행·불필요 항목과 이해 범위

실행하지 않음: 설치, 네트워크, Git, 게시, 모델 학습, 실제 자료 읽기/재계산, 전체 저장소 테스트, 원 연구 replay, 다른 운영체제·다른 장비 실행, 실제 서비스 적용, 변경 코드의 원본 덮어쓰기. 별도 요청 없이는 이 시험을 완료했다는 이유로 수행하면 안 된다.

불필요해 생략함: 모든 플레이북/과거 이력 일괄 열람, 스킬 설치, 선택기와 임계값 조정, 새 실험 지점 탐색, 원자료 다운로드, 모델 성능 점수 만들기. `demo.py`는 함수 연결 확인용으로 읽었지만 같은 합성 개념을 별도 검사에서 직접 확인하므로 `demo` CLI 실행은 생략했다. 테스트 수를 생산성이나 실제 모델 품질 점수로 해석하지 않았다.

확인한 범위는 (a) 공개 README에서 요청에 맞는 최소 경로를 찾음, (b) 일부 재사용 함수가 원본 의미와 다름을 발견함, (c) 수정 전 결함과 수정 후 회귀/차단을 실제 실행함, (d) 가려진 정답을 분리한 동일 조건 합성 비교를 설명함이다. 실제 지점 일반화, 장기 재사용 생산성, 전체 저장소 정확성은 확인하지 않았다.

다음 사람이 계산을 재확인할 때는 위의 `test_reuse.py`와 `compare_gap.py` 두 명령만 다시 실행하면 된다. 원본에 적용하려면 `a,b,a` 반복 블록을 별도 구간 이름으로 관리한다는 정책을 먼저 확인해야 한다. 현재 요청 범위에서 남은 필수 작업은 없다.
