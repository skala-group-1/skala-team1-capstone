import type en from './en'
const ja: typeof en = {
  app: { title: 'K-Beauty Consult' },
  common: { needsCheck: '要確認', retry: '再試行', cancel: 'キャンセル', confirm: '確認', loading: '読み込み中…' },
  onboarding: { notice: '病院のおすすめではなく、事実を比較します。', start: 'はじめる' },
  auth: { email: 'メール', password: 'パスワード', login: 'ログイン', signup: '新規登録', logout: 'ログアウト', loginFailed: 'メールまたはパスワードが違います' },
  nav: { home: 'ホーム', explore: '探す', ai: 'AI', reservations: '予約', me: 'マイページ' },
  error: { forbidden: 'このページを表示する権限がありません。', notFound: 'ページが見つかりません' },
}
export default ja
