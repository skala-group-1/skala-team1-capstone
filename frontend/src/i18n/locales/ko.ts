// 스태프(상담사·병원관리자·운영자) 화면용
import type en from './en'
const ko: typeof en = {
  app: { title: 'K-Beauty Consult' },
  common: { needsCheck: '확인 필요', retry: '다시 시도', cancel: '취소', confirm: '확인', loading: '불러오는 중…' },
  onboarding: { notice: '병원을 추천하지 않고 사실을 비교합니다.', start: '시작하기' },
  auth: { email: '이메일', password: '비밀번호', login: '로그인', signup: '회원가입', logout: '로그아웃', loginFailed: '이메일 또는 비밀번호가 올바르지 않습니다' },
  nav: { home: '홈', explore: '탐색', ai: 'AI', reservations: '예약', me: '내 정보' },
  error: { forbidden: '이 화면을 볼 권한이 없습니다.', notFound: '페이지를 찾을 수 없습니다' },
}
export default ko
