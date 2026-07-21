"""
Health Canada 크롤러
대상: https://laws-lois.justice.gc.ca/eng/regulations/sor-98-282/  (Medical Devices Regulations SOR/98-282)

justice.gc.ca 법령 사이트는 각 조문 페이지 하단에 "Current to / Last amended" 날짜가 표기되고,
과거 버전(비교 가능한 버전) 목록도 제공한다. 사용자가 GAP 분석 참고 사이트로 제시한
CanLII(webdiff)와 동일한 취지로, justice.gc.ca 의 버전별 비교도 가능하다.
"""
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from common.http_utils import fetch  # noqa: E402

try:
    from bs4 import BeautifulSoup
except ImportError:
    BeautifulSoup = None

REGULATION_URL = "https://laws-lois.justice.gc.ca/eng/regulations/sor-98-282/"


def run(since_year=2026, since_month=1):
    """TODO(실사용 전 필수): 'Current to' 날짜 파싱, 이전 버전과의 diff는 CanLII webdiff 방식 참고."""
    if BeautifulSoup is None:
        raise RuntimeError("beautifulsoup4 미설치")

    res = fetch(REGULATION_URL)
    items = []
    if not res.ok:
        return items, res

    soup = BeautifulSoup(res.text, "html.parser")
    current_to = soup.find(string=lambda s: s and "Current to" in s)

    items.append({
        "id": f"HC-SOR98282-{abs(hash(REGULATION_URL)) % 10000:04d}",
        "agency": "Health Canada",
        "agency_kr": "Health Canada(캐나다)",
        "published_date": None,  # TODO: current_to 문자열 정규화
        "effective_date": None,
        "publisher": "Justice Canada / Health Canada",
        "reg_no": "SOR/98-282",
        "title": f"Medical Devices Regulations (SOR/98-282) - 갱신 확인 필요 (페이지 표기: {current_to.strip() if current_to else 'N/A'})",
        "summary": None,
        "scope": "종합",
        "sop_flag": False,
        "verified": False,
        "source_url": REGULATION_URL,
        "source_type": "direct",
        "fallback_url": REGULATION_URL,
        "gap_id": None,
        "change_type": "확인필요",
    })
    return items, None


if __name__ == "__main__":
    found, block = run()
    print(f"수집 {len(found)}건")
