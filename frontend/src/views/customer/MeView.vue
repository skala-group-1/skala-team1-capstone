<script setup lang="ts">
// 「화면 목록」 C11 내 정보 (04 ④ 2:11496): 프로필 · 언어(PATCH /api/me) · 이전 AI 상담(GET /api/ai/conversations) · 로그아웃
// 고객 en/zh/ja, 스태프 ko/en (13-2)
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { useAuthStore } from '@/stores/auth'
import { aiApi, authApi } from '@/api'
import { setLocale } from '@/i18n'
import { showToast } from '@/composables/useToast'
import { fmtDate, fmtTime } from '@/utils/format'
import TopAppBar from '@/components/ui/TopAppBar.vue'
import AppIcon from '@/components/ui/AppIcon.vue'
import AppButton from '@/components/ui/AppButton.vue'
import AppDialog from '@/components/ui/AppDialog.vue'
import type { Conversation, Locale } from '@/types/contract'

const router = useRouter()
const { t, locale } = useI18n()
const auth = useAuthStore()
const conversations = ref<Conversation[]>([])
/** GET /api/me 는 email 까지 준다 (13-2) */
const email = ref<string | null>(null)

const options = computed<{ value: Locale; label: string }[]>(() =>
  auth.role === 'CUSTOMER'
    ? [
        { value: 'en', label: 'English' },
        { value: 'zh', label: '中文 (简体)' },
        { value: 'ja', label: '日本語' },
        { value: 'ko', label: '한국어' },
      ]
    : [
        { value: 'ko', label: '한국어' },
        { value: 'en', label: 'English' },
      ],
)
async function pick(l: Locale) {
  if (l === locale.value) return
  setLocale(l)
  try {
    await auth.setLocale(l)
  } catch {
    showToast(t('common.error'), 'error')
  }
}
const logoutOpen = ref(false)
async function logout() {
  logoutOpen.value = false
  await auth.logout()
  await router.replace('/login')
}
onMounted(async () => {
  email.value = ((await authApi.me().catch(() => null)) as { email?: string } | null)?.email ?? null
  if (auth.role === 'CUSTOMER') conversations.value = await aiApi.conversations().catch(() => [])
})
</script>

<template>
  <div class="page">
    <TopAppBar :title="t('me.title')" />
    <div class="body">
      <section class="card profile">
        <span class="avatar t-body-16-sb">{{ auth.user?.name?.slice(0, 1) }}</span>
        <div>
          <p class="t-title-18">{{ auth.user?.name }}</p>
          <p class="t-caption-13 muted">{{ email ?? (auth.role ? t(`staff.role.${auth.role}`) : '') }}</p>
        </div>
      </section>

      <section>
        <h2 class="t-body-16-sb">{{ t('me.language') }}</h2>
        <p class="t-caption-12 muted">{{ t('me.languageNote') }}</p>
        <ul class="card list" role="radiogroup" :aria-label="t('me.language')">
          <li v-for="o in options" :key="o.value">
            <button type="button" role="radio" class="row t-body-15" :aria-checked="locale === o.value" @click="pick(o.value)">
              {{ o.label }}
              <AppIcon v-if="locale === o.value" name="check" :size="20" class="brand" />
            </button>
          </li>
        </ul>
      </section>

      <section v-if="auth.role === 'CUSTOMER'">
        <h2 class="t-body-16-sb">{{ t('me.history') }}</h2>
        <p class="t-caption-12 muted">{{ t('me.historyNote') }}</p>
        <ul v-if="conversations.length" class="card list">
          <li v-for="c in conversations" :key="c.id">
            <RouterLink :to="`/chat/${c.id}`" class="row">
              <span class="conv">
                <span class="t-body-15">{{ c.hospital?.name ?? t('me.mainChat') }}</span>
                <span class="t-caption-12 muted">
                  {{ c.hospital ? t('me.hospitalChat') : t('chat.mode.ai') }} · {{ fmtDate(c.createdAt) }} {{ fmtTime(c.createdAt) }}
                </span>
              </span>
              <AppIcon name="chevron-right" :size="18" class="muted" />
            </RouterLink>
          </li>
        </ul>
        <p v-else class="t-body-14 muted empty">{{ t('me.noHistory') }}</p>
      </section>

      <AppButton variant="danger" size="l" block @click="logoutOpen = true">{{ t('auth.logout') }}</AppButton>
    </div>
    <AppDialog :open="logoutOpen" @close="logoutOpen = false" :title="t('me.logoutConfirm')">
      <template #actions>
        <AppButton variant="secondary" @click="logoutOpen = false">{{ t('common.cancel') }}</AppButton>
        <AppButton variant="danger" @click="logout">{{ t('auth.logout') }}</AppButton>
      </template>
    </AppDialog>
  </div>
</template>

<style scoped>
.page { display: flex; flex-direction: column; min-height: 100%; background: var(--bg-subtle); }
.body { display: flex; flex-direction: column; gap: var(--space-20); padding: var(--space-16); }
.card { border: 1px solid var(--border-default); border-radius: var(--radius-lg); background: var(--surface-card); }
.profile { display: flex; align-items: center; gap: var(--space-12); padding: var(--space-16); }
.avatar { display: grid; place-items: center; width: 48px; height: 48px; border-radius: 50%; background: var(--brand-subtle); color: var(--brand-text); }
.muted { color: var(--text-tertiary); }
.brand { color: var(--brand-primary); }
.list { margin: var(--space-12) 0 0; padding: 0; list-style: none; overflow: hidden; }
.list li + li { border-top: 1px solid var(--border-default); }
.row { display: flex; align-items: center; justify-content: space-between; width: 100%; padding: var(--space-16); border: 0; background: none; text-align: left; color: var(--text-primary); }
.conv { display: flex; flex-direction: column; gap: var(--space-2); }
.empty { margin-top: var(--space-12); }
</style>
