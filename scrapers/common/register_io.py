"""
docs/data/register.json 읽기/쓰기 + 중복 병합 유틸.
각 기관별 크롤러(mfds.py, mdcg.py ...)는 이 모듈을 통해
새로 수집한 항목을 기존 검토대장에 병합한다 (id 기준 upsert).
"""
import json
import os
from datetime import datetime, timezone, timedelta

KST = timezone(timedelta(hours=9))
REGISTER_PATH = os.path.join(
    os.path.dirname(__file__), "..", "..", "docs", "data", "register.json"
)
GAP_DIR = os.path.join(
    os.path.dirname(__file__), "..", "..", "docs", "data", "gap"
)


def load_register():
    if not os.path.exists(REGISTER_PATH):
        return {"meta": {}, "items": []}
    with open(REGISTER_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def save_register(data):
    data.setdefault("meta", {})
    data["meta"]["generated_at"] = datetime.now(KST).isoformat()
    with open(REGISTER_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def upsert_items(data, new_items):
    """id 기준으로 기존 항목을 갱신하거나 새 항목을 추가한다."""
    by_id = {it["id"]: it for it in data.get("items", [])}
    for it in new_items:
        by_id[it["id"]] = it
    # No. 재부여 (고시일 최신순)
    items = sorted(
        by_id.values(),
        key=lambda x: (x.get("published_date") or "0000-00-00"),
        reverse=True,
    )
    for idx, it in enumerate(items, start=1):
        it["no"] = idx
    data["items"] = items
    return data


def save_gap_document(gap_doc):
    os.makedirs(GAP_DIR, exist_ok=True)
    path = os.path.join(GAP_DIR, f"{gap_doc['id']}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(gap_doc, f, ensure_ascii=False, indent=2)
