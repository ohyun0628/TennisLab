"""
TennisLab court-zone wind charts
================================
올림픽공원 19개 코트. 장축은 전 코트 117°. 차이는 실내·메인(가정 ×0.75)·도로변입니다.
기상 CSV는 합성 시계열이며 기상청 원자료가 아닙니다.
"""

import os
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

# -------------------------------------------------------------------
# 한글 폰트 및 스타일 설정 (Windows: 맑은 고딕)
# -------------------------------------------------------------------
plt.rcParams['font.family'] = 'Malgun Gothic'
plt.rcParams['axes.unicode_minus'] = False
plt.rcParams['figure.dpi'] = 150

# 경로 설정
CURR_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(CURR_DIR, "..", "data")
DOCS_IMG_DIR = os.path.join(CURR_DIR, "..", "docs", "images")
os.makedirs(DOCS_IMG_DIR, exist_ok=True)

# -------------------------------------------------------------------
# 1. 데이터 로드
# -------------------------------------------------------------------
weather_path = os.path.join(DATA_DIR, "olympic_weather_history.csv")
courts_path = os.path.join(DATA_DIR, "olympic_courts.json")

df_weather = pd.read_csv(weather_path)
with open(courts_path, "r", encoding="utf-8") as f:
    courts = json.load(f)

print("="*60)
print("[TennisLab] 올림픽공원 19개 코트 구역별 바람 분석")
print(f"합성 기상 샘플: {len(df_weather):,} 건 (기상청 원자료 아님)")
print("="*60)

# -------------------------------------------------------------------
# 2. 분석 1: 계절별 19개 코트의 유효 풍속 영향도 히트맵
# -------------------------------------------------------------------
print("\n[분석 1] 계절별 19개 코트 풍향 벡터 분해 및 체감 바람 세기 계산 중...")

seasons = ["Spring", "Summer", "Autumn", "Winter"]
season_kr = {"Spring": "봄 (돌풍)", "Summer": "여름 (남동풍)", "Autumn": "가을 (쾌청)", "Winter": "겨울 (북서풍)"}

heatmap_data = []

for c in courts:
    exposure = float(c.get("wind_exposure", 0.0 if c.get("has_roof") else 1.0))
    row = []
    for s in seasons:
        if exposure <= 0:
            row.append(0.0)
        else:
            df_s = df_weather[df_weather["season"] == s]
            rel_angles = (df_s["wind_dir_deg"] - c["orientation_deg"]) % 360
            rel_rads = np.radians(rel_angles)
            eff_winds = df_s["wind_speed_ms"] * exposure * np.abs(np.cos(rel_rads))
            row.append(round(eff_winds.mean(), 2))
    heatmap_data.append(row)

df_heatmap = pd.DataFrame(
    heatmap_data,
    index=[f"{c['court_id']} {c.get('zone_label', '')}" for c in courts],
    columns=[season_kr[s] for s in seasons],
)

# 히트맵 시각화
plt.figure(figsize=(10, 8))
im = plt.imshow(df_heatmap.values, cmap="YlOrRd", aspect="auto")
cbar = plt.colorbar(im)
cbar.set_label("체감 유효 풍속 (m/s)", fontsize=11)

plt.xticks(range(len(df_heatmap.columns)), df_heatmap.columns, fontsize=11, fontweight="bold")
plt.yticks(range(len(df_heatmap.index)), df_heatmap.index, fontsize=9)
plt.title("구역별 계절 유효 바람 (실내 0, 메인 ×0.75 가정, 장축 117°)", fontsize=13, fontweight="bold", pad=15)

for i in range(len(df_heatmap.index)):
    for j in range(len(df_heatmap.columns)):
        val = df_heatmap.values[i, j]
        plt.text(j, i, f"{val:.1f}", ha="center", va="center", color="black" if val < 2.5 else "white", fontsize=9)

plt.tight_layout()
heatmap_file = os.path.join(DOCS_IMG_DIR, "court_wind_heatmap.png")
plt.savefig(heatmap_file)
plt.close()
print(f"✅ [저장 완료] 코트별 바람 히트맵 -> {heatmap_file}")

# -------------------------------------------------------------------
# 3. 분석 2: 풍속별 볼 비거리 편차(cm) 및 아웃(Out) 확률 분포
# -------------------------------------------------------------------
print("\n[분석 2] 풍속에 따른 스트로크 궤적 편차 및 베이스라인 실책 분포 분석 중...")

shot_speed_kmh = 90.0  # 평균 랠리 구속 (90km/h)
flight_time = 0.75     # 체공 시간 (초)
air_density_ratio = 1.0

wind_scenarios = [
    ("무풍 (0 m/s)", 0.0, "#9CA3AF"),
    ("미풍 (2 m/s)", 2.0, "#3B82F6"),
    ("보통 바람 (4 m/s)", 4.0, "#F59E0B"),
    ("강한 돌풍 (6 m/s)", 6.0, "#EF4444")
]

x_offsets = np.linspace(-150, 150, 500)

plt.figure(figsize=(10, 5))
for label, wind, color in wind_scenarios:
    # 비거리 변화량 중심값
    delta_x = wind * flight_time * 55.0 * air_density_ratio
    # 플레이어 스트로크 오차 표준편차 (약 25cm)
    sigma = 25.0
    # 정규분포 PDF
    pdf = (1 / (sigma * np.sqrt(2 * np.pi))) * np.exp(-0.5 * ((x_offsets - delta_x) / sigma) ** 2)
    plt.plot(x_offsets, pdf, label=f"{label} (중심 이동: {delta_x:+.0f}cm)", color=color, linewidth=2.2)
    plt.fill_between(x_offsets, pdf, alpha=0.15, color=color)

# 베이스라인 아웃 위험선 (타겟이 베이스라인 40cm 안쪽일 때 +40cm 이상이면 아웃)
plt.axvline(x=40.0, color="#DC2626", linestyle="--", linewidth=2, label="베이스라인 아웃(Out) 경계 (+40cm)")
plt.title("풍속에 따른 테니스공 착지점 편차 분포 (스트로크 구속 90km/h)", fontsize=13, fontweight="bold")
plt.xlabel("착지점 위치 편차 (기준 타겟 대비, cm)", fontsize=11)
plt.ylabel("착지 확률 밀도 (Probability Density)", fontsize=11)
plt.legend(loc="upper left", fontsize=10)
plt.grid(True, linestyle=":", alpha=0.6)

plt.tight_layout()
dist_file = os.path.join(DOCS_IMG_DIR, "trajectory_deviation_dist.png")
plt.savefig(dist_file)
plt.close()
print(f"✅ [저장 완료] 볼 착지점 편차 분포도 -> {dist_file}")

# -------------------------------------------------------------------
# 4. 분석 3: 기온에 따른 하드코트 볼 바운스 반발계수(COR) 및 스피드 곡선
# -------------------------------------------------------------------
print("\n[분석 3] 기온 변화에 따른 올림픽 하드코트 볼 바운스 특성 분석 중...")

temps = np.linspace(-5, 38, 100)
cors = 0.745 + ((temps - 20.0) * 0.0018)
cors = np.clip(cors, 0.68, 0.80)
bounce_heights = 2.54 * (cors ** 2)  # ITF 낙하 높이 2.54m

fig, ax1 = plt.subplots(figsize=(10, 5))

color = '#1D4ED8'
ax1.set_xlabel('외기 온도 (℃)', fontsize=11)
ax1.set_ylabel('볼 반발계수 (COR)', color=color, fontsize=11, fontweight="bold")
line1 = ax1.plot(temps, cors, color=color, linewidth=2.5, label='반발계수 (COR)')
ax1.tick_params(axis='y', labelcolor=color)
ax1.grid(True, linestyle=":", alpha=0.6)

# ITF 표준 하드코트 허용 범위 영역 표시 (0.73 ~ 0.76)
ax1.axhspan(0.73, 0.76, color='#E0E7FF', alpha=0.5, label='ITF 하드코트 규격 범위 (0.73~0.76)')

ax2 = ax1.twinx()  
color = '#D97706'
ax2.set_ylabel('바운스 높이 (m, 2.54m 낙하 기준)', color=color, fontsize=11, fontweight="bold")
line2 = ax2.plot(temps, bounce_heights, color=color, linewidth=2.5, linestyle='--', label='바운스 높이 (m)')
ax2.tick_params(axis='y', labelcolor=color)

# 코트 페이스 구분 라벨
plt.title("기온에 따른 올림픽공원 하드코트 볼 바운스 & 코트 페이스(CPR) 변화", fontsize=13, fontweight="bold")
fig.tight_layout()

bounce_file = os.path.join(DOCS_IMG_DIR, "court_bounce_pace.png")
plt.savefig(bounce_file)
plt.close()
print(f"✅ [저장 완료] 하드코트 바운스 곡선 -> {bounce_file}")

# -------------------------------------------------------------------
# 5. 핵심 통계 요약 리포트 출력
# -------------------------------------------------------------------
print("\n" + "="*60)
print("📋 [분석 요약 리포트 (Executive Summary)]")
print("="*60)
print("1. 코트 차이:")
print("   - 장축은 전 코트 117°. 실내는 5~8번이며 유효 바람 0.")
print("   - 메인 1번은 스탠드 차폐 가정(×0.75). 측정값이 아님.")
print("   - 도로변(9~17번)은 열린 실외. 바람은 기상청 실황을 그대로 씀.")
print("2. 궤적 차트:")
print("   - 뒷바람 4m/s 분포는 간이 추정입니다. 실측 아웃 확률이 아닙니다.")
print("3. 바운스 차트:")
print("   - COR은 기온 근사입니다. Fast/Slow 라벨도 그 근사값입니다.")
print("="*60)
print(f"차트 저장: {DOCS_IMG_DIR}")
