// Run with: node --test tests/closed-consultation.test.mjs
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'
import vm from 'node:vm'
import { compileScript, parse } from '@vue/compiler-sfc'
import ts from 'typescript'
import * as vue from 'vue'

const source = readFileSync(new URL('../src/views/customer/ChatView.vue', import.meta.url), 'utf8')
const script = compileScript(parse(source).descriptor, { id: 'chat-history-test' }).content
const compiled = ts.transpileModule(script, { compilerOptions: { module: ts.ModuleKind.CommonJS } }).outputText

function setup(mode = 'HUMAN', status = 'ACTIVE') {
  const calls = { opened: [], closed: 0, ai: [], human: [], ended: 0, toasts: [] }
  const conv = vue.reactive({
    conversationId: 'conversation-1', consultationId: 4, mode,
    messages: [], cards: [], streaming: false, draft: '',
    refresh: async () => {},
    send: async (text) => calls.ai.push(text),
  })
  const consult = vue.reactive({
    current: null, messages: [],
    async open(id) {
      calls.opened.push(id)
      this.current = { id, status, summaryCard: { procedure: 'Eyelid surgery', questions: [] } }
      this.messages = [{ id: 11, originalText: 'What should I bring?' }]
    },
    close() { calls.closed++; this.current = null; this.messages = [] },
    send: async (text) => calls.human.push(text),
    async endByCustomer() { calls.ended++; this.current = { ...this.current, status: 'CLOSED' } },
  })
  const lifecycle = {}
  const mocks = {
    vue: { ...vue, onMounted: (fn) => { lifecycle.mount = fn }, onBeforeUnmount: (fn) => { lifecycle.unmount = fn } },
    'vue-router': { useRoute: () => ({ params: { conversationId: 'conversation-1' }, query: {} }), useRouter: () => ({}) },
    'vue-i18n': { useI18n: () => ({ t: (key) => key }) },
    '@/stores/conversation': { useConversationStore: () => conv },
    '@/stores/consultation': { useConsultationStore: () => consult },
    '@/stores/search': { useSearchStore: () => ({ procedures: [] }) },
    '@/stores/reservation': { useReservationStore: () => ({}) },
    '@/stores/auth': { useAuthStore: () => ({ user: { locale: 'en' } }) },
    '@/composables/useNow': { useNow: () => vue.ref(0) },
    '@/composables/useToast': { showToast: (text) => calls.toasts.push(text) },
  }
  const module = { exports: {} }
  vm.runInNewContext(compiled, { exports: module.exports, require: (name) => mocks[name] ?? {} })
  const scope = vue.effectScope()
  const view = scope.run(() => module.exports.default.setup({}, { expose() {} }))
  return { conv, consult, calls, view, lifecycle, stop: () => scope.stop() }
}

test('closing a consultation preserves summary/messages and sends the next message to AI', async () => {
  const h = setup()
  try {
    await vue.nextTick()
    h.view.input.value = 'Hello counselor'
    await h.view.submit()
    assert.deepEqual(h.calls.human, ['Hello counselor'])
    h.consult.current.status = 'CLOSED'
    await vue.nextTick()
    assert.equal(h.conv.mode, 'HOSPITAL')
    assert.equal(h.consult.current.summaryCard.procedure, 'Eyelid surgery')
    assert.equal(h.consult.messages[0].originalText, 'What should I bring?')
    assert.equal(h.calls.closed, 0)
    h.view.input.value = 'What is the price?'
    await h.view.submit()
    assert.deepEqual(h.calls.ai, ['What is the price?'])
  } finally { h.stop() }
})

test('closed history loads in HOSPITAL mode and reopens after navigation back', async () => {
  const h = setup('HOSPITAL', 'CLOSED')
  try {
    await vue.nextTick()
    assert.deepEqual(h.calls.opened, [4])
    assert.equal(h.consult.messages.length, 1)
    h.lifecycle.unmount()
    assert.equal(h.consult.current, null)
    await h.view.enter()
    assert.equal(h.calls.opened.at(-1), 4)
    assert.equal(h.consult.messages.length, 1)
    assert.equal(h.conv.mode, 'HOSPITAL')
    h.conv.consultationId = null
    h.conv.mode = 'MAIN'
    await vue.nextTick()
    assert.equal(h.consult.current, null)
    assert.equal(h.consult.messages.length, 0)
  } finally { h.stop() }
})

test('a stale closed consultation cannot change another conversation mode', async () => {
  const h = setup()
  try {
    await vue.nextTick()
    h.consult.current = { id: 99, status: 'CLOSED' }
    await vue.nextTick()
    assert.equal(h.conv.mode, 'HUMAN')
  } finally { h.stop() }
})

test('customer ends an active consultation and the chat returns to AI', async () => {
  const h = setup()
  try {
    await vue.nextTick()
    assert.equal(h.view.canEndConsult.value, true)
    h.view.endConsultOpen.value = true
    await h.view.endConsult()
    await vue.nextTick()
    assert.equal(h.calls.ended, 1)
    assert.equal(h.view.endConsultOpen.value, false)
    assert.deepEqual(h.calls.toasts, ['chat.human.ended'])
    assert.equal(h.conv.mode, 'HOSPITAL')
    assert.equal(h.view.canEndConsult.value, false)
    h.view.input.value = 'Back to AI'
    await h.view.submit()
    assert.deepEqual(h.calls.ai, ['Back to AI'])
  } finally { h.stop() }
})

test('a waiting consultation can be cancelled, a closed one shows no end button', async () => {
  const waiting = setup('HUMAN', 'WAITING')
  try {
    await vue.nextTick()
    assert.equal(waiting.view.canEndConsult.value, true)
    await waiting.view.endConsult()
    assert.deepEqual(waiting.calls.toasts, ['chat.human.cancelled'])
  } finally { waiting.stop() }
  const closed = setup('HOSPITAL', 'CLOSED')
  try {
    await vue.nextTick()
    assert.equal(closed.view.canEndConsult.value, false)
  } finally { closed.stop() }
})
