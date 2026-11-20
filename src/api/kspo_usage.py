"""한국체육산업개발 테니스장 이용 정보 (data.go.kr 15133891)"""
import csv
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

import requests

try:
    from src.api.weather import _load_service_key
except ImportError:
    from api.weather import _load_service_key

USAGE_URL = "https://api.odcloud.kr/api/15133891/v1/uddi:727042a0-87e3-4bd0-9d33-e3f97e00bba6"
CSV_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "data", "kspo_tennis_usage_20251231.csv"))
RESERVE_URL = "https://www.ksponco.or.kr/online/tennis/index.do"


def _normalize(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    items = []
    for row in rows:
        start = str(row.get("시작일") or row.get("startdate") or "")
        kind = str(row.get("구분") or row.get("code") or "")
        try:
            count = int(row.get("이용자수") or row.get("member") or 0)
        except (TypeError, ValueError):
            continue
        if len(start) < 7 or not kind:
            continue
        items.append({
            "type": kind,
            "start": start,
            "year": int(start[:4]),
            "month": int(start[5:7]),
            "count": count
        })
    return items


def _from_csv() -> List[Dict[str, Any]]:
    if not os.path.isfile(CSV_PATH):
        return []
    for encoding in ("utf-8-sig", "cp949"):
        try:
            with open(CSV_PATH, encoding=encoding) as handle:
                return _normalize(list(csv.DictReader(handle)))
        except UnicodeDecodeError:
            continue
    return []


def _from_api() -> List[Dict[str, Any]]:
    key = _load_service_key()
    if not key:
        return []
    response = requests.get(USAGE_URL, params={"page": 1, "perPage": 120, "serviceKey": key}, timeout=10)
    if response.status_code != 200:
        return []
    return _normalize(response.json().get("data") or [])


def fetch_usage_summary() -> Dict[str, Any]:
    items = _from_api() or _from_csv()
    if not items:
        return {"is_live": False, "reserve_url": RESERVE_URL}

    now = datetime.now()
    same_month = [item for item in items if item["month"] == now.month]
    pool = same_month or items
    period = max(pool, key=lambda item: item["start"])

    def find(kind: str, year: int) -> Optional[int]:
        hit = next((item for item in items if item["year"] == year and item["month"] == period["month"] and item["type"] == kind), None)
        return hit["count"] if hit else None

    daily = find("일일입장", period["year"]) or 0
    member = find("월회원", period["year"]) or 0
    prev = find("일일입장", period["year"] - 1)
    yoy = round((daily - prev) / prev * 100) if prev else None
    daily_all = [item["count"] for item in items if item["type"] == "일일입장"]
    avg = sum(daily_all) / len(daily_all) if daily_all else daily
    busy = "혼잡" if daily >= avg * 1.15 else ("한산" if daily <= avg * 0.85 else "보통")

    return {
        "is_live": True,
        "source": "kspo",
        "period_label": f"{period['year']}년 {period['month']}월",
        "daily_visitors": daily,
        "monthly_members": member,
        "total_visitors": daily + member,
        "yoy_pct": yoy,
        "busy_label": busy,
        "reserve_url": RESERVE_URL
    }
