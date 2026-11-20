"""
TennisLab Backend REST API Server (FastAPI)
============================================
올림픽공원 테니스장 물리 엔진 및 ML 모델을 모바일 앱 및 외부 클라이언트에 서빙하는 REST API 서버
"""

import os
import sys
import json
from typing import Dict, Any, Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# sys.path 설정 (프로젝트 루트 및 src 지원)
CURR_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(CURR_DIR, ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)
if CURR_DIR not in sys.path:
    sys.path.insert(0, CURR_DIR)

try:
    from src.engine.physics import TennisPhysicsEngine
    from src.api.weather import OlympicParkWeatherAPI
    from src.api.kspo_usage import fetch_usage_summary
except ImportError:
    from engine.physics import TennisPhysicsEngine
    from api.weather import OlympicParkWeatherAPI
    from api.kspo_usage import fetch_usage_summary

app = FastAPI(
    title="TennisLab REST API",
    description="한국체육산업개발 올림픽공원 테니스장 코트 환경 동역학 및 AI 추천 API",
    version="1.0.0"
)

# 모바일 앱 및 웹 클라이언트를 위한 CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 데이터 로드
CURR_DIR = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(CURR_DIR, "..", "data", "olympic_courts.json"), "r", encoding="utf-8") as f:
    COURTS_DATA = json.load(f)

weather_api = OlympicParkWeatherAPI()


# ----------------------------------------------------
# Request / Response Schemas
# ----------------------------------------------------
class SimulationRequest(BaseModel):
    court_id: int = 1
    wind_speed_ms: Optional[float] = None
    wind_dir_deg: Optional[float] = None
    temperature_c: Optional[float] = None
    humidity_pct: Optional[float] = 50.0
    hour_24: Optional[int] = 14
    player_side: str = "West"        # "West"/"East" (South/North 호환)
    shot_speed_kmh: float = 90.0
    shot_type: str = "rally"         # "rally" or "serve"

class RecommendRequest(BaseModel):
    player_skill: int = 1            # 1: 초보자, 2: 중급자, 3: 상급자
    wind_speed_ms: Optional[float] = None
    temperature_c: Optional[float] = None


# ----------------------------------------------------
# API Endpoints
# ----------------------------------------------------
@app.get("/")
def root():
    return {
        "service": "TennisLab Backend API",
        "status": "online",
        "docs": "/docs",
        "endpoints": ["/api/courts", "/api/weather/live", "/api/usage", "/api/simulate", "/api/recommend"]
    }

@app.get("/api/courts")
def get_courts():
    """올림픽공원 19개 코트 메타데이터 목록 반환"""
    return {"total": len(COURTS_DATA), "courts": COURTS_DATA}

@app.get("/api/weather/live")
def get_live_weather():
    """기상청 실시간 올림픽공원 기상 실황 반환"""
    return weather_api.fetch_live_weather()

@app.get("/api/usage")
def get_usage():
    """한국체육산업개발 테니스장 월별 이용 정보 반환"""
    return fetch_usage_summary()

@app.post("/api/simulate")
def simulate_court_physics(req: SimulationRequest):
    """
    특정 코트의 기상 연계 볼 궤적 편차, 하드코트 바운스, 눈부심 및 AI 전술 브리핑 연산
    """
    court = next((c for c in COURTS_DATA if c["court_id"] == req.court_id), None)
    if not court:
        raise HTTPException(status_code=404, detail="Court not found")

    # 기상 값 미입력 시 실시간 기상 자동 사용
    live = weather_api.fetch_live_weather()
    w_speed = req.wind_speed_ms if req.wind_speed_ms is not None else live["wind_speed_ms"]
    w_dir = req.wind_dir_deg if req.wind_dir_deg is not None else live["wind_dir_deg"]
    temp = req.temperature_c if req.temperature_c is not None else live["temperature_c"]
    humidity = req.humidity_pct if req.humidity_pct is not None else live["humidity_pct"]

    # 1. 풍향 벡터 분해
    wind_decomp = TennisPhysicsEngine.decompose_wind(
        wind_speed_ms=w_speed,
        wind_dir_deg=w_dir,
        court_orientation_deg=court["orientation_deg"],
        player_side=req.player_side
    )

    # 2. 볼 궤적 시뮬레이션
    trajectory = TennisPhysicsEngine.simulate_ball_trajectory(
        shot_speed_kmh=req.shot_speed_kmh,
        wind_decomp=wind_decomp,
        temp_c=temp,
        shot_type=req.shot_type
    )

    # 3. 하드코트 바운스 & COR
    bounce = TennisPhysicsEngine.calculate_court_bounce(
        temp_c=temp,
        humidity_pct=humidity
    )

    # 4. 서브 눈부심
    glare = TennisPhysicsEngine.calculate_sun_glare(
        hour_24=req.hour_24,
        court_orientation_deg=court["orientation_deg"],
        player_side=req.player_side
    )

    # 5. 전술 브리핑
    tactics = TennisPhysicsEngine.generate_tactical_briefing(
        wind_decomp=wind_decomp,
        trajectory=trajectory,
        bounce=bounce,
        glare=glare,
        court_info=court
    )

    return {
        "court": court,
        "weather": {
            "wind_speed_ms": w_speed,
            "wind_dir_deg": w_dir,
            "temperature_c": temp,
            "humidity_pct": humidity
        },
        "wind_analysis": wind_decomp,
        "ball_trajectory": trajectory,
        "court_bounce": bounce,
        "sun_glare": glare,
        "tactical_briefing": tactics
    }

@app.post("/api/recommend")
def recommend_court(req: RecommendRequest):
    """
    플레이어 수준(1: 초보, 2: 중급, 3: 상급)에 따른 19개 코트 적합도 스코어링 및 Top 3 추천
    """
    live = weather_api.fetch_live_weather()
    w_speed = req.wind_speed_ms if req.wind_speed_ms is not None else live["wind_speed_ms"]
    temp = req.temperature_c if req.temperature_c is not None else live["temperature_c"]

    scored_courts = []
    for c in COURTS_DATA:
        score = 80.0
        if c["has_roof"]:
            # 실내 코트는 초보자일수록 가산점
            score = 96.0 if req.player_skill == 1 else (91.0 if req.player_skill == 2 else 88.0)
        else:
            # 실외 코트는 바람에 따른 감점
            penalty = w_speed * (4.5 if req.player_skill == 1 else (2.5 if req.player_skill == 2 else 1.2))
            score -= penalty
            if c["court_id"] == 1 and req.player_skill == 3:
                score += 10.0 # 상급자 센터코트 보너스

        score = round(max(30.0, min(99.0, score)), 1)
        scored_courts.append({
            "court_id": c["court_id"],
            "name": c["name"],
            "type": "실내" if c["has_roof"] else "실외",
            "score": score
        })

    # 점수 높은 순 정렬
    scored_courts.sort(key=lambda x: x["score"], reverse=True)

    skill_label = "초보자 (NTRP 2.0)" if req.player_skill == 1 else ("중급 랠리형 (NTRP 3.5)" if req.player_skill == 2 else "상급 파워형 (NTRP 4.5)")
    return {
        "player_skill_label": skill_label,
        "weather_summary": f"풍속 {w_speed}m/s, 기온 {temp}℃",
        "top_recommendations": scored_courts[:3],
        "all_ranked_courts": scored_courts
    }
