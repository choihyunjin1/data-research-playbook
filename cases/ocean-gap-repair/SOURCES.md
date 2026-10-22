# 공개 자료와 파일 식별자

이 연구는 예전 Ocean AI 대회의 배포 파일을 재사용하지 않았습니다. 아래 공개 자료에서 계산했으며 **원자료·원자료 행·제3자 소스는 이 저장소에 재배포하지 않습니다.** 저장된 작은 집계는 연구 결과이고, 자료 제공기관의 검증·채택을 뜻하지 않습니다.

## 이어도: KIOST 공개판 v1.1.1

- 자료: *Ieodo Ocean Research Station (I-ORS) observations of oceanic and atmospheric variables from 2004 to 2023*.
- 제공: 한국해양과학기술원(KIOST)·국립해양조사원(KHOA), Min Yong Chim 외. [제공기관 자료 페이지](https://sciwatch.kiost.ac.kr/handle/2020.kiost/46771), [DOI: 10.22808/DATA-2025-2](https://doi.org/10.22808/DATA-2025-2).
- 연구에 고정한 판: **v1.1.1**. 제공 페이지는 2026-01-16 라이선스 갱신과 CC BY 4.0을 명시합니다. 해당 페이지를 2026-10-23 다시 확인했습니다.
- 사용 변수는 시간 단위 수온입니다. 원 제품은 10분 자료를 품질관리·시간 집계한 것이므로 ‘매시간 직접 측정한 원시값’이라고 부르지 않습니다.
- [원본 ZIP](https://sciwatch.kiost.ac.kr/bitstream/2020.kiost/46771/8/ver1.1.1.zip): 1,949,744 bytes, SHA-256 `a754a4590158b24521f2a8a44335f66abfdb8f84648591f38147945e202886fc`.
- 사용 파일 `I-ORS_2004_2023_OCN_1hr.nc`: SHA-256 `55c81b0956f339f7a04f5b6e8cf771d82598e850a917c9e1022c17ffeca15df7`.

실험 1~4에서 선택한 수심·기간·일자 분모는 [연구 이력](HISTORY.md)에 있습니다. 자료 전체의 실제 결측 수와 정답을 가린 실험의 오차는 서로 다른 통계입니다. 제공 메타데이터에는 활용 알림 요청도 있습니다. 공식 v1.1.1 페이지의 공개 이용 조건은 출처 표시를 요구하는 CC BY 4.0이며, 이 저장소는 위 출처·버전·변경 범위를 표시합니다. 별도 활용 알림은 발송하지 않았고 제공기관의 승인·참여를 주장하지 않습니다.

## IMOS / AODN: National Reference Stations 시간 자료

IMOS의 Australian National Mooring Network 자료를 AODN의 공개 THREDDS에서 취득했습니다. 자료 파일의 라이선스는 **CC BY 4.0**입니다. IMOS는 NCRIS 지원을 받는 관측 인프라입니다. 제공기관·제품을 인용하되 결과의 보증이나 공동연구를 뜻하도록 쓰지 않습니다.

[IMOS 공식 제품 설명](https://imos.org.au/news/new-hourly-time-series-product-from-imos-moorings)에 따르면 시간 자료는 품질관리 상태를 구분한 시간 집계 제품이며, 모든 센서를 공통 수심으로 재격자화한 제품이 아닙니다. 같은 파일의 명목수심만 보고 동일한 수직 계류라고 가정하지 않고 기기·배치·위치를 확인합니다.

원본 식별자는 2026-10-22 연구 당시 취득 파일 기준입니다. 다음 표의 SHA와 bytes는 로컬 원본 식별값이지 원 제공기관이 발행한 전자서명은 아닙니다.

| 지점 / 연구 | 카탈로그 | 사용 파일 / bytes / SHA-256 |
|---|---|---|
| Maria Island / 3·4 | [NRSMAI](https://thredds.aodn.org.au/thredds/catalog/IMOS/ANMN/NRS/NRSMAI/hourly_timeseries/catalog.html) | `IMOS_ANMN-NRS_BOSTUZ_20080411_NRSMAI_FV02_hourly-timeseries_END-20260421_C-20260919.nc` · 73,044,828 bytes · `a156bdc40729a10a5f94e96f0367c23ccb795b5f944e1fbf8f2b0b5ac68c4d8c` |
| North Stradbroke / 5·7 | [NRSNSI](https://thredds.aodn.org.au/thredds/catalog/IMOS/ANMN/NRS/NRSNSI/hourly_timeseries/catalog.html) | `IMOS_ANMN-NRS_BOSTZ_20101213_NRSNSI_FV02_hourly-timeseries_END-20260106_C-20260510.nc` · 64,899,025 bytes · `9d9b59e2a0f6b8d58c44e82a27992366ac104884c2405c35aea3b81a6c17d0f5` |
| Rottnest / 6·7·9 | [NRSROT](https://thredds.aodn.org.au/thredds/catalog/IMOS/ANMN/NRS/NRSROT/hourly_timeseries/catalog.html) | `IMOS_ANMN-NRS_BOSTZ_20081120_NRSROT_FV02_hourly-timeseries_END-20260724_C-20260801.nc` · 142,539,740 bytes · `bc2b20d4181d8e0d95eae37ba04b3dc2e8e5a850b9617953df89de3254c30b84` |
| Kangaroo Island / 8 | [NRSKAI](https://thredds.aodn.org.au/thredds/catalog/IMOS/ANMN/NRS/NRSKAI/hourly_timeseries/catalog.html) | `IMOS_ANMN-NRS_BOSTZ_20080212_NRSKAI_FV02_hourly-timeseries_END-20260302_C-20260527.nc` · 349,738,532 bytes · `ac30ebe64bfe2b2a62077aecf87861c0536c9e27d6b39c032c1ff598d3e5af47` |

## 마지막 시험의 재계산 입력

직접 취득 주소는 [고정 NRSROT 파일](https://thredds.aodn.org.au/thredds/fileServer/IMOS/ANMN/NRS/NRSROT/hourly_timeseries/IMOS_ANMN-NRS_BOSTZ_20081120_NRSROT_FV02_hourly-timeseries_END-20260724_C-20260801.nc)입니다. 현재 replay는 이 파일 하나를 `--input-root` 바로 아래에서 읽습니다. 입력 색인·기간·명목수심은 [config/site.json](config/site.json)으로 고정합니다. 다운로드 주소가 사라지거나 최신 파일로 교체됐다면 새 파일을 같은 입력으로 간주하지 않습니다.

## 공개본에 남긴 변환

제공된 시간 집계 제품에서 고정한 기기·기간을 다시 추출한 뒤, 완전한 날짜에 인공 공백을 만들고 방법별 **일평균 복원 오차**를 재계산합니다. 제공기관의 고빈도 원측정 QC와 시간 평균 생성 과정을 다시 실행한 것은 아닙니다. 최종 추출은 fill 값·중복 관측을 제외하며 유한하지만 메타데이터 범위를 벗어난 값은 기존 연구와 같이 유지하고 개수를 기록합니다. UTC와 KST, 평가 구간과 앞뒤 선택 문맥은 각 연구의 조건을 따릅니다. 가린 정답은 평가에만 쓰며 선택기의 입력에서는 제외합니다.

공개본은 원본 연구 폴더를 통째로 복제하지 않습니다. 작은 집계·고정 함수·최종 설정을 선별하고 개인 경로를 제거했습니다. 각 파일의 원본/공개본 해시와 변환은 [이관 원장](../../provenance/migration.json)에 남깁니다. 이관 시 만든 해시는 과거 실험의 사전 고정을 새로 인증하지 않습니다.

자료의 CC BY 4.0은 [공식 라이선스](https://creativecommons.org/licenses/by/4.0/)에서 확인합니다. 제공자·자료명·버전·원 주소·변경 내용을 함께 남기며, 이 저장소의 MIT 코드 라이선스가 외부 자료 권리를 바꾸지는 않습니다.
