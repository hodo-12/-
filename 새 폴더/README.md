# OISH | 뜻밖의 조합

기존 브랜드 분석의 집계 결과를 탐색하는 Streamlit 1차 프로토타입입니다. 원본 댓글이나 분석 파이프라인을 실행하지 않습니다. API 키가 필요하지 않습니다.

**코드 배포 준비와 데이터 공개 승인은 별개입니다. 현재 패키지는 코드만 제공하며 실제 집계 데이터·댓글·검토 표본·데이터가 보이는 스크린샷을 포함하지 않습니다. GitHub 업로드와 클라우드 배포는 수행하지 않았습니다.**

## 구성

```
prototype_v1/
  app.py                    # 실행 진입점
  oish_data.py              # 검증, 검색, 원본 순위 조회
  requirements.txt          # 앱 의존성
  requirements-dev.txt      # 테스트 의존성
  README.md
  TEST_REPORT.md
  .gitignore
  .streamlit/config.toml
  data/
    README.md
    approval.example.json   # 승인되지 않은 빈 서식
  assets/style.css          # 직접 작성한 UI 스타일, 외부 이미지 없음
  tests/test_app.py
```

## 로컬 실행

검증 기준은 **Python 3.12**입니다. 새 환경에서도 같은 버전을 권장합니다. 의존성은 실제 실행에 사용한 버전으로 고정했습니다. Python은 requirements.txt에 넣지 않습니다.

프로젝트 폴더에서:

```bash
python -m venv .venv
# Windows PowerShell
.venv\Scripts\Activate.ps1
# macOS/Linux에서는 source .venv/bin/activate
python -m pip install -r requirements.txt
python -m streamlit run app.py --server.address 127.0.0.1
```

데이터가 없는 기본 실행은 **데이터 연결 대기 화면과 방법론**을 표시합니다. 가상의 통계나 추천 결과는 표시하지 않습니다. 앱은 실행 위치가 아닌 app.py의 위치를 기준으로 assets와 data를 찾습니다.

### 내부 시연 모드: 기존 실제 집계 결과 연결

프로젝트 밖에 있는 기존 분석 결과 폴더를 연결하세요. 데이터는 복사하지 않아도 됩니다. 아래 `../analysis_results`는 실제 파일이 있는 폴더로 바꾸는 상대경로 예시이며, 제공되는 폴더가 아닙니다. 상대경로의 기준은 prototype_v1입니다.

```powershell
$env:OISH_MODE = 'local_review'
$env:OISH_DATA_DIR = '../analysis_results'
python -m streamlit run app.py --server.address 127.0.0.1
```

```bash
# macOS/Linux
OISH_MODE=local_review OISH_DATA_DIR=../analysis_results python -m streamlit run app.py --server.address 127.0.0.1
```

앱은 이 폴더에서 다음 다섯 파일만 읽습니다. 원래 분석 폴더의 다른 파일은 읽지 않습니다.

| 파일 | 용도 |
|---|---|
| summary.json | 원시 행·고유 댓글·영상·브랜드 등 요약 |
| brand_quality.csv | 전체 브랜드 목록과 표본 수 |
| brand_image_rates.csv | 영상 동일 가중 이미지 비율 |
| brand_similarity.csv | 기존 이미지 코사인 유사도 행렬 |
| collaboration_ranking.csv | 기존 점수, 전체 순위, 공통·차별 이미지 |

내부 시연 모드는 인증 기능이 아닙니다. `127.0.0.1`에만 연결하고 공개 서버·터널·Community Cloud에서 사용하지 마세요. 앱에 표시되는 집계와 화면 캡처 역시 공개 승인 대상입니다.

## 기능과 해석

- 대시보드 수치는 연결된 summary.json에서 읽으며 코드에 하드코딩하지 않습니다.
- 전체 브랜드는 brand_quality.csv를 기준으로 검색합니다. 프로필이나 추천이 없는 브랜드도 검색할 수 있습니다.
- TOP 5는 해당 브랜드가 A 또는 B에 있는 기존 추천표를 점수순으로 최대 5개 조회합니다. 전체 순위와 브랜드별 순서는 다를 수 있습니다.
- A/B를 바꾸면 각 브랜드의 차별 이미지를 함께 뒤집습니다. 저장된 점수는 변경하지 않습니다.
- 추천표에 없는 조합은 점수를 새로 계산하지 않습니다. 저장된 유사도가 있으면 유사도만 보여주고, 이미지 접점은 두 프로필의 관측 여부로 표시합니다.
- 이미지 그래프는 CSV의 비율을 표시용으로만 100배 하여 %로 표현합니다. 여러 이미지가 동시에 언급될 수 있어 합계는 100%가 아닙니다.
- 파일 기준 산업군은 엄밀한 산업분류가 아닙니다. 해당 제한과 미검증 결과를 앱의 방법론에서 설명합니다.
- 파일 누락, 잘못된 숫자, 합계 불일치, 중복 키, 데이터 없음은 안내 메시지로 처리합니다. 원본 댓글·식별자 열이 있는 파일은 거부합니다.

## 환경 변수

| 변수 | 기본값 | 역할 |
|---|---|---|
| OISH_MODE | public | public 또는 local_review |
| OISH_DATA_DIR | 없음 | local_review에서만 필요. 프로젝트 외부의 집계 폴더 |
| OISH_TEST_DATA_DIR | 없음 | 실제 자료를 이용한 테스트에만 사용 |

public 모드는 OISH_DATA_DIR를 무시하고 프로젝트 내부 data/만 읽습니다. 비밀번호·API 키·개인정보를 환경 변수나 코드에 추가할 필요가 없습니다.

## GitHub에 올릴 파일

위 구성의 코드, 스타일, 테스트, 문서, 빈 데이터 안내 및 승인 서식만 올립니다. `data/*.csv`와 `data/*.json`은 기본적으로 Git에서 제외되며, 빈 `approval.example.json`만 예외입니다.

올리면 안 되는 항목:

- 원시 유튜브 댓글, 정제 댓글 본문, 작성자 정보, 댓글·영상 단위 내부 검토 자료
- internal_only/, human_review_sample.csv, 전체 분석 Notebook, 기존 분석 ZIP
- 승인되지 않은 집계표·그래프·화면 캡처·테스트 로그
- .env, secrets.toml, 키·비밀번호, 가상환경, 로컬 절대경로가 들어 있는 설정

`.gitignore`는 이미 추적된 파일을 삭제하지 않습니다. 업로드 전에 실제 변경 목록을 직접 검토하세요. 폴더 통째 드래그 업로드도 금지 파일을 자동 걸러주지 않습니다.

## 공개 데이터 승인과 연결

다음 항목은 수집 담당자와 권한 있는 검토자가 확인해야 합니다.

1. 수집 경로, 수집·갱신일, 플랫폼 약관 및 데이터 제공 계약의 적용 범위.
2. 댓글 파생 지표 생성, 서로 다른 채널·브랜드의 집계, 웹앱 표시 허용 범위.
3. 공개 GitHub 저장소에 집계 CSV를 재배포하는 권한과 Streamlit 서버에서 처리·보관하는 권한.
4. 경진대회 제출·발표·스크린샷 공개 허용 범위. 내부 시연 허가는 공개 허가와 다릅니다.
5. 보관 기간, 갱신·삭제·철회 대응 및 관련 문서의 책임자.
6. 브랜드명·상표와 연구 결과 표시의 적절성. 자동 분류 미검증과 연구 한계의 명시.

관련 정책 검토 출발점: [YouTube API 개발자 정책](https://developers.google.com/youtube/terms/developer-policies), [파생 지표·보관 추가 정책](https://developers.google.com/youtube/terms/derived-metrics-policy). 실제 수집 경로에 어떤 조건이 적용되는지는 아직 확인되지 않았습니다.

**실제 승인을 받은 뒤에만** 다섯 집계 파일을 data/에 넣고, approval.example.json을 approval.json으로 복사해 실제 승인자·일자·근거·허용 범위를 기록하세요. `public_release_approved`를 true로 바꾸는 행위 자체가 승인 취득은 아닙니다. 비공개 승인 증빙이나 연락처를 저장소에 넣지 말고 공개 가능한 참조 번호만 사용하세요.

`sha256`에는 다섯 파일명과 실제 SHA-256 해시를 기록합니다. 파일별 해시는 다음 방식으로 확인할 수 있습니다.

```bash
python -c "import hashlib; from pathlib import Path; p=Path('data/summary.json'); print(hashlib.sha256(p.read_bytes()).hexdigest())"
```

승인된 파일만 명시적으로 Git 추적 예외에 추가하세요. 앱은 승인 기록이 없거나 해시가 바뀌면 실제 집계를 표시하지 않습니다. 이 검사는 파일 대응 확인이며 법적 승인 검증이나 보안 인증 서비스는 아닙니다.

## Streamlit Community Cloud 배포 절차 — 이후 별도 환경에서 수행

1. GitHub에 위 코드 구조를 업로드하고 먼저 공개 데이터 권한을 확인합니다. 미승인 상태에서는 코드의 대기 화면만 실행할 수 있습니다.
2. 승인된 집계 파일과 승인 기록을 포함할지 검토합니다. private 저장소만으로 데이터 이용 문제가 해결되지는 않습니다.
3. Streamlit Community Cloud에서 Create app을 선택하고 저장소·브랜치를 지정합니다.
4. 프로젝트를 저장소 루트에 올렸다면 진입점은 **app.py**입니다. prototype_v1 하위 폴더를 유지했다면 **prototype_v1/app.py**를 선택합니다. requirements.txt는 app.py와 같은 디렉터리에 둡니다.
5. Advanced settings에서 **Python 3.12**를 선택합니다. 공개 실행에는 환경 변수·Secrets 설정이 필요 없습니다. `local_review` 설정이나 로컬 경로를 클라우드에 넣지 않습니다.
6. 배포한 별도 환경에서 설치 로그, 대기/정상 화면, 모든 기능, 모바일 레이아웃을 다시 확인합니다. Windows 로컬 테스트는 Linux 클라우드 실배포 검증을 대신하지 않습니다.

공식 문서: [배포 절차](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/deploy), [의존성 설정](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/app-dependencies).

## 테스트 재현

```bash
python -m pip install -r requirements-dev.txt
python -m pytest tests -q
```

실제 집계 파일 기반 테스트는 `OISH_TEST_DATA_DIR`에 집계 폴더를 지정하면 실행됩니다. 환경 변수가 없으면 해당 테스트는 건너뛰며 통과로 간주하지 않습니다. 테스트는 원본 CSV를 수정하지 않습니다. 자세한 실제 검증 결과는 TEST_REPORT.md를 참고하세요.

## 2차 발표 확장

- 수동 검증을 통과한 이미지 사전과 승인된 최신 집계 스냅샷으로 교체.
- 채널·광고·기간을 반영한 표집 비교와 추천 민감도 화면.
- 이미지 공통점과 차별점의 그래프, 승인된 이분 네트워크 탐색.
- 소비자 설문 기반 참신성·적합성 검증과 별도 실험 결과 연계.
- 접근 제어·승인 이력 관리·갱신 및 삭제 정책을 갖춘 내부 연구 운영 환경.
