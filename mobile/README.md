# TennisLab Mobile (Expo)

올림픽공원 테니스장 실시간 기상·코트 축 가이드. 웹과 같은 데이터(기상청 실황, 장축 117°, 월별 이용, 공식 예약)를 폰에서 봅니다.

## 실행

```bash
cd mobile
npm install
npx expo start
```

1. 스마트폰에 **Expo Go (SDK 58)** 을 설치합니다.
2. 폰과 PC를 같은 Wi-Fi에 둡니다.
3. 터미널 QR을 Expo Go로 스캔합니다.

`mobile/.env`에 `EXPO_PUBLIC_KMA_KEY=` (data.go.kr 일반 인증키)를 넣습니다. 이 파일은 git에 올리지 않습니다.

스토어 Expo Go는 SDK 58만 지원합니다. 예전 SDK 51 프로젝트는 QR을 찍으면 바로 닫힙니다.
