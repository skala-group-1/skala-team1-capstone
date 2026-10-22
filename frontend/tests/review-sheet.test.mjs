// Run with: node --test tests/review-sheet.test.mjs
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'
import vm from 'node:vm'
import { compileScript, parse } from '@vue/compiler-sfc'
import ts from 'typescript'
import * as vue from 'vue'

const source = readFileSync(new URL('../src/components/booking/ReviewSheet.vue', import.meta.url), 'utf8')
const script = compileScript(parse(source).descriptor, { id: 'review-sheet-test' }).content
const compiled = ts.transpileModule(script, { compilerOptions: { module: ts.ModuleKind.CommonJS } }).outputText

function setup(writeReview) {
  const calls = { written: [], emitted: [] }
  const props = vue.reactive({ open: false, reservation: { id: 7, hospital: { name: 'H' }, procedure: { name: 'P' } } })
  const mocks = {
    vue,
    'vue-i18n': { useI18n: () => ({ t: (key) => key }) },
    '@/api': {
      reservationApi: {
        writeReview: async (id, body) => {
          calls.written.push({ id, body })
          return writeReview(id, body)
        },
      },
      toApiError: (e) => e?.api ?? null,
    },
  }
  const module = { exports: {} }
  vm.runInNewContext(compiled, { exports: module.exports, require: (name) => mocks[name] ?? {} })
  const scope = vue.effectScope()
  const sheet = scope.run(() =>
    module.exports.default.setup(props, { expose() {}, emit: (name, ...args) => calls.emitted.push([name, ...args]) }),
  )
  return { props, calls, sheet, stop: () => scope.stop() }
}

test('submit needs a rating and at least 10 characters, and sends trimmed content', async () => {
  const h = setup(async (id, body) => ({ id: 99, rating: body.rating, content: body.content }))
  try {
    h.props.open = true
    await vue.nextTick()
    assert.equal(h.sheet.valid.value, false)
    h.sheet.content.value = '   short   '
    h.sheet.rating.value = 5
    assert.equal(h.sheet.valid.value, false)
    await h.sheet.submit()
    assert.equal(h.calls.written.length, 0)

    h.sheet.content.value = '  Friendly staff and a great interpreter.  '
    assert.equal(h.sheet.valid.value, true)
    await h.sheet.submit()
    // vm 컨텍스트에서 만든 객체라 프로토타입이 달라 JSON 으로 비교
    assert.equal(JSON.stringify(h.calls.written), JSON.stringify([{ id: 7, body: { rating: 5, content: 'Friendly staff and a great interpreter.' } }]))
    assert.equal(h.calls.emitted[0][0], 'done')
    assert.equal(h.calls.emitted[0][1].id, 99)
  } finally { h.stop() }
})

test('already reviewed shows a dedicated message and reopening resets the form', async () => {
  const h = setup(async () => {
    throw { api: { code: 'REVIEW_ALREADY_EXISTS', message: 'server text' } }
  })
  try {
    h.props.open = true
    await vue.nextTick()
    h.sheet.rating.value = 3
    h.sheet.content.value = 'This is a long enough review.'
    await h.sheet.submit()
    assert.equal(h.sheet.errorMsg.value, 'reservations.review.already')
    assert.equal(h.sheet.submitting.value, false)
    assert.equal(h.calls.emitted.length, 0)

    h.props.open = false
    await vue.nextTick()
    h.props.open = true
    await vue.nextTick()
    assert.equal(h.sheet.rating.value, 0)
    assert.equal(h.sheet.content.value, '')
    assert.equal(h.sheet.errorMsg.value, null)
  } finally { h.stop() }
})
