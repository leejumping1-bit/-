"""
MDCG(EU) 크롤러

대상 페이지 (요청서 기준):
  - https://health.ec.europa.eu/medical-devices-sector/latest-updates_en
  - https://health.ec.europa.eu/medical-devices-new-regulations_en
  - https://health.ec.europa.eu/medical-devices-sector/directives_en
  - https://health.ec.europa.eu/medical-devices-eudamed_en

EU 사이트는 국내 사이트와 달리 접속 차단 위험이 낮으나(IP 차단 이슈는 주로 MFDS 등
국내 사이트에 한정됨), 페이지가 Drupal 기반이라 목록 구조가 자주 바뀔 수 있다.
'latest-updates_en' 페이지는 날짜별 업데이트 목록(예: "20 APRIL 2026 ...")을 제공하므로
이 페이지를 1차 수집 대상으로 삼는다.

검증된 예시(2026-04-20): MDCG 2021-24 rev.1 Guidance on classification of medical devices
  https://health.ec.europa.eu/latest-updates/update-mdcg-2021-24-rev1-guidance-classification-medical-devices-april-2026-2026-04-20_en
"""
import re
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from common.http_utils import fetch  # noqa: E402

try:
    from bs4 import BeautifulSoup
except ImportError:
    BeautifulSoup = None

LATEST_UPDATES_URL = "https://health.ec.europa.eu/latest-updates_en"

# 이 페이지는 DG SANTE(EU 보건총국) 전체 소식(제약/원헬스 등 포함) 피드이므로,
# 의료기기와 무관한 항목을 걸러내기 위한 최소 키워드 필터.
# TODO(실사용 전 필수): 오탐/누락 여부를 실제 운영하며 키워드를 보강할 것.
MEDICAL_DEVICE_KEYWORDS = [
    "medical device", "medical devices", "in vitro diagnostic", "ivdr", "mdr",
    "mdcg", "notified bod", "eudamed", "udi", "emdn",
]


def _is_medical_device_related(text: str) -> bool:
    t = (text or "").lower()
    return any(kw in t for kw in MEDICAL_DEVICE_KEYWORDS)

MONTHS = {
    "JANUARY": 1, "FEBRUARY": 2, "MARCH": 3, "APRIL": 4, "MAY": 5, "JUNE": 6,
    "JULY": 7, "AUGUST": 8, "SEPTEMBER": 9, "OCTOBER": 10, "NOVEMBER": 11, "DECEMBER": 12,
}
DATE_RE = re.compile(r"(\d{1,2})\s+([A-Z]+)\s+(20\d{2})")


def _parse_date(text):
    m = DATE_RE.search((text or "").upper())
    if not m:
        return None
    d, mon, y = m.groups()
    mo = MONTHS.get(mon)
    if not mo:
        return None
    return f"{y}-{mo:02d}-{int(d):02d}"


def run(since_year=2026, since_month=1):
    """
    TODO(실사용 전 필수):
      - 상세 페이지에서 실제 MDCG 문서번호(예: MDCG 2021-24 rev.1)와 PDF 링크 추출
      - PDF 본문에서 조항 단위 텍스트를 추출해 diff_engine.build_gap_document 로 전달
    """
    if BeautifulSoup is None:
        raise RuntimeError("beautifulsoup4 미설치")

    res = fetch(LATEST_UPDATES_URL)
    if not res.ok:
        return [], res

    soup = BeautifulSoup(res.text, "html.parser")
    items = []
    for a in soup.select("a[href]"):
        title = a.get_text(strip=True)
        href = a.get("href")
        if not title or len(title) < 8 or not href:
            continue
        container_text = a.find_parent().get_text(" ", strip=True) if a.find_parent() else ""
        if not _is_medical_device_related(title) and not _is_medical_device_related(container_text):
            continue
        pub_date = _parse_date(container_text) or _parse_date(title)
        if not pub_date:
            continue
        y, mo = int(pub_date[:4]), int(pub_date[5:7])
        if (y, mo) < (since_year, since_month):
            continue
        url = href if href.startswith("http") else "https://health.ec.europa.eu" + href
        items.append({
            "id": f"MDCG-{pub_date.replace('-', '')}-{abs(hash(url)) % 10000:04d}",
            "agency": "MDCG",
            "agency_kr": "MDCG(EU)",
            "published_date": pub_date,
            "effective_date": None,
            "publisher": "European Commission - MDCG",
            "reg_no": None,  # TODO: 상세 페이지에서 MDCG 번호 파싱
            "title": title,
            "summary": None,
            "scope": "종합",
            "sop_flag": True,
            "verified": False,
            "source_url": url,
            "source_type": "direct",
            "fallback_url": LATEST_UPDATES_URL,
            "gap_id": None,
            "change_type": "확인필요",
        })
    return items, None


if __name__ == "__main__":
    found, block = run()
    print(f"수집 {len(found)}건")
