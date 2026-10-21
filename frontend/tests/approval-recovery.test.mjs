import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'
import vm from 'node:vm'
import ts from 'typescript'
import { createPinia, setActivePinia, defineStore } from 'pinia'

const source = readFileSync(new URL('../src/stores/conversation.ts', import.meta.url), 'utf8')
const compiled = ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.CommonJS } }).outputText
function setup() {
  setActivePinia(createPinia())
  const pending = { action: 'REQUEST_CONSULTATION', display: { rows: [], notice: '', title: '' }, args: {}, editable: [] }
  const active = { id: 'task', conversationId: 'chat', status: 'WAITING_APPROVAL', pendingAction: pending }
  const calls = { create: 0, streams: [], approved: [] }
  const api = {
    conversation: async (id) => ({ id, mode: 'HOSPITAL', messages: [], conditions: null }),
    myTasks: async () => [active], task: async () => active,
    createTask: async () => { calls.create++; throw { response: { data: { details: { activeTaskId: 'task' } } } } },
    approve: async (...args) => { calls.approved.push(args) },
  }
  const module = { exports: {} }
  const mocks = { pinia: { defineStore }, '@/api': {
    aiApi: api, streamTask: (id, handlers, seq) => {
      calls.streams.push({ id, handlers, seq }); return () => {}
    },
  } }
  vm.runInNewContext(compiled, { exports: module.exports, require: (name) => mocks[name] })
  return { store: module.exports.useConversationStore(), api, calls, pending }
}

test('reload restores approval form without creating or approving a task', async () => {
  const { store, calls } = setup()
  await store.load('chat')
  assert.equal(store.pendingAction.action, 'REQUEST_CONSULTATION')
  assert.equal(store.taskId, 'task')
  assert.equal(calls.create, 0)
  assert.equal(calls.approved.length, 0)
  await store.send('retry')
  assert.equal(calls.create, 0)
})

test('BUSY recovers the active task and clears the generic failure', async () => {
  const { store, calls } = setup()
  store.conversationId = 'chat'
  await store.send('connect')
  assert.equal(calls.create, 1)
  assert.equal(store.pendingAction.action, 'REQUEST_CONSULTATION')
  assert.equal(store.error, null)
})

test('late response cannot restore a different conversation', async () => {
  const { store, api, calls } = setup()
  let resolve
  api.myTasks = () => new Promise((r) => { resolve = r })
  store.conversationId = 'chat'
  const recovery = store.restoreActiveTask()
  store.conversationId = 'other'
  resolve([{ id: 'task', conversationId: 'chat', status: 'RUNNING' }])
  assert.equal(await recovery, false)
  assert.equal(calls.streams.length, 0)
})

test('old stream callbacks cannot overwrite a resumed approval stream', async () => {
  const { store, calls } = setup()
  await store.load('chat')
  const old = calls.streams[0].handlers
  store.lastSeq = 3
  await store.approve(true)
  old.onClose(); old.onError()
  assert.equal(store.streaming, true)
  assert.equal(store.error, null)
  assert.equal(calls.streams[1].seq, 3)
  assert.equal(calls.approved.length, 1)
})
