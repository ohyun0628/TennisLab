const SERVICE_KEY = process.env.EXPO_PUBLIC_KMA_KEY || '';
const USAGE_URL =
  'https://api.odcloud.kr/api/15133891/v1/uddi:727042a0-87e3-4bd0-9d33-e3f97e00bba6';

export const RESERVE_URL = 'https://www.ksponco.or.kr/online/tennis/index.do';

function field(row, ...names) {
  for (const name of names) {
    if (row[name] != null && row[name] !== '') return row[name];
  }
  return null;
}

function parseRows(rows) {
  return rows
    .map((row) => {
      const start = String(field(row, '시작일', 'startdate') || '');
      const type = String(field(row, '구분', 'code') || '');
      const count = Number(field(row, '이용자수', 'member') || 0);
      const match = start.match(/^(\d{4})-(\d{2})/);
      if (!match || !type || Number.isNaN(count)) return null;
      return {
        type,
        start,
        year: Number(match[1]),
        month: Number(match[2]),
        count
      };
    })
    .filter(Boolean);
}

function pickPeriod(items) {
  const now = new Date();
  const thisMonth = now.getMonth() + 1;
  const sameMonth = items.filter((item) => item.month === thisMonth);
  const pool = sameMonth.length ? sameMonth : items;
  return pool.reduce((latest, item) => (item.start > latest.start ? item : latest), pool[0]);
}

function formatCount(value) {
  return Number(value || 0).toLocaleString('ko-KR');
}

export function summarizeUsage(rows) {
  const items = parseRows(rows);
  if (!items.length) {
    throw new Error('empty usage');
  }

  const period = pickPeriod(items);
  const daily = items.find((item) => item.year === period.year && item.month === period.month && item.type === '일일입장');
  const member = items.find((item) => item.year === period.year && item.month === period.month && item.type === '월회원');
  const prevDaily = items.find((item) => item.year === period.year - 1 && item.month === period.month && item.type === '일일입장');

  const dailyCount = daily ? daily.count : 0;
  const memberCount = member ? member.count : 0;
  const prevCount = prevDaily ? prevDaily.count : null;
  const yoy = prevCount ? Math.round(((dailyCount - prevCount) / prevCount) * 100) : null;

  const dailyAll = items.filter((item) => item.type === '일일입장').map((item) => item.count);
  const avg = dailyAll.reduce((sum, value) => sum + value, 0) / dailyAll.length;
  const busyLabel = dailyCount >= avg * 1.15 ? '혼잡' : dailyCount <= avg * 0.85 ? '한산' : '보통';

  return {
    periodLabel: `${period.year}년 ${period.month}월`,
    dailyCount,
    memberCount,
    totalCount: dailyCount + memberCount,
    dailyLabel: `${formatCount(dailyCount)}명`,
    memberLabel: `${formatCount(memberCount)}명`,
    totalLabel: `${formatCount(dailyCount + memberCount)}명`,
    yoy,
    yoyLabel: yoy == null ? '전년 동월 비교 없음' : `전년 동월 대비 ${yoy > 0 ? '+' : ''}${yoy}%`,
    busyLabel,
    sourceLabel: '한국체육산업개발 테니스장 이용 정보',
    isLive: true
  };
}

export async function fetchUsageSummary() {
  if (!SERVICE_KEY) {
    throw new Error('missing service key');
  }
  const response = await fetch(`${USAGE_URL}?page=1&perPage=120&serviceKey=${SERVICE_KEY}`);
  if (!response.ok) {
    throw new Error(`HTTP ${response.status}`);
  }
  const payload = await response.json();
  const rows = payload?.data;
  if (!Array.isArray(rows) || !rows.length) {
    throw new Error('usage empty');
  }
  return summarizeUsage(rows);
}
