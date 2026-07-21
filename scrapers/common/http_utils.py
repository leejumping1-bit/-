"""
공통 HTTP 유틸리티
- 모든 크롤러가 공유하는 요청/재시도/차단 감지 로직
- MFDS 등 국내 사이트가 해외 IP(GitHub 호스팅 러너)를 차단하는 경우를 대비해
  실패 시 예외를 던지지 않고 '차단 추정' 상태를 반환하여, 전체 크롤링 파이프라인이
  중단되지 않도록 설계했습니다. (README.md의 Self-hosted Runner 안내 참고)
"""
import time
import requests

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8",
}


class FetchResult:
    def __init__(self, ok, status_code=None, text=None, blocked=False, error=None):
        self.ok = ok
        self.status_code = status_code
        self.text = text
        self.blocked = blocked   # 접속 차단으로 추정되는 경우 True
        self.error = error


def fetch(url, timeout=15, retries=2, backoff=2.0, session=None) -> FetchResult:
    """
    GET 요청. 실패해도 예외를 발생시키지 않고 FetchResult로 상태를 반환한다.
    타임아웃/커넥션 오류가 반복되면 blocked=True 로 표시 (국내 사이트의 해외 IP 차단 추정).
    """
    sess = session or requests
    last_err = None
    for attempt in range(retries + 1):
        try:
            resp = sess.get(url, headers=DEFAULT_HEADERS, timeout=timeout)
            if resp.status_code in (403, 999):
                return FetchResult(False, resp.status_code, blocked=True,
                                    error=f"HTTP {resp.status_code} (차단 추정)")
            resp.raise_for_status()
            resp.encoding = resp.apparent_encoding or resp.encoding
            return FetchResult(True, resp.status_code, resp.text)
        except requests.exceptions.Timeout as e:
            last_err = e
        except requests.exceptions.ConnectionError as e:
            last_err = e
            # 접속 자체가 거부되는 패턴은 차단 가능성이 높음
            if attempt == retries:
                return FetchResult(False, None, blocked=True, error=f"연결 실패(차단 추정): {e}")
        except requests.exceptions.RequestException as e:
            last_err = e
        time.sleep(backoff * (attempt + 1))
    return FetchResult(False, None, blocked=False, error=str(last_err))
