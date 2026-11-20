"""
Generate synthetic seasonal weather for Olympic Park tennis analysis
==================================================================
기상청 원자료가 아닙니다. 서울 사계절 경향을 흉내 낸 합성 시계열(365일 x 24시간 = 8,760건)입니다.
앱의 실시간 안내는 이 CSV가 아니라 기상청 초단기실황 API를 씁니다.
"""

import os
import numpy as np
import pandas as pd
from datetime import datetime, timedelta

def generate_olympic_weather():
    np.random.seed(42)
    start_date = datetime(2025, 1, 1, 0, 0)
    records = []

    for i in range(8760):
        current_time = start_date + timedelta(hours=i)
        month = current_time.month
        hour = current_time.hour

        # 1. 계절 구분
        if month in [12, 1, 2]:
            season = "Winter"
            base_temp = -2.0 + (month % 2) * 2.0
            temp_amplitude = 7.0
            base_wind = 3.2
            base_dir = 315.0  # 북서풍
            base_humidity = 55.0
        elif month in [3, 4, 5]:
            season = "Spring"
            base_temp = 12.0
            temp_amplitude = 10.0
            base_wind = 3.8   # 봄철 돌풍
            base_dir = 270.0  # 서풍
            base_humidity = 50.0
        elif month in [6, 7, 8]:
            season = "Summer"
            base_temp = 25.5
            temp_amplitude = 6.0
            base_wind = 2.4
            base_dir = 140.0  # 남동풍
            base_humidity = 78.0
        else:
            season = "Autumn"
            base_temp = 14.0
            temp_amplitude = 9.0
            base_wind = 2.6
            base_dir = 330.0  # 북북서풍
            base_humidity = 60.0

        # 2. 일변화 (일교차 및 낮 시간 바람 증가)
        diurnal_factor = np.sin((hour - 8) / 24.0 * 2 * np.pi)
        temp = base_temp + (temp_amplitude / 2) * diurnal_factor + np.random.normal(0, 2.0)
        humidity = base_humidity - (15.0 * diurnal_factor) + np.random.normal(0, 5.0)
        humidity = np.clip(humidity, 20.0, 95.0)

        # 낮 시간(12~16시)에 대류 현상으로 풍속 증가
        wind_diurnal = 1.2 if (11 <= hour <= 16) else 0.8
        wind_speed = max(0.5, (base_wind * wind_diurnal) + np.random.normal(0, 1.2))
        wind_dir = (base_dir + np.random.normal(0, 35.0)) % 360.0

        records.append({
            "datetime": current_time.strftime("%Y-%m-%d %H:%M"),
            "month": month,
            "hour": hour,
            "season": season,
            "temperature_c": round(temp, 1),
            "humidity_pct": round(humidity, 1),
            "wind_speed_ms": round(wind_speed, 1),
            "wind_dir_deg": round(wind_dir, 1)
        })

    df = pd.DataFrame(records)
    
    # 저장 경로
    curr_dir = os.path.dirname(os.path.abspath(__file__))
    out_path = os.path.join(curr_dir, "..", "data", "olympic_weather_history.csv")
    df.to_csv(out_path, index=False, encoding="utf-8-sig")
    print(f"[Success] Generated {len(df)} weather records -> {out_path}")

if __name__ == "__main__":
    generate_olympic_weather()
