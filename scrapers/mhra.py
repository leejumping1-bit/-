"""
MHRA(UK) 크롤러

대상 페이지 (요청서 기준):
  - https://www.gov.uk/guidance/regulating-medical-devices-in-the-uk
  - https://www.legislation.gov.uk/uksi/2002/618/contents  (UK MDR 2002)
  - https://www.gov.uk/search/news-and-communications  (뉴스/공지 검색 - 필터 파라미터로 MHRA 한정 가능)

gov.uk 는 Content API(JSON)를 공개 제공한다: https://www.gov.uk/api/content{path}
legislation.gov.uk 도 변경이력(changes) API를 제공한다.
이 스캐폴드는 gov.uk 검색 페이지를 1차 대상으로 한다.
"""
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from common.http_utils import fetch  # noqa: E402

try:
    from bs4 import BeautifulSoup
except ImportError:
    BeautifulSoup = None

SEARCH_URL = "https://www.gov.uk/search/news-and-communications?organisations%5B%5D=medicines-and-healthcare-products-regulatory-agency&order=updated-newest"
LEGISLATION_URL = "https://www.legislation.gov.uk/uksi/2002/618/contents"


def run(since_year=2026, since_month=1):
    """
    TODO(실사용 전 필수):
      - gov.uk 검색 결과의 실제 DOM(.gem-c-document-list) 셀렉터 확인
      - legislation.gov.uk 의 "Changes to legislation" 섹션에서 발효 예정 개정 파싱
    """
    if BeautifulSoup is None:
        raise RuntimeError("beautifulsoup4 미설치")

    res = fetch(SEARCH_URL)
    items = []
    if not res.ok:
        return items, res

    soup = BeautifulSoup(res.text, "html.parser")
    for a in soup.select("a.gem-c-document-list__item-title, a[data-track-category]"):
        title = a.get_text(strip=True)
        href = a.get("href")
        if not title or not href:
            continue
        url = href if href.startswith("http") else "https://www.gov.uk" + href
        items.append({
            "id": f"MHRA-{abs(hash(url)) % 100000:05d}",
            "agency": "MHRA",
            "agency_kr": "MHRA(영국)",
            "published_date": None,  # TODO: 목록의 날짜 메타 파싱
            "effective_date": None,
            "publisher": "MHRA",
            "reg_no": None,
            "title": title,
            "summary": None,
            "scope": "종합",
            "sop_flag": False,
            "verified": False,
            "source_url": url,
            "source_type": "direct",
            "fallback_url": "https://www.gov.uk/guidance/regulating-medical-devices-in-the-uk",
            "gap_id": None,
            "change_type": "확인필요",
        })
    return items, None


if __name__ == "__main__":
    found, block = run()
    print(f"수집 {len(found)}건")
