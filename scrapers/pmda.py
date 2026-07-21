"""
PMDA(일본) 크롤러
대상: https://www.pmda.go.jp/english/review-services/regulatory-info/0004.html

PMDA 영문 페이지는 정기 개정이 드물고, 새 통지(notification)가 PDF 링크로 추가되는 방식이다.
"""
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from common.http_utils import fetch  # noqa: E402

try:
    from bs4 import BeautifulSoup
except ImportError:
    BeautifulSoup = None

PMDA_URL = "https://www.pmda.go.jp/english/review-services/regulatory-info/0004.html"


def run(since_year=2026, since_month=1):
    """TODO(실사용 전 필수): 목록 항목의 날짜 표기 형식(예: 'as of DD Month YYYY') 파싱 규칙 확정."""
    if BeautifulSoup is None:
        raise RuntimeError("beautifulsoup4 미설치")

    res = fetch(PMDA_URL)
    items = []
    if not res.ok:
        return items, res

    soup = BeautifulSoup(res.text, "html.parser")
    for a in soup.select('a[href$=".pdf"], a[href*="0004"]'):
        title = a.get_text(strip=True)
        href = a.get("href")
        if not title or len(title) < 6 or not href:
            continue
        url = href if href.startswith("http") else "https://www.pmda.go.jp" + href
        items.append({
            "id": f"PMDA-{abs(hash(url)) % 100000:05d}",
            "agency": "PMDA",
            "agency_kr": "PMDA(일본)",
            "published_date": None,
            "effective_date": None,
            "publisher": "Pharmaceuticals and Medical Devices Agency",
            "reg_no": None,
            "title": title,
            "summary": None,
            "scope": "종합",
            "sop_flag": False,
            "verified": False,
            "source_url": url,
            "source_type": "direct",
            "fallback_url": PMDA_URL,
            "gap_id": None,
            "change_type": "확인필요",
        })
    return items, None


if __name__ == "__main__":
    found, block = run()
    print(f"수집 {len(found)}건")
