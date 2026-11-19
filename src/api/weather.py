"""
Weather API Module for TennisLab
================================
기상청 초단기실황 및 단기예보 Open API 연동 모듈
위치: 서울 올림픽공원 테니스장 (서울 송파구 올림픽로 424)
기상청 격자 좌표: X=62, Y=125
"""

import requests
import datetime
from typing import Dict, Any, Optional


class OlympicParkWeatherAPI:
    """올림픽공원 테니스장 전용 기상 데이터 수집기"""

    # 올림픽공원 테니스장 기상청 격자 좌표
    GRID_X = 62
    GRID_Y = 125
    LATITUDE = 37.5208
    LONGITUDE = 127.1215

    # 기상청 단기예보 엔드포인트
    BASE_URL = "http://apis.data.go.kr/1360000/VilageFcstInfoService_2.0/getUltraSrtNcst"

    def __init__(self, service_key: Optional[str] = None):
        self.service_key = service_key

    def fetch_live_weather(self) -> Dict[str, Any]:
        """
        기상청 실시간 초단기 실황 조회 (API 키 없을 시 정밀 디폴트 실황 반환)
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
                    return self._parse_kma_items(items, now)
            except Exception as e:
                print(f"[WeatherAPI] 실시간 API 호출 실패, 시뮬레이션 모드로 전환: {e}")

        # API 키가 없거나 호출 실패 시 현실적인 서울 올림픽공원 실황 반환
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
            "is_live_api": True
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
            "is_live_api": False
        }
