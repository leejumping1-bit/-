"""
FDA(US) 크롤러

대상: eCFR Title 21 Part 820 (Quality System Regulation) 일자별 비교
  https://www.ecfr.gov/compare/{YYYY-MM-DD}/to/{YYYY-MM-DD}/title-21/chapter-I/subchapter-H/part-820

eCFR은 공식 Compare API(JSON)를 제공하므로 HTML 스크레이핑보다 API 사용을 권장한다:
  https://www.ecfr.gov/api/versioner/v1/comparison/{date1}/{date2}/title-21.json?...

이 스캐폴드는 매월 1일 기준으로 "지난달 1일 대비 이번달 1일" 비교 URL을 생성해
변경 여부를 확인하는 최소 구현이다. 실제 조문 diff는 eCFR versioner API 응답을 파싱하여
common/diff_engine.py 로 넘겨야 한다 (TODO).
"""
import sys
import os
from datetime import date

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from common.http_utils import fetch  # noqa: E402

PART = "title-21/chapter-I/subchapter-H/part-820"
COMPARE_API = "https://www.ecfr.gov/api/versioner/v1/comparison/{d1}/{d2}/{part}.json"


def _first_of_month(y, m):
    return date(y, m, 1).isoformat()


def run(since_year=2026, since_month=1):
    """
    TODO(실사용 전 필수):
      - COMPARE_API 응답 스키마 확인 후 실제 changed=true 여부/변경 조항 파싱
      - 변경이 있는 경우에만 register.json 항목 생성
    """
    today = date.today()
    d1 = _first_of_month(since_year, since_month)
    d2 = today.isoformat()
    url = COMPARE_API.format(d1=d1, d2=d2, part=PART)

    res = fetch(url)
    items = []
    if not res.ok:
        return items, res

    # TODO: JSON 파싱 및 변경 조항 추출
    human_compare_url = f"https://www.ecfr.gov/compare/{d1}/to/{d2}/{PART}"
    items.append({
        "id": f"FDA-{d2.replace('-', '')}-QSR",
        "agency": "FDA",
        "agency_kr": "FDA(미국)",
        "published_date": None,   # TODO: 실제 변경일 파싱
        "effective_date": None,
        "publisher": "US FDA / eCFR",
        "reg_no": "21 CFR Part 820",
        "title": f"21 CFR Part 820 (QMSR) 비교 결과 확인 필요 ({d1} → {d2})",
        "summary": None,
        "scope": "종합",
        "sop_flag": False,
        "verified": False,
        "source_url": human_compare_url,
        "source_type": "direct",
        "fallback_url": "https://www.ecfr.gov/current/title-21/chapter-I/subchapter-H/part-820",
        "gap_id": None,
        "change_type": "확인필요",
    })
    return items, None


if __name__ == "__main__":
    found, block = run()
    print(f"수집 {len(found)}건")
