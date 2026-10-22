/**
 * localStorage 래퍼. 저장소가 막힌 환경(일부 인앱 웹뷰·사이트 데이터 차단)에서는 getItem 도 예외를 던져
 * import 시점에 읽는 i18n 이 앱 mount 자체를 막는다 → 실패하면 null·무시하고 계속 진행
 */
export const storage = {
  get(key: string): string | null {
    try {
      return localStorage.getItem(key)
    } catch {
      return null
    }
  },
  set(key: string, value: string) {
    try {
      localStorage.setItem(key, value)
    } catch {
      // 저장 못 해도 화면은 동작 (다음 방문 때 기본값)
    }
  },
  remove(key: string) {
    try {
      localStorage.removeItem(key)
    } catch {
      // 위와 같음
    }
  },
}
