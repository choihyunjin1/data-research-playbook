# v0.2.0 SaveTax 수집 사례 검수

검증일: 2026-10-23. 기준 커밋은 `d28017258531bae2611e2e00f0af3f2183c320ab`이다. 새 사례·합성 반례를 추가하므로 minor 버전으로 올렸다. 기존 릴리스·태그·당시 보고서는 수정하지 않는다. 이번 반영 자체가 새 GitHub 릴리스나 배포 자산 생성을 뜻하지 않는다.

## 직접 실행한 검사

| 검사 | 결과와 범위 |
|---|---|
| 공개 저장소 전체 회귀 | 76개 PASS, 실패·오류·skip 0. 기존 68개와 새 합성 8개다. Windows Python 3.12.14, numpy 2.3.5, pandas 3.0.1, netCDF4 1.7.4. [실행 receipt](unit-tests-v0.2.0.json) |
| 기존 demo | editable 설치 후 `python -m research_playbook demo` 정상 실행. [출력·보존 대조](savetax-validation-v0.2.0.json) |
| 새 합성 반례 | 공유 URL의 잘못된 연결만 격리, 최신 미확인 가격을 과거 값으로 대체하지 않음, 원문·이력 보존, 500+1 분할·고정 순서·중복·누락 검출. CLI의 3개 품목 행은 유지되고 fixture 비교 가능 행은 2→1→0 |
| 원프로젝트 선택 검사 | 수집 스케줄러·출처 연결·전체 가격 export 계약 검사 24개 PASS. 임시/합성 DB이며 실제 판매처 HTTP·운영 DB 쓰기 없음. 전체 운영 수집기 검사나 실환경 재수집으로 확대하지 않음 |
| 독립 문서 검토 | 집계 시점·분모, 출처 용량과 API 예산의 차이, 공개 범위를 검토했다. 전환율의 코호트·기간 조건과 요청 순서 커서의 적용 범위를 좁혔다. 합성 구현 범위 검토에서 공개 차단 사유 없음 |

공개 저장소 실행은 프로젝트 가상환경에 `python -m pip install -e ".[replay]"`로 지정 의존성을 설치한 뒤 수행했다. venv는 기존 numpy·pandas를 읽고 replay 의존성을 자체 설치했다. 글로벌 환경은 수정하지 않았다. `scripts/run_checks.py --output reports/unit-tests-v0.2.0.json`은 unittest discovery를 실행해 결과를 남긴다. 원프로젝트 선택 검사는 `PYTHONPATH=tests` 상태에서 `python -m unittest tests.test_merchant_capacity_scheduling tests.test_source_associations tests.test_full_price_export -v`로 실행했다.

## 초기 실패와 수정 조건

- 원프로젝트 첫 실행은 형제 test 모듈을 찾지 못해 19개 보고 중 오류 2개가 발생했다. 테스트 import 경로만 바로잡은 뒤 같은 선택 모듈의 24개 검사가 통과했다. 구현 수정으로 해결했다고 기록하지 않는다.
- 공개 저장소 첫 실행은 netCDF4 미설치로 기존 replay 모듈 import에 실패했다. 36개 보고 중 오류 1개였다. 선언된 replay 의존성을 프로젝트 venv에 설치한 뒤 전체 76개가 통과했다. 초기 실패 요약은 [별도 receipt](savetax-validation-v0.2.0.json)의 `initial_attempts`에 보존하며 개인 경로가 들어간 원시 traceback은 공개하지 않는다.

## 기존 기록과 공개 범위

기준 커밋의 기존 파일 중 이번 명시적 변경 경로를 제외한 138개 파일은 바이트 단위 대조에서 불일치 0개였다. 경로별 SHA는 [보존 대조](savetax-validation-v0.2.0.json)에 있다. Ocean·합성 자전거 사례, 과거 평가·보고서, 기존 알고리즘·검사는 바꾸지 않았다. 공통 지침에는 기존 원칙을 복제하는 대신 이번 사례 근거를 연결했다.

권리는 2026-10-23 데이터셋 공식 안내를 무인증으로 다시 확인했다. 원자료 재배포는 제외하고 직접 작성한 설명·선별 운영 집계·합성 코드만 선정했다. 응답 URL·SHA와 관측의 한계는 [사례 집계](../cases/savetax-crawler/evidence-summary.json)에 있다. 원문을 공개하지 않은 지문은 독립적인 과거 수집 재현이나 법적 권리 인증이 아니다.

파일별 선정은 `provenance/PUBLIC_FILES.json`, 현재 바이트는 `PUBLIC_MANIFEST.json`에 기록했다. stage 후 공개 목록 156개 경로·인식 가능한 개인정보/인증정보 패턴·로컬 링크 검사는 오류 0개였고, manifest는 자신을 제외한 155개 파일 대조를 통과했다. 문구 수정 후에는 재생성·재검증한다. 이 검사도 공개 권리의 진위나 모든 비밀정보 부재를 보증하지 않는다. 원격 반영·CI는 push 후 해당 커밋의 GitHub Actions 결과로 확인하며 로컬 PASS를 원격 PASS로 대신하지 않는다.

## 미실행·보류

- 새로운 판매처 요청·가격 재조사·점수 제출, 987,050행 원자료 재계산, 외부 가격 전수검증은 하지 않았다. 수집 자동화는 삭제하고 서비스는 drain 후 종료했다.
- 운영 수집기 전체와 사이트별 adapter는 외부 의존성·권리·서비스 설정의 별도 공개 검토 전까지 로컬에 보존한다. 공개 예제는 핵심 상태 경계의 작은 재현이다.
- 조달 원본·대형 CSV·판매처 HTML/이미지/규격서·계정 화면·인증정보·상품별 제출 자료는 반입하지 않았다.
- 장기 가격 수율·전체 수집 ETA·AI 성능/생산성 향상·실제 점수 성과는 입증하지 않았다. 단기 요청 속도를 같은 조건의 인과 효과로 해석하지 않는다.
