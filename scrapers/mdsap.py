"""
MDSAP 크롤러
대상: https://www.mdsap.global/documents/library/audit-approach  (AU P0002 등 문서 라이브러리)

MDSAP 문서 라이브러리는 정적 목록에 가까워 갱신 빈도가 낮다.
문서 버전(Edition/Revision) 번호와 게시일을 목록에서 직접 파싱한다.
"""
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from common.http_utils import fetch  # noqa: E402

try:
    from bs4 import BeautifulSoup
except ImportError:
    BeautifulSoup = None

LIBRARY_URL = "https://www.mdsap.global/documents/library/audit-approach"


def run(since_year=2026, since_month=1):
    """TODO(실사용 전 필수): 실제 문서 목록 DOM 구조 확인 후 제목/버전/게시일 파싱."""
    if BeautifulSoup is None:
        raise RuntimeError("beautifulsoup4 미설치")

    res = fetch(LIBRARY_URL)
    items = []
    if not res.ok:
        return items, res

    soup = BeautifulSoup(res.text, "html.parser")
    for a in soup.select('a[href$=".pdf"], a[href*="document"]'):
        title = a.get_text(strip=True)
        href = a.get("href")
        if not title or len(title) < 6 or not href:
            continue
        url = href if href.startswith("http") else "https://www.mdsap.global" + href
        items.append({
            "id": f"MDSAP-{abs(hash(url)) % 100000:05d}",
            "agency": "MDSAP",
            "agency_kr": "MDSAP(AU P0002)",
            "published_date": None,
            "effective_date": None,
            "publisher": "MDSAP Consortium",
            "reg_no": None,
            "title": title,
            "summary": None,
            "scope": "종합",
            "sop_flag": False,
            "verified": False,
            "source_url": url,
            "source_type": "direct",
            "fallback_url": LIBRARY_URL,
            "gap_id": None,
            "change_type": "확인필요",
        })
    return items, None


if __name__ == "__main__":
    found, block = run()
    print(f"수집 {len(found)}건")
