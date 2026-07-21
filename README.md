# 국내외 규격 및 가이던스 업데이트 검토대장 (Regulatory Watch Console)

의료기기 QA 담당자를 위한 **규격·규제 모니터링 웹사이트**입니다.
GitHub Pages(프론트) + GitHub Actions(월간 크롤러, 백엔드) 구조로 동작하며,
별도의 유료 서버 없이 GitHub 계정만으로 운영할 수 있도록 설계했습니다.

---

## 1. 지금 이 상태에서 할 수 있는 것 / 없는 것

**할 수 있는 것 (바로 동작)**
- `docs/` 폴더를 GitHub Pages로 배포하면 검토대장 · 요약 · Gap 분석 화면이 즉시 보입니다.
- 시드 데이터로 **실제로 검색·확인한** MFDS 3건, MDCG 1건(총 4건은 원문 링크까지 확인됨)과
  사용자가 제공했으나 제가 원문을 직접 재확인하지 못한 MFDS 2건(모두 링크·요약을
  비워두고 "미확인"으로 명시)이 들어 있습니다. **지어낸 수치나 조문 내용은 없습니다.**
- 월별 필터, 엑셀 다운로드, Gap 분석 화면(적/청 하이라이트, 동일구간 생략, N.A. 표기)은
  모두 실제로 동작합니다. Gap 분석 예시(`GAP-SAMPLE-FORMAT`)는 **형식 설명용 샘플**이라고
  화면에 명확히 표시되며 실제 규정 문구가 아닙니다.

**아직 안 되는 것 (배포 후 사용자가 완성해야 하는 부분)**
- 8개 기관 크롤러 코드는 전체 작성돼 있지만, 저는 이 환경에서 실제 크롤러를
  실행/검증할 네트워크 접근 권한이 없습니다. `scrapers/*.py` 안의 `TODO` 주석 부분
  (상세 페이지 파싱, 고시번호·시행일 추출, scope 자동분류 고도화)은 **실제 사이트에
  접속해 HTML 구조를 확인하며 완성**해야 합니다. 이건 요청하신 "거짓 데이터 절대 금지"
  원칙을 지키기 위해 제가 검증 못한 부분을 추정 코드로 채우지 않았기 때문입니다.
- MFDS를 제외한 7개 기관도 목록 페이지 진입은 되지만 상세 파싱은 TODO 상태입니다.

---

## 2. 폴더 구조

```
docs/                     ← GitHub Pages가 서빙하는 프론트엔드 (Settings > Pages > /docs)
  index.html
  style.css
  app.js
  data/
    register.json         ← 검토대장 데이터 (크롤러가 매월 갱신)
    gap/*.json             ← 항목별 Gap 분석 데이터

scrapers/                 ← 백엔드 크롤러 (Python)
  common/
    http_utils.py          ← 재시도/차단감지 공통 요청 함수
    diff_engine.py          ← 조문 diff → Gap 분석 JSON 변환 엔진
    register_io.py          ← register.json 읽기/쓰기/병합
  mfds.py / mdcg.py / fda.py / mhra.py / mdsap.py / tga.py
  health_canada.py / pmda.py
  run_all.py               ← 전체 크롤러 실행 오케스트레이터

.github/workflows/monthly-crawl.yml   ← 매월 1일 자동 실행
requirements.txt
```

---

## 3. GitHub Pages 배포

1. 이 폴더 전체를 GitHub 저장소에 push
2. 저장소 **Settings → Pages → Build and deployment → Branch: main, Folder: /docs** 선택
3. 몇 분 후 `https://<계정>.github.io/<저장소명>/` 접속

---

## 4. MFDS 접속 차단 문제 — Self-hosted Runner 등록 방법

말씀하신 대로 GitHub Actions의 기본 러너는 해외(주로 미국) IP를 사용하므로
식약처 등 국내 사이트가 차단할 가능성이 있습니다. 아래 순서로 **한국에 있는
PC 또는 서버를 GitHub Actions 러너로 등록**하면, MFDS 크롤링만 그 PC에서 실행됩니다.

1. GitHub 저장소 → **Settings → Actions → Runners → New self-hosted runner**
2. 운영체제 선택 후 안내되는 명령어를 한국 소재 PC/서버(상시 켜져 있어야 함)에서 실행
   (`./config.sh --url ... --token ...` → `./run.sh`)
3. 등록 시 **Label에 `korea` 추가** (워크플로우의 `runs-on: [self-hosted, korea]` 와 매칭)
4. Python 3.11 및 `pip install -r requirements.txt` 를 해당 PC에 설치
5. 이후 `crawl-mfds` 잡은 자동으로 이 PC에서만 실행됩니다.

> Self-hosted runner는 **무료**이지만 해당 PC/서버가 크롤링 시각(매월 1일 09:10 KST)에
> 켜져 있고 인터넷에 연결돼 있어야 합니다. 상시 운영이 부담스럽다면 대안으로
> (a) 한국 리전 프록시 서비스를 `http_utils.py`의 `fetch()`에 연동하거나,
> (b) 차단 감지 시 관리자에게 알림을 보내고 수동으로 자료를 업로드하는 방식을
> 병행할 수 있습니다. 두 방식 모두 `common/http_utils.py`의 `FetchResult.blocked`
> 플래그를 기준으로 쉽게 확장할 수 있게 설계했습니다.

---

## 5. 로컬 테스트

```bash
pip install -r requirements.txt
python scrapers/run_all.py --only mdcg      # 기관 하나만 테스트
python scrapers/run_all.py                  # 전체 실행 (MFDS는 한국 네트워크에서만 성공 가능성 높음)
```

프론트만 로컬에서 확인하려면 `docs/` 폴더에서 `python -m http.server 8000` 후
`http://localhost:8000` 접속 (또는 VSCode Live Server 등 사용).

---

## 6. 검토대장 컬럼 ↔ 심사원 관점 자동 판단 로직

| 컬럼 | 채우는 방식 |
|---|---|
| 적용범위 | 제목 키워드 1차 분류(`scrapers/mfds.py`의 `SCOPE_KEYWORDS`) → 일반의료기기/체내이식형/디지털의료기기/체외진단/종합/기타 |
| SOP(★) | 1차 키워드 규칙(`_guess_sop_flag`)으로 시행규칙·GMP·품질기준 등 핵심 규정 여부 판정. 정확도를 높이려면 Anthropic API(Claude)로 본문을 요약·판단하도록 `run_all.py`에 후처리 단계를 추가하는 것을 권장합니다(코드에 연동 지점 주석 표시). |
| 내용요약 | 현재는 사람이 직접 검증한 문장만 채워져 있습니다. 자동요약을 붙이려면 상세 본문 파싱 후 LLM 요약 호출을 `mfds.py` 등의 TODO 지점에 추가하세요. |

---

## 7. Gap 분석 방식

`scrapers/common/diff_engine.py`가 CanLII(webdiff) 스타일로:
- 동일 문장 구간은 `⋯ 동일 내용 생략 ⋯`으로 접기
- 삭제된 문장은 빨간색 취소선
- 추가/변경된 문장은 파란색 강조
- 신규 제정 조항은 개정 전을 `N.A.`로 표기

을 자동 생성합니다. 실제로 쓰려면 기관별 스크래퍼에서 **개정 전/후 조문 원문 텍스트**를
확보해 `build_gap_document(...)`에 넘기는 부분만 완성하면 됩니다(현재는 자리표시 상태).

---

## 8. 정직성 원칙 (중요)

이 프로젝트는 "거짓 데이터 반영 금지" 요구사항을 지키기 위해 다음을 지켰습니다.
- 제가 직접 웹 검색으로 원문을 확인한 항목만 `verified: true`로 표시
- 사용자가 제공했지만 제가 재확인하지 못한 항목은 `verified: false` + 요약/시행일을
  비워두고 화면에 "미확인" 배지로 노출
- Gap 분석 샘플은 실제 규정처럼 보이지 않도록 조문번호를 "(예시)"로 표기하고
  화면 상단에 경고 문구를 고정 표시
- 크롤러가 아직 파싱하지 못하는 상세 필드는 `null`로 두었으며 임의의 값으로 채우지 않았습니다
