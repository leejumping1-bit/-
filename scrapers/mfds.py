"""
MFDS(식품의약품안전처) 크롤러

대상 게시판 (요청서 기준):
  - m_203 : 법/시행령/시행규칙            https://www.mfds.go.kr/brd/m_203/list.do
  - m_211 : 고시/훈령/예규 전문           https://www.mfds.go.kr/brd/m_211/list.do
  - m_212 :                              https://www.mfds.go.kr/brd/m_212/list.do
  - m_215 : 고시훈령예규                 https://www.mfds.go.kr/brd/m_215/list.do
  - m_207 : 제개정고시등                 https://www.mfds.go.kr/brd/m_207/list.do
  - m_209 : 입법/행정예고                https://www.mfds.go.kr/brd/m_209/list.do
  - m_1087: 법률 제개정 현황              https://www.mfds.go.kr/brd/m_1087/list.do

MFDS 게시판은 eGovFrame 기반이지만 <table>이 아닌 <div class="bbs_list01"> > <ul> > <li>
구조를 사용한다. 각 <li> 안에:
  - <div class="num">     : 글 번호
  - <div class="center_column"> : 제목(<a class="title">) + 메타(<div class="winfo">)
  - <div class="right_column">  : 등록일(YYYY-MM-DD)

m_203 게시판의 경우 <a> href가 law.go.kr 등 외부 링크인 경우가 있어
view.do 셀렉터만으로는 수집 불가 → a.title 셀렉터를 사용한다.
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

BOARDS = {
    "law_rule": "https://www.mfds.go.kr/brd/m_203/list.do",
    "notice_full_text": "https://www.mfds.go.kr/brd/m_211/list.do",
    "board_212": "https://www.mfds.go.kr/brd/m_212/list.do",
    "notice_order": "https://www.mfds.go.kr/brd/m_215/list.do",
    "enact_amend": "https://www.mfds.go.kr/brd/m_207/list.do",
    "pre_announce": "https://www.mfds.go.kr/brd/m_209/list.do",
    "law_status": "https://www.mfds.go.kr/brd/m_1087/list.do",
}

DATE_RE = re.compile(r"(20\d{2})[-.](\d{1,2})[-.](\d{1,2})")


def _normalize_date(text):
    m = DATE_RE.search(text or "")
    if not m:
        return None
    y, mo, d = m.groups()
    return f"{y}-{int(mo):02d}-{int(d):02d}"


def _extract_date_from_li(li):
    """
    <li> 안에서 등록일을 추출한다. 두 가지 위치를 시도:
      1) <div class="right_column"> 텍스트 (대부분의 게시판)
      2) <div class="winfo"> > <p> 안의 날짜 패턴 (일부 게시판)
    """
    # 1차: right_column
    right = li.select_one(".right_column")
    if right:
        date = _normalize_date(right.get_text(strip=True))
        if date:
            return date

    # 2차: winfo 내 p 태그에서 날짜 패턴 탐색
    winfo = li.select_one(".winfo")
    if winfo:
        for p in winfo.select("p"):
            text = p.get_text(strip=True)
            date = _normalize_date(text)
            if date:
                return date

    # 3차: li 전체 텍스트에서 fallback
    return _normalize_date(li.get_text(" ", strip=True))


def _extract_winfo_fields(li):
    """winfo 메타데이터(고시번호, 담당부서 등) 추출."""
    fields = {}
    winfo = li.select_one(".winfo")
    if not winfo:
        return fields
    for p in winfo.select("p"):
        text = p.get_text(" ", strip=True)
        # "라벨 | 값" 패턴
        parts = re.split(r"\s*\|\s*", text, maxsplit=1)
        if len(parts) == 2:
            key, val = parts[0].strip(), parts[1].strip()
            fields[key] = val
    return fields


def crawl_board(board_key, board_url, since_year=2026, since_month=1, max_pages=3):
    """
    목록 페이지를 순회하며 게시글 메타(제목/등록일/링크)를 수집한다.

    MFDS 게시판은 <div class="bbs_list01"> > <ul> > <li> 구조를 사용하며,
    각 게시글 <li>에는 <a class="title"> 링크가 있다.
    m_203의 경우 href가 law.go.kr 등 외부 사이트일 수 있다.
    첨부파일 <li>는 <a class="title">이 없어 자동으로 건너뛴다.
    """
    if BeautifulSoup is None:
        raise RuntimeError("beautifulsoup4 가 설치되어 있지 않습니다. requirements.txt 참고")

    results = []
    for page in range(1, max_pages + 1):
        url = f"{board_url}?page={page}"
        res = fetch(url)
        if not res.ok:
            return results, res  # blocked 여부는 호출자가 판단

        soup = BeautifulSoup(res.text, "html.parser")
        bbs_list = soup.select_one(".bbs_list01")
        if not bbs_list:
            # bbs_list01이 없으면 해당 게시판 구조가 다를 수 있음
            break

        rows_found = 0
        for li in bbs_list.select("li"):
            # 게시글 <li>인지 확인 (a.title이 있어야 함)
            a = li.select_one("a.title")
            if not a:
                continue

            title = a.get_text(strip=True)
            if not title or len(title) < 4:
                continue

            href = a.get("href", "")
            # URL 정규화
            if href.startswith("http"):
                view_url = href
            elif href.startswith("./") or href.startswith("view.do"):
                base = board_url.rsplit("/", 1)[0]
                view_url = base + "/" + href.lstrip("./")
            else:
                view_url = href

            # 날짜 추출 (right_column 우선, winfo fallback)
            pub_date = _extract_date_from_li(li)

            # since 필터
            if pub_date:
                y, mo = int(pub_date[:4]), int(pub_date[5:7])
                if (y, mo) < (since_year, since_month):
                    continue

            # winfo 메타데이터 추출
            winfo = _extract_winfo_fields(li)

            results.append({
                "board": board_key,
                "title": title,
                "view_url": view_url,
                "list_url": board_url,
                "published_date_guess": pub_date,
                "winfo": winfo,
            })
            rows_found += 1

        if rows_found == 0:
            break
    return results, None


def run(since_year=2026, since_month=1):
    """
    모든 MFDS 게시판을 크롤링하여 register.json items 스키마로 변환한다.

    반환: (items: list[dict], blocked_boards: list[str])
    - blocked_boards는 접속 차단된 게시판 키 목록 (빈 리스트이면 차단 없음)

    TODO(실사용 전 필수):
      1) 각 view_url 상세 페이지에서 고시번호/시행일/첨부 원문(hwpx, pdf)을 추가로 파싱
      2) scope(적용범위: 일반의료기기/이식형/디지털/체외진단/종합/기타)를 제목·본문 키워드로 자동 분류
         (아래 SCOPE_KEYWORDS 참고 - 필요시 고도화)
      3) SOP 반영 필요(★) 여부는 1차로 키워드 규칙 적용 후, 필요시 LLM 요약(Anthropic API) 연동 권장
    """
    items = []
    blocked_boards = []

    for key, url in BOARDS.items():
        rows, block_info = crawl_board(key, url, since_year, since_month)
        if block_info and block_info.blocked:
            blocked_boards.append(key)
            continue
        for r in rows:
            items.append(_to_register_item(r))

    return items, blocked_boards


SCOPE_KEYWORDS = {
    "체외진단": "체외진단",
    "디지털의료기기": "디지털",
    "이식형": "이식형",
}


def _guess_scope(title):
    for scope, kw in SCOPE_KEYWORDS.items():
        if kw in title:
            return scope
    return "종합"


def _guess_sop_flag(title):
    # 심사원 관점 1차 규칙: 시행규칙/기준/GMP/품질 관련 키워드는 SOP 영향 가능성 높음
    keywords = ["시행규칙", "품질관리", "기준", "GMP", "허가", "인증", "심사"]
    return any(k in title for k in keywords)


def _to_register_item(row):
    title = row["title"]
    pub = row.get("published_date_guess")
    winfo = row.get("winfo", {})
    reg_no = winfo.get("고시번호") or winfo.get("법률번호")

    item_id = f"MFDS-{(pub or 'UNKNOWN').replace('-', '')}-{abs(hash(row['view_url'])) % 10000:04d}"
    return {
        "id": item_id,
        "agency": "MFDS",
        "agency_kr": "식품의약품안전처(한국)",
        "published_date": pub,
        "effective_date": None,  # 상세 페이지 파싱 필요 (TODO)
        "publisher": winfo.get("담당부서", "식품의약품안전처"),
        "reg_no": reg_no,        # winfo에서 추출, 상세 페이지에서 보완 필요 (TODO)
        "title": title,
        "summary": None,         # 상세 파싱 + 자동요약 로직 필요 (TODO)
        "scope": _guess_scope(title),
        "sop_flag": _guess_sop_flag(title),
        "verified": False,       # 상세 파싱으로 필드가 채워지기 전까지는 미검증으로 표기
        "source_url": row["view_url"],
        "source_type": "direct",
        "fallback_url": row["list_url"],
        "gap_id": None,
        "change_type": "확인필요",
    }


if __name__ == "__main__":
    found_items, blocked = run()
    print(f"수집 {len(found_items)}건, 차단된 게시판: {blocked}")
    # 날짜 파싱 통계
    with_date = sum(1 for it in found_items if it.get("published_date"))
    no_date = sum(1 for it in found_items if not it.get("published_date"))
    print(f"  날짜 있는 항목: {with_date}건, 날짜 없는 항목: {no_date}건")
    # 게시판별 분포
    from collections import Counter
    import re as _re
    boards = Counter()
    for it in found_items:
        m = _re.search(r"m_(\d+)", it.get("source_url") or it.get("fallback_url", ""))
        boards[m.group(0) if m else "unknown"] += 1
    print(f"  게시판별: {dict(boards)}")
