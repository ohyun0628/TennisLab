import React, { useState, useEffect, useCallback } from 'react';
import {
  StyleSheet,
  Text,
  View,
  ScrollView,
  TouchableOpacity,
  SafeAreaView,
  StatusBar,
  ActivityIndicator,
  RefreshControl,
  Linking
} from 'react-native';
import { bounceFromTemp, decomposeWind, fetchLiveWeather } from './weather';
import { fetchUsageSummary, RESERVE_URL } from './usage';

// 올림픽공원 19개 코트 기본 메타데이터
const COURTS = [
  { id: 1, name: '메인 코트', type: 'stadium', isIndoor: false, orientationDeg: 117, desc: '메인 스타디움. 높은 스탠드 와류 주의.' },
  { id: 2, name: '2번 코트', type: 'outdoor', isIndoor: false, orientationDeg: 117, desc: '실외 하드코트. 회원안내실 인근.' },
  { id: 3, name: '3번 코트', type: 'outdoor', isIndoor: false, orientationDeg: 117, desc: '실외 하드코트. 회원안내실 인근.' },
  { id: 4, name: '4번 코트', type: 'outdoor', isIndoor: false, orientationDeg: 117, desc: '실외 하드코트. 회원안내실 인근.' },
  { id: 5, name: '실내 5번', type: 'indoor', isIndoor: true, orientationDeg: 117, desc: '실내 전천후 하드코트.' },
  { id: 6, name: '실내 6번', type: 'indoor', isIndoor: true, orientationDeg: 117, desc: '실내 전천후 하드코트.' },
  { id: 7, name: '실내 7번', type: 'indoor', isIndoor: true, orientationDeg: 117, desc: '실내 전천후 하드코트.' },
  { id: 8, name: '실내 8번', type: 'indoor', isIndoor: true, orientationDeg: 117, desc: '실내 전천후 하드코트.' },
  { id: 9, name: '9번 코트', type: 'outdoor', isIndoor: false, orientationDeg: 117, desc: '실외 하드코트. 도로변 동측.' },
  { id: 10, name: '10번 코트', type: 'outdoor', isIndoor: false, orientationDeg: 117, desc: '실외 하드코트. 도로변 동측.' },
  { id: 11, name: '11번 코트', type: 'outdoor', isIndoor: false, orientationDeg: 117, desc: '실외 하드코트. 도로변 동측.' },
  { id: 12, name: '12번 코트', type: 'outdoor', isIndoor: false, orientationDeg: 117, desc: '실외 하드코트. 도로변 동측.' },
  { id: 13, name: '13번 코트', type: 'outdoor', isIndoor: false, orientationDeg: 117, desc: '실외 하드코트. 도로변 동측.' },
  { id: 14, name: '14번 코트', type: 'outdoor', isIndoor: false, orientationDeg: 117, desc: '실외 하드코트. 도로변 동측.' },
  { id: 15, name: '15번 코트', type: 'outdoor', isIndoor: false, orientationDeg: 117, desc: '실외 하드코트. 도로변 동측.' },
  { id: 16, name: '16번 코트', type: 'outdoor', isIndoor: false, orientationDeg: 117, desc: '실외 하드코트. 도로변 동측.' },
  { id: 17, name: '17번 코트', type: 'outdoor', isIndoor: false, orientationDeg: 117, desc: '실외 하드코트. 도로변 동측.' },
  { id: 18, name: '18번 코트', type: 'outdoor', isIndoor: false, orientationDeg: 117, desc: '실외 하드코트. 메인코트 인근.' },
  { id: 19, name: '19번 코트', type: 'outdoor', isIndoor: false, orientationDeg: 117, desc: '실외 하드코트. 메인코트 인근.' }
];

export default function App() {
  const [selectedCourt, setSelectedCourt] = useState(COURTS[0]);
  const [playerSide, setPlayerSide] = useState('West');
  const [weather, setWeather] = useState({
    temp: null,
    windSpeed: null,
    windDir: '--',
    windDirDeg: 0,
    humidity: null,
    timestamp: '',
    sourceLabel: '올림픽공원 실시간 기상',
    isLive: false
  });
  const [usage, setUsage] = useState(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  const loadLiveData = useCallback(async (isRefresh = false) => {
    if (isRefresh) setRefreshing(true);
    try {
      const [live, usageSummary] = await Promise.all([
        fetchLiveWeather(),
        fetchUsageSummary().catch((error) => {
          console.warn('[App] 이용 정보 불러오기 실패', error);
          return null;
        })
      ]);
      setWeather(live);
      if (usageSummary) setUsage(usageSummary);
    } catch (error) {
      console.warn('[App] 실시간 데이터 불러오기 실패', error);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    loadLiveData();
    const timer = setInterval(() => loadLiveData(), 10 * 60 * 1000);
    return () => clearInterval(timer);
  }, [loadLiveData]);

  const isIndoor = selectedCourt.isIndoor;
  const { tailHeadWind } = decomposeWind(
    Number(weather.windSpeed) || 0,
    Number(weather.windDirDeg) || 0,
    selectedCourt.orientationDeg || 117,
    playerSide
  );
  const liveTailHead = isIndoor ? 0 : tailHeadWind;
  const deltaDistance = isIndoor ? 0 : Math.round(liveTailHead * 0.75 * 55.0);
  const bounce = bounceFromTemp(Number(weather.temp) || 18);
  const bounceHeight = isIndoor ? Number((bounce.bounceHeight - 0.02).toFixed(2)) : bounce.bounceHeight;

  return (
    <SafeAreaView style={styles.container}>
      <StatusBar barStyle="light-content" backgroundColor="#1E3A8A" />

      {/* 헤더 */}
      <View style={styles.header}>
        <View>
          <Text style={styles.headerTitle}>🎾 TennisLab Mobile</Text>
          <Text style={styles.headerSubtitle}>올림픽공원 테니스장 실시간 코트 가이드</Text>
        </View>
        <View style={[styles.liveBadge, weather.isLive ? styles.liveBadgeOn : styles.liveBadgeOff]}>
          <Text style={styles.liveBadgeText}>{weather.isLive ? '● LIVE' : '● ...'}</Text>
        </View>
      </View>

      <ScrollView
        contentContainerStyle={styles.scrollContent}
        showsVerticalScrollIndicator={false}
        refreshControl={
          <RefreshControl
            refreshing={refreshing}
            onRefresh={() => loadLiveData(true)}
            tintColor="#1E3A8A"
          />
        }
      >
        {/* 기상 요약 카드 */}
        <View style={styles.weatherCard}>
          <Text style={styles.cardHeaderTitle}>🌤️ {weather.sourceLabel}</Text>
          {loading ? (
            <ActivityIndicator color="#1E3A8A" style={{ marginVertical: 12 }} />
          ) : (
            <>
              <View style={styles.weatherRow}>
                <View style={styles.weatherItem}>
                  <Text style={styles.weatherLabel}>기온</Text>
                  <Text style={styles.weatherValue}>{weather.temp}℃</Text>
                </View>
                <View style={styles.weatherDivider} />
                <View style={styles.weatherItem}>
                  <Text style={styles.weatherLabel}>풍속</Text>
                  <Text style={styles.weatherValue}>{weather.windSpeed} m/s</Text>
                </View>
                <View style={styles.weatherDivider} />
                <View style={styles.weatherItem}>
                  <Text style={styles.weatherLabel}>풍향</Text>
                  <Text style={styles.weatherValue}>{weather.windDir}</Text>
                </View>
              </View>
              <Text style={styles.weatherMeta}>
                {weather.timestamp ? `${weather.timestamp} 갱신` : '실시간 조회'}
                {weather.humidity != null ? ` · 습도 ${weather.humidity}%` : ''}
              </Text>
            </>
          )}
        </View>

        {/* 19개 코트 가로 스크롤 선택기 */}
        <Text style={styles.sectionTitle}>🎯 코트 선택 (총 19개 코트)</Text>
        <ScrollView horizontal showsHorizontalScrollIndicator={false} style={styles.courtScroll}>
          {COURTS.map((court) => {
            const isSelected = selectedCourt.id === court.id;
            return (
              <TouchableOpacity
                key={court.id}
                style={[
                  styles.courtChip,
                  isSelected && styles.courtChipSelected,
                  court.isIndoor && !isSelected && styles.courtChipIndoor
                ]}
                onPress={() => setSelectedCourt(court)}
              >
                <Text style={[styles.courtChipText, isSelected && styles.courtChipTextSelected]}>
                  {court.name}
                </Text>
                <Text style={[styles.courtChipSub, isSelected && styles.courtChipTextSelected]}>
                  {court.isIndoor ? '실내' : (court.id === 1 ? '스타디움' : '실외')}
                </Text>
              </TouchableOpacity>
            );
          })}
        </ScrollView>

        {/* 플레이어 엔드 선택 (West vs East, 장축 117°) */}
        <View style={styles.playerSideRow}>
          <Text style={styles.playerSideLabel}>내 코트 위치:</Text>
          <TouchableOpacity
            style={[styles.sideButton, playerSide === 'West' && styles.sideButtonActive]}
            onPress={() => setPlayerSide('West')}
          >
            <Text style={[styles.sideButtonText, playerSide === 'West' && styles.sideButtonTextActive]}>
              서쪽 (117°)
            </Text>
          </TouchableOpacity>
          <TouchableOpacity
            style={[styles.sideButton, playerSide === 'East' && styles.sideButtonActive]}
            onPress={() => setPlayerSide('East')}
          >
            <Text style={[styles.sideButtonText, playerSide === 'East' && styles.sideButtonTextActive]}>
              동쪽 (297°)
            </Text>
          </TouchableOpacity>
        </View>

        {/* 선택된 코트 물리 동역학 카드 */}
        <View style={styles.physicsCard}>
          <View style={styles.physicsHeader}>
            <Text style={styles.physicsTitle}>{selectedCourt.name} 동역학 분석</Text>
            <View style={[styles.badge, isIndoor ? styles.badgeIndoor : styles.badgeOutdoor]}>
              <Text style={styles.badgeText}>{isIndoor ? '실내 코트' : '실외 하드'}</Text>
            </View>
          </View>

          <Text style={styles.physicsDesc}>
            {selectedCourt.desc} 장축 {selectedCourt.orientationDeg}° (OSM·위성 실측)
          </Text>

          {/* 주요 지표 3열 그리드 */}
          <View style={styles.metricGrid}>
            <View style={styles.metricBox}>
              <Text style={styles.metricLabel}>체감 유효 바람</Text>
              <Text style={[styles.metricValue, { color: isIndoor ? '#10B981' : '#2563EB' }]}>
                {isIndoor ? '0.0 m/s' : `${liveTailHead > 0 ? '+' : ''}${liveTailHead.toFixed(1)}m/s`}
              </Text>
              <Text style={styles.metricSub}>
                {isIndoor ? '바람 차단' : (Math.abs(liveTailHead) < 0.5 ? '미풍' : (liveTailHead > 0 ? '뒷바람 (밀어줌)' : '맞바람 (저항)'))}
              </Text>
            </View>

            <View style={styles.metricBox}>
              <Text style={styles.metricLabel}>볼 비거리 편차</Text>
              <Text style={[styles.metricValue, { color: deltaDistance > 0 ? '#DC2626' : (deltaDistance < 0 ? '#F59E0B' : '#10B981') }]}>
                {deltaDistance > 0 ? `+${deltaDistance}cm` : `${deltaDistance}cm`}
              </Text>
              <Text style={styles.metricSub}>
                {isIndoor ? '안정권' : (deltaDistance > 0 ? '아웃(Out) 주의' : '네트(Net) 주의')}
              </Text>
            </View>

            <View style={styles.metricBox}>
              <Text style={styles.metricLabel}>바운스 높이</Text>
              <Text style={[styles.metricValue, { color: '#8B5CF6' }]}>{bounceHeight}m</Text>
              <Text style={styles.metricSub}>{bounce.paceLabel}</Text>
            </View>
          </View>
        </View>

        {/* AI 전술 가이드 */}
        <View style={styles.tacticsCard}>
          <Text style={styles.tacticsHeader}>🧠 AI 전술 브리핑</Text>
          {isIndoor ? (
            <View style={styles.tacticItem}>
              <Text style={styles.tacticText}>• 실내 코트는 바람 영향이 0이므로, 평소 연습한 표준 타점과 정교한 앵글 샷 전술을 구사하세요.</Text>
            </View>
          ) : (
            <>
              <View style={styles.tacticItem}>
                <Text style={styles.tacticText}>
                  {Math.abs(liveTailHead) < 0.5
                    ? '🍃 [미풍]: 바람 영향이 작습니다. 평소 타점과 궤적으로 안정적으로 플레이하세요.'
                    : liveTailHead < 0
                    ? '🌪️ [맞바람]: 공이 덜 날아갑니다. 타점을 평소보다 10cm 높이고 깊은 탑스핀으로 네트 여유를 확보하세요.'
                    : '🚀 [뒷바람]: 공이 길게 나갑니다. 무리한 풀스윙을 피하고 숏 앵글이나 슬라이스 드롭샷을 적극 활용하세요.'}
                </Text>
              </View>
              <View style={styles.tacticItem}>
                <Text style={styles.tacticText}>
                  {bounce.cor >= 0.76
                    ? '⚡ [고탄성 바운스]: 코트 반발력이 좋아 라이징 볼 타격이 효과적입니다.'
                    : bounce.cor <= 0.72
                    ? '❄️ [저탄성 바운스]: 기온이 낮아 공이 낮게 튑니다. 무릎을 굽히고 낮은 타점에 대비하세요.'
                    : '🎾 [표준 바운스]: 평소 연습한 타점 높이로 플레이하세요.'}
                </Text>
              </View>
            </>
          )}
        </View>

        {/* 한국체육산업개발 이용 정보 */}
        {usage ? (
          <View style={styles.usageCard}>
            <Text style={styles.cardHeaderTitle}>📅 {usage.sourceLabel}</Text>
            <Text style={styles.usagePeriod}>{usage.periodLabel} 공식 이용 통계</Text>
            <View style={styles.weatherRow}>
              <View style={styles.weatherItem}>
                <Text style={styles.weatherLabel}>일일입장</Text>
                <Text style={styles.weatherValue}>{usage.dailyLabel}</Text>
              </View>
              <View style={styles.weatherDivider} />
              <View style={styles.weatherItem}>
                <Text style={styles.weatherLabel}>월회원</Text>
                <Text style={styles.weatherValue}>{usage.memberLabel}</Text>
              </View>
              <View style={styles.weatherDivider} />
              <View style={styles.weatherItem}>
                <Text style={styles.weatherLabel}>혼잡도</Text>
                <Text style={styles.weatherValue}>{usage.busyLabel}</Text>
              </View>
            </View>
            <Text style={styles.weatherMeta}>{usage.yoyLabel}</Text>
            <TouchableOpacity style={styles.reserveButton} onPress={() => Linking.openURL(RESERVE_URL)}>
              <Text style={styles.reserveButtonText}>올림픽테니스장 공식 예약하기</Text>
            </TouchableOpacity>
          </View>
        ) : null}

        {/* 푸터 */}
        <View style={styles.footer}>
          <Text style={styles.footerText}>한국체육산업개발(주) 공공데이터 경진대회 출품작</Text>
          <Text style={styles.footerSubText}>TennisLab Mobile Client v1.0.0</Text>
        </View>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#F3F4F6'
  },
  header: {
    backgroundColor: '#1E3A8A',
    paddingHorizontal: 20,
    paddingVertical: 16,
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center'
  },
  headerTitle: {
    color: '#FFFFFF',
    fontSize: 20,
    fontWeight: 'bold'
  },
  headerSubtitle: {
    color: '#93C5FD',
    fontSize: 12,
    marginTop: 2
  },
  liveBadge: {
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 8
  },
  liveBadgeOn: {
    backgroundColor: '#DC2626'
  },
  liveBadgeOff: {
    backgroundColor: '#6B7280'
  },
  liveBadgeText: {
    color: '#FFFFFF',
    fontSize: 10,
    fontWeight: 'bold'
  },
  scrollContent: {
    padding: 16
  },
  weatherCard: {
    backgroundColor: '#FFFFFF',
    borderRadius: 14,
    padding: 16,
    marginBottom: 16,
    shadowColor: '#000',
    shadowOpacity: 0.05,
    shadowRadius: 6,
    elevation: 2
  },
  cardHeaderTitle: {
    fontSize: 13,
    fontWeight: '600',
    color: '#6B7280',
    marginBottom: 12
  },
  weatherRow: {
    flexDirection: 'row',
    justifyContent: 'space-around',
    alignItems: 'center'
  },
  weatherItem: {
    alignItems: 'center'
  },
  weatherLabel: {
    fontSize: 12,
    color: '#9CA3AF',
    marginBottom: 4
  },
  weatherValue: {
    fontSize: 16,
    fontWeight: 'bold',
    color: '#1F2937'
  },
  weatherDivider: {
    width: 1,
    height: 30,
    backgroundColor: '#E5E7EB'
  },
  weatherMeta: {
    marginTop: 10,
    fontSize: 11,
    color: '#9CA3AF',
    textAlign: 'center'
  },
  sectionTitle: {
    fontSize: 15,
    fontWeight: 'bold',
    color: '#1F2937',
    marginBottom: 10
  },
  courtScroll: {
    marginBottom: 16
  },
  courtChip: {
    backgroundColor: '#FFFFFF',
    borderRadius: 12,
    paddingVertical: 10,
    paddingHorizontal: 16,
    marginRight: 10,
    alignItems: 'center',
    borderWidth: 1.5,
    borderColor: '#E5E7EB'
  },
  courtChipIndoor: {
    borderColor: '#A7F3D0',
    backgroundColor: '#ECFDF5'
  },
  courtChipSelected: {
    backgroundColor: '#2563EB',
    borderColor: '#1D4ED8'
  },
  courtChipText: {
    fontSize: 14,
    fontWeight: 'bold',
    color: '#374151'
  },
  courtChipSub: {
    fontSize: 11,
    color: '#9CA3AF',
    marginTop: 2
  },
  courtChipTextSelected: {
    color: '#FFFFFF'
  },
  playerSideRow: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 16
  },
  playerSideLabel: {
    fontSize: 13,
    color: '#4B5563',
    marginRight: 10
  },
  sideButton: {
    flex: 1,
    backgroundColor: '#E5E7EB',
    paddingVertical: 8,
    borderRadius: 8,
    alignItems: 'center',
    marginHorizontal: 4
  },
  sideButtonActive: {
    backgroundColor: '#1E40AF'
  },
  sideButtonText: {
    fontSize: 12,
    color: '#4B5563',
    fontWeight: '600'
  },
  sideButtonTextActive: {
    color: '#FFFFFF'
  },
  physicsCard: {
    backgroundColor: '#FFFFFF',
    borderRadius: 14,
    padding: 16,
    marginBottom: 16,
    shadowColor: '#000',
    shadowOpacity: 0.05,
    shadowRadius: 6,
    elevation: 2
  },
  physicsHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center'
  },
  physicsTitle: {
    fontSize: 16,
    fontWeight: 'bold',
    color: '#111827'
  },
  physicsDesc: {
    fontSize: 12,
    color: '#6B7280',
    marginTop: 4,
    marginBottom: 14
  },
  badge: {
    paddingHorizontal: 8,
    paddingVertical: 3,
    borderRadius: 6
  },
  badgeIndoor: {
    backgroundColor: '#D1FAE5'
  },
  badgeOutdoor: {
    backgroundColor: '#FEF3C7'
  },
  badgeText: {
    fontSize: 11,
    fontWeight: 'bold',
    color: '#065F46'
  },
  metricGrid: {
    flexDirection: 'row',
    justifyContent: 'space-between'
  },
  metricBox: {
    flex: 1,
    backgroundColor: '#F9FAFB',
    borderRadius: 10,
    padding: 12,
    marginHorizontal: 3,
    alignItems: 'center',
    borderWidth: 1,
    borderColor: '#F3F4F6'
  },
  metricLabel: {
    fontSize: 11,
    color: '#6B7280',
    marginBottom: 6
  },
  metricValue: {
    fontSize: 17,
    fontWeight: 'bold',
    marginBottom: 4
  },
  metricSub: {
    fontSize: 10,
    color: '#9CA3AF'
  },
  tacticsCard: {
    backgroundColor: '#EFF6FF',
    borderRadius: 14,
    padding: 16,
    borderLeftWidth: 4,
    borderLeftColor: '#3B82F6',
    marginBottom: 16
  },
  usageCard: {
    backgroundColor: '#FFFFFF',
    borderRadius: 14,
    padding: 16,
    marginBottom: 16,
    shadowColor: '#000',
    shadowOpacity: 0.05,
    shadowRadius: 6,
    elevation: 2
  },
  usagePeriod: {
    fontSize: 13,
    fontWeight: '600',
    color: '#1F2937',
    marginBottom: 12
  },
  reserveButton: {
    marginTop: 14,
    backgroundColor: '#1E3A8A',
    borderRadius: 10,
    paddingVertical: 12,
    alignItems: 'center'
  },
  reserveButtonText: {
    color: '#FFFFFF',
    fontSize: 14,
    fontWeight: 'bold'
  },
  tacticsHeader: {
    fontSize: 15,
    fontWeight: 'bold',
    color: '#1E40AF',
    marginBottom: 10
  },
  tacticItem: {
    marginBottom: 6
  },
  tacticText: {
    fontSize: 13,
    color: '#1E3A8A',
    lineHeight: 18
  },
  footer: {
    alignItems: 'center',
    paddingVertical: 16
  },
  footerText: {
    fontSize: 12,
    color: '#9CA3AF'
  },
  footerSubText: {
    fontSize: 11,
    color: '#D1D5DB',
    marginTop: 2
  }
});
