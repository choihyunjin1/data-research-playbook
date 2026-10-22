# 보관과 복구 범위

공개 Git 저장소와 비공개 원자료 복구 묶음은 서로 다릅니다.

## 원본 연구 묶음

로컬 `ocean-20261023` 보관 위치에 다음을 저장했습니다. 개인정보·대회 자산이 섞일 수 있으므로 공개하지 않습니다.

- `original-research.zip`: 연구 9단계, 신청 초안, 기존 개발 영역의 코드·결과·실패 기록.
- `baseline.json`: 파일 2,300개의 상대경로·크기·SHA-256과 제외 목록. 캐시·Git 작업 메타데이터·실행 환경 등은 제외했습니다.
- `restore-verification.json`: 별도 `restore-check/`에 실제 압축 해제하고 전 파일을 대조한 결과.
- `preservation-after.json`: 이관 후 원본의 추가·삭제·변경 여부 대조.

압축 크기 **242,710,774 bytes**, SHA-256:
`1b412b0c848979408bfa47898ab6e82673579b365de847c2a816034bad92701a`

복구할 때 빈 폴더에만 압축을 풀고 `baseline.json`과 파일별 크기·SHA를 대조합니다. 원 프로젝트 위에 곧바로 덮어쓰지 않습니다. 라이선스가 제한된 파일을 이 묶음에서 공개 저장소로 복사하지 않습니다.

## 공개 코드 이력

릴리스 태그와 모든 공개 Git ref를 별도 `data-research-playbook.bundle`에 보관하고, bundle에서 새 폴더로 clone해 커밋·트리·파일 목록을 비교합니다. `git bundle verify`와 `git fsck --full` 결과도 보관합니다. 릴리스 자산과 다운로드 검증 기록은 bundle 밖에 별도 저장합니다.

```powershell
git clone data-research-playbook.bundle restored-playbook
cd restored-playbook
git checkout v0.1.0
python scripts/package_manifest.py --verify
```

Git bundle은 GitHub 이슈·설정·릴리스 자산을 포함하지 않습니다. [GitHub 백업 지침](https://docs.github.com/en/repositories/archiving-a-github-repository/backing-up-a-repository)의 구분에 따릅니다. **다른 장치·클라우드의 원자료 백업은 미완료**입니다. 공개 코드의 원격 보관이 원자료의 이중 보관을 대신하지 않습니다.
