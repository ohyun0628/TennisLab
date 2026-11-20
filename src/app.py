"""
TennisLab - 올림픽공원 테니스장 실시간 코트 환경 동역학 & AI 전술 플랫폼
========================================================================
2026 한국체육산업개발(주) 공공데이터 활용 경진대회 출품작
"""

import json
import os
import streamlit as st
import plotly.graph_objects as go
import pandas as pd
from datetime import datetime

from engine.physics import TennisPhysicsEngine
from api.weather import OlympicParkWeatherAPI
from api.kspo_usage import CSV_PATH, fetch_usage_summary

# ----------------------------------------------------
# 1. 페이지 기본 설정 (Page Config)
# ----------------------------------------------------
st.set_page_config(
    page_title="TennisLab | 올림픽공원 테니스장 코트 동역학 플랫폼",
    page_icon="🎾",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 커스텀 CSS (모바일 반응형 및 세련된 스포츠 사이언스 UI 스타일)
st.markdown("""
<style>
    .main-title {
        font-size: 2.2rem;
        font-weight: 800;
        color: #1E3A8A;
        margin-bottom: 0.2rem;
    }
    .sub-title {
        font-size: 1.05rem;
        color: #4B5563;
        margin-bottom: 1.2rem;
    }
    .metric-card {
        background-color: #F8FAFC;
        border-radius: 12px;
        padding: 16px;
        border: 1px solid #E2E8F0;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }
    .tactics-box {
        background: linear-gradient(135deg, #EFF6FF 0%, #DBEAFE 100%);
        border-left: 5px solid #2563EB;
        border-radius: 8px;
        padding: 16px;
        margin-top: 10px;
    }
    .badge-indoor {
        background-color: #10B981;
        color: white;
        padding: 4px 10px;
        border-radius: 12px;
        font-size: 0.8rem;
        font-weight: bold;
    }
    .badge-outdoor {
        background-color: #F59E0B;
        color: white;
        padding: 4px 10px;
        border-radius: 12px;
        font-size: 0.8rem;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)

# ----------------------------------------------------
# 2. 데이터 로드 (코트 메타데이터)
# ----------------------------------------------------
@st.cache_data
def load_court_metadata():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    data_path = os.path.join(current_dir, "..", "data", "olympic_courts.json")
    with open(data_path, "r", encoding="utf-8") as f:
        return json.load(f)

courts_data = load_court_metadata()
courts_dict = {f"코트 {c['court_id']}: {c['name']}": c for c in courts_data}

# ----------------------------------------------------
# 3. 사이드바 (기상 조건 및 시뮬레이션 설정)
# ----------------------------------------------------
st.sidebar.image("https://img.icons8.com/color/96/tennis.png", width=64)
st.sidebar.title("🎾 TennisLab 환경 설정")

weather_mode = st.sidebar.radio(
    "기상 데이터 소스",
    ["기상청 실시간/실황 연동", "환경 시뮬레이터 (사용자 지정)"]
)

weather_api = OlympicParkWeatherAPI()
live_weather = weather_api.fetch_live_weather()

if weather_mode == "기상청 실시간/실황 연동":
    st.sidebar.info(f"📍 위치: 서울 올림픽공원 (격자 62, 125)\n🕒 갱신 시각: {live_weather['timestamp']}")
    wind_speed = live_weather["wind_speed_ms"]
    wind_dir = live_weather["wind_dir_deg"]
    temperature = live_weather["temperature_c"]
    humidity = live_weather["humidity_pct"]
    hour = datetime.now().hour
else:
    st.sidebar.markdown("### 🎛️ 기상 변수 제어")
    wind_speed = st.sidebar.slider("풍속 (m/s)", min_value=0.0, max_value=12.0, value=3.5, step=0.1)
    wind_dir = st.sidebar.slider("풍향 (도, 0°=북풍, 90°=동풍)", min_value=0, max_value=360, value=340, step=10)
    temperature = st.sidebar.slider("기온 (℃)", min_value=-5.0, max_value=38.0, value=20.0, step=0.5)
    humidity = st.sidebar.slider("습도 (%)", min_value=20, max_value=95, value=50, step=5)
    hour = st.sidebar.slider("경기 시간대 (24시)", min_value=6, max_value=21, value=14, step=1)

st.sidebar.markdown("---")
st.sidebar.markdown("### 🏃 플레이어 설정")
player_side = st.sidebar.segmented_control(
    "플레이어 코트 위치",
    ["서쪽 엔드 (117°)", "동쪽 엔드 (297°)"],
    default="서쪽 엔드 (117°)",
    required=True,
    key="player_end",
)
player_side_key = "West" if player_side.startswith("서쪽") else "East"

shot_type = st.sidebar.selectbox(
    "시뮬레이션 타구 유형",
    ["포핸드/백핸드 랠리 (평균 90km/h)", "플랫/탑스핀 서브 (평균 150km/h)"],
    index=0
)
shot_speed_kmh = 90.0 if "랠리" in shot_type else 150.0
shot_type_key = "rally" if "랠리" in shot_type else "serve"

# ----------------------------------------------------
# 4. 메인 대시보드 헤더
# ----------------------------------------------------
st.markdown('<div class="main-title">🎾 TennisLab: 올림픽공원 테니스장 코트 동역학 플랫폼</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">한국체육산업개발 공공데이터와 기상청 초단기 실황 API를 결합한 실시간 코트별 환경 시뮬레이션 및 데이터 기반 플레이 가이드</div>', unsafe_allow_html=True)

# ----------------------------------------------------
# 5. 코트 선택기
# ----------------------------------------------------
col_court_sel, col_court_info = st.columns([1.5, 2.5])

with col_court_sel:
    selected_court_name = st.selectbox("🎯 분석할 코트를 선택하세요 (총 19개 코트)", list(courts_dict.keys()), index=0)
    selected_court = courts_dict[selected_court_name]

with col_court_info:
    is_indoor = selected_court["has_roof"]
    badge_html = '<span class="badge-indoor">실내 코트 (전천후)</span>' if is_indoor else '<span class="badge-outdoor">실외 하드코트</span>'
    st.markdown(f"**선택 코트**: {selected_court['name']} {badge_html}", unsafe_allow_html=True)
    st.markdown(
        f"**코트 특성**: {selected_court['description']} "
        f"(장축 방위각: {selected_court['orientation_deg']}° · OSM·위성 실측, 공공 API 없음)"
    )

# ----------------------------------------------------
# 6. 물리 엔진 연산 (Physics Engine Calculation)
# ----------------------------------------------------
wind_decomp = TennisPhysicsEngine.decompose_wind(
    wind_speed_ms=wind_speed,
    wind_dir_deg=wind_dir,
    court_orientation_deg=selected_court["orientation_deg"],
    player_side=player_side_key
)

trajectory = TennisPhysicsEngine.simulate_ball_trajectory(
    shot_speed_kmh=shot_speed_kmh,
    wind_decomp=wind_decomp,
    temp_c=temperature,
    shot_type=shot_type_key
)

bounce = TennisPhysicsEngine.calculate_court_bounce(
    temp_c=temperature,
    humidity_pct=humidity
)

glare = TennisPhysicsEngine.calculate_sun_glare(
    hour_24=hour,
    court_orientation_deg=selected_court["orientation_deg"],
    player_side=player_side_key
)

tactics = TennisPhysicsEngine.generate_tactical_briefing(
    wind_decomp=wind_decomp,
    trajectory=trajectory,
    bounce=bounce,
    glare=glare,
    court_info=selected_court
)

# ----------------------------------------------------
# 7. 핵심 물리 지표 메트릭 카드
# ----------------------------------------------------
st.markdown("### 📊 실시간 코트 물리 환경 분석")
m1, m2, m3, m4 = st.columns(4)

with m1:
    if is_indoor:
        st.metric("유효 바람", "0.0 m/s", "실내 차단")
    else:
        st.metric(
            "유효 바람 (종/횡)",
            f"{wind_decomp['tail_head_wind_ms']:+.1f} m/s",
            f"측풍 {wind_decomp['cross_wind_ms']:+.1f} m/s"
        )

with m2:
    if is_indoor:
        st.metric("볼 비거리 편차", "0 cm", "표준 궤적 유지")
    else:
        dist_delta = trajectory["distance_delta_cm"]
        dist_label = "길어짐 (Out 주의)" if dist_delta > 0 else "짧아짐 (Net 주의)"
        st.metric("볼 비거리 편차 (Δx)", f"{dist_delta:+.1f} cm", dist_label)

with m3:
    if is_indoor:
        st.metric("좌우 휨 편차", "0 cm", "직진성 양호")
    else:
        lat_delta = trajectory["lateral_delta_cm"]
        lat_label = "우측 밀림" if lat_delta > 0 else "좌측 밀림"
        st.metric("좌우 휨 편차 (Δy)", f"{lat_delta:+.1f} cm", lat_label)

with m4:
    st.metric(
        "코트 반발력 (COR)",
        f"{bounce['cor']:.3f}",
        f"바운스: {bounce['court_pace_label']}"
    )

st.markdown("---")

# ----------------------------------------------------
# 8. 시각화 (2D 코트 궤적 맵 & 풍향 레이더)
# ----------------------------------------------------
col_viz1, col_viz2 = st.columns([1.8, 1.2])

with col_viz1:
    st.markdown("#### 🎯 코트 내 볼 착지점 편차 시뮬레이션")
    
    # Plotly 2D 테니스 코트 그리기
    fig = go.Figure()

    # 테니스 코트 외곽 (단식 규격: 23.77m x 8.23m)
    fig.add_shape(type="rect", x0=-4.115, y0=-11.885, x1=4.115, y1=11.885,
                  line=dict(color="#FFFFFF", width=3), fillcolor="#2563EB", opacity=0.85)

    # 서비스 박스 (네트 중심에서 6.4m)
    fig.add_shape(type="rect", x0=-4.115, y0=-6.4, x1=4.115, y1=6.4,
                  line=dict(color="#FFFFFF", width=2))
    # 센터 서비스 라인
    fig.add_shape(type="line", x0=0, y0=-6.4, x1=0, y1=6.4,
                  line=dict(color="#FFFFFF", width=2))
    # 네트 (Net)
    fig.add_shape(type="line", x0=-5.0, y0=0, x1=5.0, y1=0,
                  line=dict(color="#FCD34D", width=4, dash="solid"))

    # 플레이어 위치 마커
    player_y = -11.5 if player_side_key == "West" else 11.5
    fig.add_trace(go.Scatter(
        x=[0], y=[player_y],
        mode="markers+text",
        marker=dict(size=14, color="#EF4444", symbol="star"),
        name="플레이어 위치",
        text=["플레이어"], textposition="bottom center"
    ))

    # 목표 착지점 (기준: 반대편 베이스라인 안쪽)
    target_y = 9.5 if player_side_key == "West" else -9.5
    fig.add_trace(go.Scatter(
        x=[0], y=[target_y],
        mode="markers",
        marker=dict(size=12, color="#10B981", symbol="circle-open"),
        name="정상 조준 타겟 (무풍)"
    ))

    # 환경 영향으로 실제 착지 예상점
    if not is_indoor:
        real_y = target_y + (trajectory["distance_delta_cm"] / 100.0)
        real_x = 0 + (trajectory["lateral_delta_cm"] / 100.0)
        fig.add_trace(go.Scatter(
            x=[real_x], y=[real_y],
            mode="markers+text",
            marker=dict(size=14, color="#F59E0B", symbol="x"),
            name="바람 편차 착지점",
            text=["실제 착지"], textposition="top right"
        ))
        # 궤적 벡터 화살표
        fig.add_annotation(
            x=real_x, y=real_y,
            ax=0, ay=target_y,
            xref="x", yref="y", axref="x", ayref="y",
            text="", showarrow=True,
            arrowhead=2, arrowsize=1, arrowwidth=2, arrowcolor="#F59E0B"
        )

    fig.update_layout(
        title="올림픽공원 코트 탑뷰 (단위: m)",
        xaxis=dict(range=[-6, 6], visible=True, showgrid=False, zeroline=False),
        yaxis=dict(range=[-14, 14], visible=True, showgrid=False, zeroline=False),
        height=480,
        margin=dict(l=20, r=20, t=40, b=20),
        plot_bgcolor="#1E293B",
        showlegend=True
    )
    st.plotly_chart(fig, use_container_width=True)

with col_viz2:
    st.markdown("#### 🧭 유효 풍향 레이더 & 눈부심")
    
    # 풍향 극좌표계(Polar) 차트
    fig_polar = go.Figure()
    fig_polar.add_trace(go.Scatterpolar(
        r=[0, wind_speed if not is_indoor else 0],
        theta=[0, wind_dir],
        mode="lines+markers",
        line=dict(color="#3B82F6", width=4),
        marker=dict(size=8, color="#1D4D8F"),
        name="실제 풍향/풍속"
    ))
    fig_polar.update_layout(
        polar=dict(
            radialaxis=dict(visible=True, range=[0, max(8, wind_speed + 2)]),
            angularaxis=dict(direction="clockwise", rotation=90)
        ),
        height=320,
        margin=dict(l=20, r=20, t=20, b=20)
    )
    st.plotly_chart(fig_polar, use_container_width=True)
    
    st.markdown(f"**☀️ 서브 시야 눈부심**: `{glare.get('glare_risk', 'None')}`")
    st.markdown(f"**🌡️ 하드코트 체감 상태**: `{bounce['court_pace_label']}` (낙하 바운스: {bounce['bounce_height_m']}m)")

# ----------------------------------------------------
# 9. AI 맞춤 전술 가이드
# ----------------------------------------------------
st.markdown("### 🧠 AI 전술 브리핑 (Tactical Briefing)")
with st.container():
    st.markdown(f"""
    <div class="tactics-box">
        <h4 style="margin-top:0; color:#1E40AF;">📋 {selected_court['name']} 경기 전략 리포트</h4>
        <p><strong>종합 분석:</strong> {tactics['summary']}</p>
        <p><strong>추천 포지션/엔드:</strong> {tactics['recommended_side']}</p>
        <hr style="border:0.5px solid #BFDBFE;">
        <strong>맞춤 세부 전술:</strong>
        <ul>
            {"".join([f"<li>{t}</li>" for t in tactics['tactics']])}
        </ul>
    </div>
    """, unsafe_allow_html=True)

# ----------------------------------------------------
# 10. 한국체육산업개발 테니스장 이용 정보 (공공데이터)
# ----------------------------------------------------
st.markdown("---")
st.markdown("### 올림픽 테니스장 이용 정보")
st.caption("한국체육산업개발 공공데이터 (data.go.kr 15133891). 코트별 실시간 예약 슬롯은 공개되지 않아 공식 예약 사이트로 연결합니다.")

@st.cache_data(ttl=3600)
def load_kspo_usage():
    return fetch_usage_summary()

usage = load_kspo_usage()
if usage.get("is_live"):
    col_u1, col_u2, col_u3 = st.columns(3)
    yoy = usage.get("yoy_pct")
    col_u1.metric("일일입장", f"{usage['daily_visitors']:,}명", usage.get("busy_label"))
    col_u2.metric("월회원", f"{usage['monthly_members']:,}명")
    col_u3.metric("전년 동월", f"{yoy:+d}%" if yoy is not None else "-", usage.get("period_label"))
    st.link_button("올림픽테니스장 공식 예약", usage["reserve_url"], width="stretch")
    if os.path.isfile(CSV_PATH):
        df_usage = pd.read_csv(CSV_PATH, encoding="cp949")
        st.dataframe(df_usage, width="stretch", hide_index=True, alt="올림픽공원 테니스장 월별 이용 정보")
else:
    st.warning("이용 정보를 불러오지 못했습니다.")
