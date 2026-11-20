const OLYMPIC = {
  lat: 37.5208,
  lon: 127.1215,
  nx: 62,
  ny: 125
};

const WIND_DIRS = [
  '북', '북북동', '북동', '동북동',
  '동', '동남동', '남동', '남남동',
  '남', '남남서', '남서', '서남서',
  '서', '서북서', '북서', '북북서'
];

function round1(value) {
  return Math.round(Number(value) * 10) / 10;
}

function round2(value) {
  return Math.round(Number(value) * 100) / 100;
}

export function formatWindDir(deg) {
  const degree = ((Number(deg) % 360) + 360) % 360;
  const idx = Math.round(degree / 22.5) % 16;
  return `${WIND_DIRS[idx]} (${Math.round(degree)}°)`;
}

function kmaBaseDateTime(now = new Date()) {
  const shifted = new Date(now.getTime() - 40 * 60 * 1000);
  const year = shifted.getFullYear();
  const month = String(shifted.getMonth() + 1).padStart(2, '0');
  const day = String(shifted.getDate()).padStart(2, '0');
  const hour = String(shifted.getHours()).padStart(2, '0');
  return { baseDate: `${year}${month}${day}`, baseTime: `${hour}00` };
}

async function fetchWithTimeout(url, ms = 8000) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), ms);
  try {
    const response = await fetch(url, { signal: controller.signal });
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }
    return await response.json();
  } finally {
    clearTimeout(timer);
  }
}

async function fetchKma(serviceKey) {
  const { baseDate, baseTime } = kmaBaseDateTime();
  const query = new URLSearchParams({
    pageNo: '1',
    numOfRows: '10',
    dataType: 'JSON',
    base_date: baseDate,
    base_time: baseTime,
    nx: String(OLYMPIC.nx),
    ny: String(OLYMPIC.ny)
  });
  const url = `https://apis.data.go.kr/1360000/VilageFcstInfoService_2.0/getUltraSrtNcst?serviceKey=${serviceKey}&${query.toString()}`;
  const data = await fetchWithTimeout(url);
  const items = data?.response?.body?.items?.item;
  if (!items || !items.length) {
    throw new Error('KMA empty');
  }

  const parsed = { temp: 18, windSpeed: 2.5, windDirDeg: 350, humidity: 55, rainMm: 0 };
  for (const item of items) {
    const value = parseFloat(item.obsrValue);
    if (Number.isNaN(value)) continue;
    if (item.category === 'T1H') parsed.temp = value;
    if (item.category === 'WSD') parsed.windSpeed = value;
    if (item.category === 'VEC') parsed.windDirDeg = value;
    if (item.category === 'REH') parsed.humidity = value;
    if (item.category === 'RN1') parsed.rainMm = value;
  }

  return {
    temp: round1(parsed.temp),
    windSpeed: round1(parsed.windSpeed),
    windDirDeg: parsed.windDirDeg,
    windDir: formatWindDir(parsed.windDirDeg),
    humidity: Math.round(parsed.humidity),
    rainMm: parsed.rainMm,
    timestamp: new Date().toLocaleString('ko-KR', { hour: '2-digit', minute: '2-digit' }),
    source: 'kma',
    sourceLabel: '올림픽공원 실시간 기상 (기상청 초단기실황)',
    isLive: true
  };
}

async function fetchOpenMeteo() {
  const url = `https://api.open-meteo.com/v1/forecast?latitude=${OLYMPIC.lat}&longitude=${OLYMPIC.lon}&current=temperature_2m,relative_humidity_2m,wind_speed_10m,wind_direction_10m,precipitation&wind_speed_unit=ms&timezone=Asia%2FSeoul`;
  const data = await fetchWithTimeout(url);
  const current = data?.current;
  if (!current) {
    throw new Error('Open-Meteo empty');
  }

  const timeLabel = String(current.time || '').replace('T', ' ');
  return {
    temp: round1(current.temperature_2m),
    windSpeed: round1(current.wind_speed_10m),
    windDirDeg: current.wind_direction_10m,
    windDir: formatWindDir(current.wind_direction_10m),
    humidity: Math.round(current.relative_humidity_2m),
    rainMm: current.precipitation || 0,
    timestamp: timeLabel,
    source: 'open-meteo',
    sourceLabel: '올림픽공원 실시간 기상',
    isLive: true
  };
}

export async function fetchLiveWeather() {
  const serviceKey = process.env.EXPO_PUBLIC_KMA_KEY;
  if (serviceKey) {
    try {
      return await fetchKma(serviceKey);
    } catch (error) {
      console.warn('[weather] 기상청 API 실패, 실시간 관측으로 전환', error);
    }
  }
  return fetchOpenMeteo();
}

export function decomposeWind(windSpeed, windDirDeg, courtOrientationDeg = 117, playerSide = 'West') {
  const facesOrientation = playerSide === 'West' || playerSide === 'South';
  const heading = facesOrientation ? courtOrientationDeg : (courtOrientationDeg + 180) % 360;
  let relative = (Number(windDirDeg) - heading) % 360;
  if (relative < 0) relative += 360;
  const radians = (relative * Math.PI) / 180;
  return {
    tailHeadWind: round2(-Number(windSpeed) * Math.cos(radians)),
    crossWind: round2(Number(windSpeed) * Math.sin(radians))
  };
}

export function bounceFromTemp(tempC) {
  const cor = Math.max(0.68, Math.min(0.8, 0.745 + (Number(tempC) - 20) * 0.0018));
  return {
    cor: Number(cor.toFixed(3)),
    bounceHeight: Number((2.54 * cor * cor).toFixed(2)),
    paceLabel: cor >= 0.76 ? 'Fast 코트' : cor <= 0.72 ? 'Slow 코트' : 'Medium 코트'
  };
}
