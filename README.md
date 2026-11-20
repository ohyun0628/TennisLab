# TennisLab (테니스 랩)

> 올림픽공원 테니스장 **실시간 기상·코트 축 기준 플레이 가이드**  
> 2026 한국체육산업개발(주) 공공데이터 활용 경진대회 출품

기상청 실황과 19개 코트의 실측 장축(**117°**)을 결합해, 오늘 이 코트·이 엔드에서 바람이 공에 어떻게 먹는지 보여 줍니다. 한국체육산업개발 **월별 이용 통계**와 **공식 예약**으로 연결합니다.

📄 [출품 기획서](docs/proposal.md)

---

## 무엇을 하나요

이용자가 코트를 고르면 앱이 하는 일은 세 가지입니다.

1. **지금 날씨** — 기상청 초단기실황 (올림픽공원 격자 62, 125)
2. **그 코트 기준 체감** — 장축이 동서 117°라서 서쪽/동쪽 엔드의 맞바람·뒷바람이 반대. 실내(5~8번)는 바람 0
3. **짧은 플레이 가이드** — 비거리·휨 추정, 바운스, 서브 눈부심, 공식 예약 링크

실시간 빈 코트 조회는 공개 API가 없어서 하지 않습니다.

---

## 데이터

| 구분 | 내용 |
| :--- | :--- |
| 주관기관 | [테니스장 이용 정보](https://www.data.go.kr/data/15133891/fileData.do) (15133891). 월별 일일입장·월회원, **2021.01~2025.12**, 연 1회 갱신 |
| 주관기관 부가 | [공식 코트 배치도](https://www.ksponco.or.kr/sports/img/olparktennis/plot_plan.jpg) (1 메인, 5~8 실내, 2~4·9~19 실외), [공식 예약](https://www.ksponco.or.kr/online/tennis/index.do) |
| 타 기관 | 기상청 초단기실황. 실패 시 Open-Meteo |
| 방위각 | 공공 API 없음. OSM 센터코트 폴리곤 + 위성 실측 **117° / 297°** (`data/court_azimuth_source.json`) |

코트 번호는 KSPO 공식 배치도를 따릅니다.

---

## 실행

키는 프로젝트 루트 `.env` 또는 `mobile/.env`에 둡니다. git에 올리지 않습니다.

```
KMA_SERVICE_KEY=     # data.go.kr 일반 인증키(Decoding)
EXPO_PUBLIC_KMA_KEY= # 모바일용 같은 키
```

### 웹 (Streamlit)

```bash
pip install -r requirements.txt
python -m streamlit run src/app.py
```

브라우저 `http://localhost:8501`

### 모바일 (Expo)

```bash
cd mobile
npm install
npx expo start
```

Expo Go는 **SDK 58**이어야 합니다. 자세한 내용은 [mobile/README.md](mobile/README.md).

---

## 프로젝트 구조

```text
TennisLab/
├── docs/proposal.md                 # 출품 기획서
├── data/
│   ├── olympic_courts.json          # 19개 코트 (공식 번호, 장축 117°)
│   ├── court_azimuth_source.json    # 방위각 실측 근거
│   ├── kspo_plot_plan.jpg           # KSPO 공식 배치도
│   └── kspo_tennis_usage_20251231.csv
├── src/
│   ├── app.py                       # Streamlit 웹
│   ├── server.py                    # FastAPI (선택)
│   ├── api/weather.py               # 기상청 실황
│   ├── api/kspo_usage.py            # 월별 이용 15133891
│   └── engine/physics.py            # 풍향 분해·간이 궤적
└── mobile/                          # Expo 앱
```

---

## 하지 않는 것

- 코트별 실시간 예약 슬롯, 예약 사이트 스크래핑
- 학습된 머신러닝 추천, 취소율·가동률 개선 수치 주장
- 방위각을 공공 API에서 받은 것처럼 표기

안내 문장과 추천은 **규칙 기반**입니다. 궤적·바운스는 **간이 추정**입니다.
