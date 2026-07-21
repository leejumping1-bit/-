"""
TGA(호주) 크롤러
대상: https://www.tga.gov.au/products/medical-devices/overview/australian-regulatory-guidelines-medical-devices-argmd
(ARGMD - Australian Regulatory Guidelines for Medical Devices)
"""
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from common.http_utils import fetch  # noqa: E402

try:
    from bs4 import BeautifulSoup
except ImportError:
    BeautifulSoup = None

ARGMD_URL = "https://www.tga.gov.au/products/medical-devices/overview/australian-regulatory-guidelines-medical-devices-argmd"


def run(since_year=2026, since_month=1):
    """TODO(실사용 전 필수): TGA 페이지의 'Last updated/reviewed' 메타 태그 파싱, 하위 챕터 목록 순회."""
    if BeautifulSoup is None:
        raise RuntimeError("beautifulsoup4 미설치")

    res = fetch(ARGMD_URL)
    items = []
    if not res.ok:
        return items, res

    soup = BeautifulSoup(res.text, "html.parser")
    updated_meta = soup.select_one('[class*="updated"], time')
    last_updated = updated_meta.get_text(strip=True) if updated_meta else None

    items.append({
        "id": f"TGA-ARGMD-{abs(hash(ARGMD_URL)) % 10000:04d}",
        "agency": "TGA",
        "agency_kr": "TGA(호주)",
        "published_date": None,  # TODO: last_updated 문자열을 YYYY-MM-DD 로 정규화
        "effective_date": None,
        "publisher": "Therapeutic Goods Administration",
        "reg_no": "ARGMD",
        "title": f"Australian Regulatory Guidelines for Medical Devices (ARGMD) - 갱신 확인 필요 (페이지 표기: {last_updated})",
        "summary": None,
        "scope": "종합",
        "sop_flag": False,
        "verified": False,
        "source_url": ARGMD_URL,
        "source_type": "direct",
        "fallback_url": ARGMD_URL,
        "gap_id": None,
        "change_type": "확인필요",
    })
    return items, None


if __name__ == "__main__":
    found, block = run()
    print(f"수집 {len(found)}건")
