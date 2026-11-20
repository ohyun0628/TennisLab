"""
Weather API Module for TennisLab
================================
기상청 초단기실황 및 단기예보 Open API 연동 모듈
위치: 서울 올림픽공원 테니스장 (서울 송파구 올림픽로 424)
기상청 격자 좌표: X=62, Y=125
"""

import os
import datetime
from typing import Dict, Any, Optional

import requests


def _read_env_file(path: str) -> dict:
    values = {}
    if not os.path.isfile(path):
        return values
    with open(path, encoding="utf-8") as handle:
        for raw in handle:
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def _load_service_key() -> Optional[str]:
    key = os.environ.get("KMA_SERVICE_KEY") or os.environ.get("EXPO_PUBLIC_KMA_KEY")
    if key:
        return key
    root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    for env_path in (os.path.join(root, ".env"), os.path.join(root, "mobile", ".env")):
        values = _read_env_file(env_path)
        key = values.get("KMA_SERVICE_KEY") or values.get("EXPO_PUBLIC_KMA_KEY")
        if key:
            return key
    return None


class OlympicParkWeatherAPI:
    """올림픽공원 테니스장 전용 기상 데이터 수집기"""

    # 올림픽공원 테니스장 기상청 격자 좌표
    GRID_X = 62
    GRID_Y = 125
    LATITUDE = 37.5208
    LONGITUDE = 127.1215

    # 기상청 초단기실황 엔드포인트
    BASE_URL = "https://apis.data.go.kr/1360000/VilageFcstInfoService_2.0/getUltraSrtNcst"
    OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"

    def __init__(self, service_key: Optional[str] = None):
        self.service_key = service_key or _load_service_key()

    def fetch_live_weather(self) -> Dict[str, Any]:
        """
        기상청 초단기실황 조회. 키가 없으면 올림픽공원 좌표 실시간 관측을 사용합니다.
        """
        now = datetime.datetime.now()
        base_date = now.strftime("%Y%m%d")
        # 매시간 45분 이후 호출 안전 (현재 시각 30분 전 기준)
        base_time = (now - datetime.timedelta(minutes=30)).strftime("%H00")

        if self.service_key:
            try:
                params = {
                    "serviceKey": self.service_key,
                    "pageNo": "1",
                    "numOfRows": "10",
                    "dataType": "JSON",
                    "base_date": base_date,
                    "base_time": base_time,
                    "nx": str(self.GRID_X),
                    "ny": str(self.GRID_Y)
                }
                response = requests.get(self.BASE_URL, params=params, timeout=5)
                if response.status_code == 200:
                    data = response.json()
                    items = data.get("response", {}).get("body", {}).get("items", {}).get("item", [])
                    if items:
                        parsed = self._parse_kma_items(items, now)
                        parsed["source"] = "kma"
                        return parsed
            except Exception as e:
                print(f"[WeatherAPI] 기상청 API 호출 실패, 실시간 관측으로 전환: {e}")

        live = self._fetch_open_meteo(now)
        if live:
            return live

        return self._generate_realistic_fallback(now)

    def _parse_kma_items(self, items: list, now: datetime.datetime) -> Dict[str, Any]:
        """기상청 응답 파싱"""
        parsed = {
            "timestamp": now.strftime("%Y-%m-%d %H:%M"),
            "temperature_c": 18.0,
            "wind_speed_ms": 2.5,
            "wind_dir_deg": 350.0,
            "humidity_pct": 55.0,
            "rain_1h_mm": 0.0,
            "is_live_api": True,
            "source": "kma"
        }
        for item in items:
            cat = item.get("category")
            val = float(item.get("obsrValue", 0))
            if cat == "T1H":    # 기온 (C)
                parsed["temperature_c"] = val
            elif cat == "WSD":  # 풍속 (m/s)
                parsed["wind_speed_ms"] = val
            elif cat == "VEC":  # 풍향 (deg)
                parsed["wind_dir_deg"] = val
            elif cat == "REH":  # 습도 (%)
                parsed["humidity_pct"] = val
            elif cat == "RN1":  # 1시간 강수량 (mm)
                parsed["rain_1h_mm"] = val
        return parsed

    def _generate_realistic_fallback(self, now: datetime.datetime) -> Dict[str, Any]:
        """시간대별 현실적인 기상 모델 생성"""
        hour = now.hour
        # 낮 시간(12~16시)은 기온이 높고 바람이 다소 강함
        if 11 <= hour <= 16:
            temp = 19.5
            wind_speed = 3.6
            wind_dir = 340.0  # 북북서풍
            humidity = 48.0
        elif 17 <= hour <= 21:
            temp = 15.2
            wind_speed = 2.2
            wind_dir = 320.0  # 북서풍
            humidity = 62.0
        else:
            temp = 12.0
            wind_speed = 1.8
            wind_dir = 20.0   # 북동풍
            humidity = 70.0

        return {
            "timestamp": now.strftime("%Y-%m-%d %H:%M"),
            "temperature_c": temp,
            "wind_speed_ms": wind_speed,
            "wind_dir_deg": wind_dir,
            "humidity_pct": humidity,
            "rain_1h_mm": 0.0,
            "is_live_api": False,
            "source": "fallback"
        }

    def _fetch_open_meteo(self, now: datetime.datetime) -> Optional[Dict[str, Any]]:
        """올림픽공원 좌표 실시간 관측 (기상청 키 없을 때 사용)"""
        try:
            params = {
                "latitude": self.LATITUDE,
                "longitude": self.LONGITUDE,
                "current": "temperature_2m,relative_humidity_2m,wind_speed_10m,wind_direction_10m,precipitation",
                "wind_speed_unit": "ms",
                "timezone": "Asia/Seoul"
            }
            response = requests.get(self.OPEN_METEO_URL, params=params, timeout=5)
            if response.status_code != 200:
                return None
            current = response.json().get("current") or {}
            if "temperature_2m" not in current:
                return None
            return {
                "timestamp": str(current.get("time", now.strftime("%Y-%m-%d %H:%M"))).replace("T", " "),
                "temperature_c": round(float(current["temperature_2m"]), 1),
                "wind_speed_ms": round(float(current.get("wind_speed_10m", 0)), 1),
                "wind_dir_deg": float(current.get("wind_direction_10m", 0)),
                "humidity_pct": float(current.get("relative_humidity_2m", 0)),
                "rain_1h_mm": float(current.get("precipitation", 0)),
                "is_live_api": True,
                "source": "open-meteo"
            }
        except Exception as e:
            print(f"[WeatherAPI] Open-Meteo 호출 실패: {e}")
            return None
