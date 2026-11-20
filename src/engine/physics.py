"""
TennisLab Core Physics & Environmental Dynamics Engine
======================================================
한국체육산업개발 올림픽공원 테니스장 코트 환경 동역학 및 물리 시뮬레이션 엔진

주요 기능:
1. 풍향·풍속 벡터 분해 (Court-Aligned Wind Vector Decomposition)
2. 공기역학 모델 기반 볼 비거리/체공시간/좌우 궤적 편차 계산
3. 기온·습도 연계 하드코트 볼 반발계수(COR) 및 바운스 높이 추정
4. 태양 방위각/고도각 기반 서브 눈부심(Sun Glare) 지수 산출
5. 실시간 전술 및 플레이 가이드 생성
"""

import math
from typing import Dict, Any, Tuple


class TennisPhysicsEngine:
    """테니스 공 동역학 및 코트 환경 분석 엔진"""

    # 물리 상수 및 테니스공 규격 (ITF 규정 기준)
    BALL_MASS = 0.0577          # 질량 (kg, 약 57.7g)
    BALL_DIAMETER = 0.067       # 지름 (m, 6.7cm)
    BALL_AREA = math.pi * (BALL_DIAMETER / 2) ** 2  # 단면적 (m^2)
    DRAG_COEFF = 0.55           # 테니스공 항력계수 (Cd, 펠트 재질 고려)
    STANDARD_TEMP = 20.0        # 기준 온도 (섭씨)
    BASE_COR_HARD = 0.745       # 20도 기준 하드코트 반발계수 (COR: 0.73~0.76)
    DROP_HEIGHT = 2.54          # ITF 바운스 측정 기준 낙하 높이 (100인치, m)

    @classmethod
    def calculate_air_density(cls, temperature_c: float, humidity_pct: float = 50.0, pressure_hpa: float = 1013.25) -> float:
        """
        온도, 습도, 기압에 따른 공기 밀도(kg/m^3) 계산
        """
        temp_k = temperature_c + 273.15
        p_dry = (pressure_hpa * 100) / (287.058 * temp_k)
        # 습도에 따른 수증기압 보정
        sat_vapor_press = 6.1078 * (10 ** ((7.5 * temperature_c) / (237.3 + temperature_c))) * 100
        vapor_press = sat_vapor_press * (humidity_pct / 100.0)
        air_density = ((pressure_hpa * 100 - vapor_press) / (287.058 * temp_k)) + (vapor_press / (461.495 * temp_k))
        return round(air_density, 4)

    @staticmethod
    def player_heading_deg(court_orientation_deg: float, player_side: str = "West") -> float:
        """
        플레이어가 바라보는 방위각.
        West(또는 구 코드 South): 서쪽 엔드에서 장축 방향(올림픽공원 117°)을 봄.
        East(또는 구 코드 North): 반대 엔드(297°)를 봄.
        """
        side = (player_side or "West").strip().lower()
        if side in {"east", "north", "e", "n"}:
            return (court_orientation_deg + 180.0) % 360.0
        return court_orientation_deg % 360.0

    @classmethod
    def decompose_wind(cls, wind_speed_ms: float, wind_dir_deg: float, court_orientation_deg: float, player_side: str = "West") -> Dict[str, Any]:
        """
        기상청 풍향/풍속을 코트 축 기준(맞바람/뒷바람, 좌/우 측풍)으로 벡터 분해
        
        Args:
            wind_speed_ms: 풍속 (m/s)
            wind_dir_deg: 풍향 (0~360도, 북풍=0, 동풍=90, 남풍=180, 서풍=270)
            court_orientation_deg: 코트 장축 방향 (올림픽공원 실측 117도, ESE)
            player_side: "West" 서쪽 엔드 / "East" 동쪽 엔드 (South/North는 호환 별칭)
        """
        heading_deg = cls.player_heading_deg(court_orientation_deg, player_side)

        # 바람이 불어오는 방향과 플레이어 시선의 상대 각도
        rel_angle_deg = (wind_dir_deg - heading_deg) % 360
        rel_rad = math.radians(rel_angle_deg)

        # 종방향 바람 (Longitudinal wind): cos(rel_rad)
        # cos(0도) = 정면 맞바람 (Headwind)
        # cos(180도) = 등 뒤 뒷바람 (Tailwind)
        headwind_comp = -wind_speed_ms * math.cos(rel_rad)  # 양수: 뒷바람, 음수: 맞바람
        
        # 횡방향 바람 (Lateral crosswind): sin(rel_rad)
        # sin > 0: 우측에서 불어옴 (공이 좌측으로 밀림)
        # sin < 0: 좌측에서 불어옴 (공이 우측으로 밀림)
        crosswind_comp = wind_speed_ms * math.sin(rel_rad)

        return {
            "wind_speed_ms": wind_speed_ms,
            "wind_dir_deg": wind_dir_deg,
            "relative_angle_deg": round(rel_angle_deg, 1),
            "tail_head_wind_ms": round(headwind_comp, 2),   # +: 뒷바람(Tail), -: 맞바람(Head)
            "cross_wind_ms": round(crosswind_comp, 2),       # +: 우측풍, -: 좌측풍
            "wind_type_korean": cls._get_wind_description(headwind_comp, crosswind_comp)
        }

    @staticmethod
    def _get_wind_description(tail_head: float, cross: float) -> str:
        """바람 성분을 직관적인 한국어로 변환"""
        parts = []
        if abs(tail_head) >= 0.5:
            parts.append(f"{'뒷바람' if tail_head > 0 else '맞바람'} ({abs(tail_head):.1f}m/s)")
        if abs(cross) >= 0.5:
            parts.append(f"{'우측풍' if cross > 0 else '좌측풍'} ({abs(cross):.1f}m/s)")
        return " + ".join(parts) if parts else "미풍/고요함 (영향 미미)"

    @classmethod
    def simulate_ball_trajectory(cls, shot_speed_kmh: float, wind_decomp: Dict[str, Any], temp_c: float = 20.0, shot_type: str = "rally") -> Dict[str, Any]:
        """
        바람과 기온에 따른 스트로크 비거리 및 좌우 궤적 편차 시뮬레이션
        
        Args:
            shot_speed_kmh: 스트로크 속도 (km/h, 평균 랠리: 80~100km/h, 서브: 130~170km/h)
            wind_decomp: decompose_wind 결과 딕셔너리
            temp_c: 기온
            shot_type: "rally" (스트로크) 또는 "serve" (서브)
        """
        speed_ms = shot_speed_kmh / 3.6
        flight_time_s = 0.75 if shot_type == "rally" else 0.55  # 평균 체공시간
        
        air_density = cls.calculate_air_density(temp_c)
        air_density_ratio = air_density / 1.204  # 20도 기준 공기밀도 비

        tail_head_wind = wind_decomp["tail_head_wind_ms"]
        cross_wind = wind_decomp["cross_wind_ms"]

        # 공기 저항(항력)에 의한 바람 영향도 계산
        # 비거리 변화량 (cm 단위): 뒷바람은 비거리 증가, 맞바람은 비거리 감소
        delta_distance_cm = (tail_head_wind * flight_time_s * 55.0) * air_density_ratio
        
        # 좌우 밀림 편차 (cm 단위): 우측풍은 왼쪽으로 밀림(-)
        delta_lateral_cm = (-cross_wind * flight_time_s * 48.0) * air_density_ratio

        return {
            "shot_type": shot_type,
            "nominal_speed_kmh": shot_speed_kmh,
            "flight_time_sec": flight_time_s,
            "air_density_kg_m3": air_density,
            "distance_delta_cm": round(delta_distance_cm, 1),   # +: 길어짐(Out 위험), -: 짧아짐(Net 위험)
            "lateral_delta_cm": round(delta_lateral_cm, 1),     # +: 오른쪽으로 밀림, -: 왼쪽으로 밀림
            "trajectory_impact_summary": cls._get_trajectory_summary(delta_distance_cm, delta_lateral_cm)
        }

    @staticmethod
    def _get_trajectory_summary(dist_delta: float, lat_delta: float) -> str:
        desc = []
        if dist_delta > 15:
            desc.append(f"공이 평소보다 약 {abs(dist_delta):.0f}cm 길게 날아가 아웃(Out) 위험 높음")
        elif dist_delta < -15:
            desc.append(f"공이 평소보다 약 {abs(dist_delta):.0f}cm 짧아져 네트(Net) 걸릴 위험 높음")
        else:
            desc.append("비거리 편차 안정권 (±15cm 이내)")

        if abs(lat_delta) > 10:
            side = "오른쪽" if lat_delta > 0 else "왼쪽"
            desc.append(f"{side}으로 약 {abs(lat_delta):.0f}cm 휨 발생")

        return " | ".join(desc)

    @classmethod
    def calculate_court_bounce(cls, temp_c: float, humidity_pct: float = 50.0) -> Dict[str, Any]:
        """
        기온 및 습도에 따른 올림픽공원 하드코트 볼 바운스 반발계수(COR) 및 바운스 높이 계산
        - 기온 1도 상승 시 볼 내부 공기압 약 0.35% 증가 -> COR 상승
        - 하드코트 표면 온도는 직사광선 시 기온 + 5~10도 상승
        """
        temp_delta = temp_c - cls.STANDARD_TEMP
        
        # 온도 변화에 따른 COR 보정 (1도당 약 0.0018 변화)
        cor = cls.BASE_COR_HARD + (temp_delta * 0.0018)
        cor = max(0.68, min(0.80, cor))  # 유효 범위 클램핑

        # 2.54m(ITF 기준 100인치)에서 낙하 시 바운스 높이: h = H * e^2
        bounce_height_m = cls.DROP_HEIGHT * (cor ** 2)
        base_bounce_m = cls.DROP_HEIGHT * (cls.BASE_COR_HARD ** 2)
        bounce_diff_cm = (bounce_height_m - base_bounce_m) * 100

        # 체감 코트 스피드 (CPR: Court Pace Rating 간이 추정)
        # 온도가 높을수록 공이 빠르게 튀어 Fast 코트 성향을 띰
        pace_label = "Medium (표준)"
        if cor >= 0.76:
            pace_label = "Fast (고탄성/빠른 바운스)"
        elif cor <= 0.72:
            pace_label = "Slow (저탄성/묵직한 바운스)"

        return {
            "ambient_temp_c": temp_c,
            "cor": round(cor, 3),
            "bounce_height_m": round(bounce_height_m, 2),
            "bounce_diff_from_standard_cm": round(bounce_diff_cm, 1),
            "court_pace_label": pace_label
        }

    @classmethod
    def calculate_sun_glare(cls, hour_24: int, court_orientation_deg: float, player_side: str = "West") -> Dict[str, Any]:
        """
        시간대별 태양 위치(방위각/고도각 간이 추산) 및 서브 토스 시 눈부심(Sun Glare) 위험도 산출
        """
        # 서울 위도(37.5도) 기준 간이 태양 궤적 모델
        if hour_24 < 6 or hour_24 > 19:
            return {"sun_visible": False, "glare_risk": "None (야간/조명 경기)"}

        # 정오(12시) 기준 태양 방위각 약 180도(정남향)
        sun_azimuth = 90 + (hour_24 - 6) * 15  # 대략 6시=90도, 12시=180도, 18시=270도
        # 태양 고도각 (정오에 최대 약 50~65도)
        sun_altitude = math.sin(math.radians((hour_24 - 6) * 15)) * 60

        # 서브 토스 시선: 서쪽 엔드=117°(오전 태양과 겹침), 동쪽 엔드=297°(오후 태양과 겹침)
        target_azimuth = cls.player_heading_deg(court_orientation_deg, player_side)
        angle_diff = abs(sun_azimuth - target_azimuth)
        angle_diff = min(angle_diff, 360 - angle_diff)

        # 토스 시야각(시선 40~70도 상공, 방위각 차이 30도 이내일 때 눈부심 극심)
        if angle_diff <= 35 and 20 <= sun_altitude <= 70:
            glare_risk = "HIGH (서브 토스 시 태양 직시 위험! 선글라스/모자 필수)"
        elif angle_diff <= 60 and 15 <= sun_altitude <= 75:
            glare_risk = "MEDIUM (부분 눈부심 발생)"
        else:
            glare_risk = "LOW (시야 양호)"

        return {
            "sun_visible": True,
            "sun_altitude_deg": round(sun_altitude, 1),
            "sun_azimuth_deg": round(sun_azimuth, 1),
            "glare_risk": glare_risk
        }

    @classmethod
    def generate_tactical_briefing(cls, wind_decomp: Dict[str, Any], trajectory: Dict[str, Any], bounce: Dict[str, Any], glare: Dict[str, Any], court_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        모든 환경 요인을 종합한 AI 플레이어 맞춤형 전술 브리핑
        """
        zone = court_info.get("zone", "outdoor")
        if court_info.get("has_roof", False) or zone == "indoor":
            return {
                "court_status": "실내 코트",
                "summary": "외부 바람과 직사광선이 차단된 전천후 코트입니다.",
                "tactics": [
                    "유효 바람은 0입니다. 평소 타점과 궤적으로 치세요.",
                    f"실내 기온 기준 바운스는 '{bounce['court_pace_label']}' 입니다.",
                    "강풍·눈부심이 없는 날의 안정 코트로 안내합니다."
                ],
                "recommended_side": "어느 엔드든 같습니다"
            }

        tactics = []
        tail_head = wind_decomp["tail_head_wind_ms"]
        cross = wind_decomp["cross_wind_ms"]
        if zone == "stadium":
            tactics.append("🏟️ [메인 스타디움]: 스탠드가 열린 바람을 일부 막습니다(간이 ×0.75). 측면 와류가 있어 네트 근처 볼이 흔들릴 수 있습니다.")
        elif zone == "roadside":
            tactics.append("🚗 [도로변]: 장축은 117°로 같습니다. 도로 쪽 열린 바람과 차량 소음이 큽니다. 토스·리턴 리듬을 짧게 가져가세요.")
        elif zone == "desk":
            tactics.append("📍 [회원안내실 인근]: 실외 일반 코트입니다. 장축 117°, 바람은 기상청 실황을 그대로 씁니다.")
        elif zone == "near_main":
            tactics.append("📍 [메인코트 인근]: 실외 일반 코트입니다. 장축 117°, 바람은 기상청 실황을 그대로 씁니다.")

        # 1. 바람 전술
        if tail_head <= -1.0:
            tactics.append("🌪️ [맞바람]: 공이 네트에 걸리기 쉽습니다. 타점을 평소보다 10cm 높이고 깊은 헤비 탑스핀으로 네트 클리어런스(여유 높이)를 1m 이상 확보하세요.")
        elif tail_head >= 1.0:
            tactics.append("🚀 [뒷바람]: 베이스라인 아웃 위험이 매우 높습니다. 풀스윙 오버파워를 자제하고, 상대방이 짧은 볼에 대비하기 어렵도록 짧은 드롭샷이나 슬라이스를 섞으세요.")

        if abs(cross) >= 1.0:
            side = "왼쪽" if cross > 0 else "오른쪽"
            tactics.append(f"💨 [측풍 주의]: 공이 {side}으로 밀립니다. 와이드 서브 구사 시 바람 방향을 활용하면 상대 리턴을 코트 밖으로 유도할 수 있습니다.")

        # 2. 바운스 전술
        if bounce["cor"] >= 0.76:
            tactics.append("⚡ [고탄성 바운스]: 코트 표면 온도가 높아 바운스가 높고 빠릅니다. 라이징 볼(정점 전 타격)을 치거나 물러서서 타점을 잡으세요.")
        elif bounce["cor"] <= 0.72:
            tactics.append("❄️ [저탄성 바운스]: 날씨가 쌀쌀하여 공이 낮게 튀므로, 무릎을 충분히 굽히고 낮은 자세를 유지하세요.")

        # 3. 눈부심 전술
        if "HIGH" in glare.get("glare_risk", ""):
            tactics.append("☀️ [서브 눈부심 주의]: 토스 시 태양과 시선이 겹칩니다. 토스 위치를 평소보다 살짝 오른쪽(또는 왼쪽)으로 틀어서 올리세요.")

        if not tactics:
            tactics.append("쾌적한 기상 조건입니다. 기본 전술에 충실하게 플레이하세요.")

        return {
            "court_status": "실외 하드 코트 (Outdoor)",
            "summary": f"{wind_decomp['wind_type_korean']} | 바운스: {bounce['court_pace_label']}",
            "tactics": tactics,
            "recommended_side": "바람을 등지는 엔드(뒷바람)가 공격적인 서브 및 랠리 주도권에 유리합니다." if tail_head < 0 else "맞바람 엔드에서는 안정적인 스트로크 유지에 집중하세요."
        }
