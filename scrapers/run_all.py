"""
전체 8개 기관 크롤러를 실행하고 결과를 docs/data/register.json 에 병합한다.

실행 방법:
  python scrapers/run_all.py                # 전체 실행
  python scrapers/run_all.py --only mfds     # 특정 기관만 실행 (self-hosted runner용)

GitHub Actions에서는 두 개 잡(job)으로 나누어 실행한다 (.github/workflows/monthly-crawl.yml):
  - job "crawl-global": ubuntu-latest 러너 → MFDS를 제외한 7개 기관
  - job "crawl-mfds"   : self-hosted 러너(한국 소재 PC/서버) → MFDS만 실행
    (MFDS 등 국내 사이트가 해외 IP를 차단하는 문제 대응. README.md 참고)
"""
import argparse
import importlib
import sys
import os

sys.path.append(os.path.dirname(__file__))
from common import register_io  # noqa: E402

AGENCY_MODULES = {
    "mfds": "mfds",
    "mdcg": "mdcg",
    "fda": "fda",
    "mhra": "mhra",
    "mdsap": "mdsap",
    "tga": "tga",
    "health_canada": "health_canada",
    "pmda": "pmda",
}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--only", nargs="*", default=None,
                         help="특정 기관만 실행 (예: --only mfds mdcg)")
    parser.add_argument("--since-year", type=int, default=2026)
    parser.add_argument("--since-month", type=int, default=1)
    args = parser.parse_args()

    targets = args.only or list(AGENCY_MODULES.keys())

    register = register_io.load_register()
    all_new_items = []
    summary = {}

    for key in targets:
        mod_name = AGENCY_MODULES.get(key)
        if not mod_name:
            print(f"[SKIP] 알 수 없는 기관 키: {key}")
            continue
        try:
            mod = importlib.import_module(mod_name)
        except Exception as e:
            print(f"[ERROR] {key} 모듈 로드 실패: {e}")
            continue

        try:
            new_items, block_info = mod.run(args.since_year, args.since_month)
        except Exception as e:
            print(f"[ERROR] {key} 크롤링 실패: {e}")
            summary[key] = f"오류: {e}"
            continue

        # block_info 처리: list(차단된 게시판 목록) 또는 FetchResult 객체 모두 지원
        if isinstance(block_info, list) and block_info:
            # mfds.run() 등: 차단된 게시판 키 목록을 반환
            print(f"[BLOCKED] {key}: 차단된 게시판 {block_info} — self-hosted runner 사용을 확인하세요.")
            summary[key] = f"일부 차단({len(block_info)}개 게시판), {len(new_items)}건 수집"
            # 차단되지 않은 게시판의 결과는 그대로 사용
        elif block_info is not None and getattr(block_info, "blocked", False):
            print(f"[BLOCKED] {key}: {block_info.error} — self-hosted runner 사용을 확인하세요.")
            summary[key] = "차단됨(접속 실패)"
            continue

        all_new_items.extend(new_items)
        summary[key] = f"{len(new_items)}건 수집"
        print(f"[OK] {key}: {len(new_items)}건 수집")

    register = register_io.upsert_items(register, all_new_items)
    register_io.save_register(register)

    print("\n=== 크롤링 요약 ===")
    for k, v in summary.items():
        print(f"  {k:16s} : {v}")
    print(f"\n검토대장 총 {len(register['items'])}건 저장 완료 → docs/data/register.json")


if __name__ == "__main__":
    main()
