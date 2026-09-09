import { test } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import vm from 'node:vm';
import ts from 'typescript';
import { fileURLToPath } from 'node:url';
const __dirname = path.dirname(fileURLToPath(import.meta.url));

function adapter(response) {
  const calls = [];
  class ApiError extends Error {
    constructor(message, status, payload) { super(message); this.status = status; this.payload = payload; }
  }
  const sandbox = {
    exports: {},
    require(name) {
      if (name.endsWith('/api/client')) return {
        apiPost: async (...args) => { calls.push(args); return response; },
        apiGet: async (...args) => { calls.push(args); return response; },
      };
      if (name.endsWith('/api/errors')) return { ApiError };
      if (name.endsWith('/state-machine/engine')) return {};
      throw new Error(`Unexpected import: ${name}`);
    },
  };
  const source = fs.readFileSync(path.join(__dirname, '../src/lib/adapters/sessionAdapter.ts'), 'utf8');
  vm.runInNewContext(ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.CommonJS } }).outputText, sandbox);
  return { ...sandbox.exports, calls };
}

test('processing evaluation rejects so callers retain drafts', async () => {
  const api = adapter({ status: 'processing', session: { status: 'in_progress' } });
  await assert.rejects(api.finalizeSession('session-1', {}), error => error.payload.detail.code === 'evaluation_processing');
});

test('completed evaluation preserves existing session return contract', async () => {
  const session = { id: 'session-1', status: 'completed' };
  const api = adapter({ status: 'completed', session });
  assert.equal(await api.finalizeSession('session-1', { answers: [] }), session);
});

test('inconsistent completion cannot clear answers', async () => {
  const api = adapter({ status: 'completed', session: { status: 'in_progress' } });
  await assert.rejects(api.finalizeSession('session-1', {}));
});

test('text fallback requests no speech synthesis with learner state context', async () => {
  const api = adapter({ assistantText: 'Next question' });
  const payload = { stateId: 'state-2', learnerText: 'My answer', textOnly: true };
  await api.submitConversationTurn('session-1', payload);
  assert.equal(api.calls[0][0], '/api/learner/sessions/session-1/conversation-turn');
  assert.equal(api.calls[0][1], payload);
});

test('delivery status uses the authenticated session endpoint and encodes IDs', async () => {
  const api = adapter({ status: 'fallback', contentType: 'audio/wav' });
  const result = await api.getVoiceDelivery('session/1', 'delivery/1');
  assert.equal(result.status, 'fallback');
  assert.equal(api.calls[0][0], '/api/learner/sessions/session%2F1/voice/delivery/delivery%2F1');
});

test('invalid browser timings never reach the API', async () => {
  const api = adapter({});
  for (const invalid of [NaN, Infinity, -1, 600001]) await api.recordBrowserVoiceMetric('session', 'state', 'browser_playback', invalid);
  assert.equal(api.calls.length, 0);
  await api.recordBrowserVoiceMetric('session', 'state', 'browser_first_frame', 123.4);
  assert.equal(api.calls[0][1].metrics.latency_ms, 123);
  assert.deepEqual(Object.keys(api.calls[0][1]).sort(), ['event', 'metrics', 'stateId']);
});

test('missing evidence recovery and cancellation preserve session authorization endpoints', async () => {
  const api = adapter({ id: 'session/1' });
  await api.recoverConversationState('session/1', 'state-1');
  await api.cancelVoiceDelivery('session/1', 'state-1');
  assert.equal(api.calls[0][0], '/api/learner/sessions/session%2F1/conversation/recover');
  assert.equal(api.calls[1][0], '/api/learner/sessions/session%2F1/voice/cancel');
  assert.equal(api.calls[0][1].stateId, 'state-1');
});

test('text opening explicitly disables speech without changing the response contract', async () => {
  const api = adapter({ assistantText: 'Opening question', conversationComplete: false });
  const result = await api.startVoiceOpening('session-1', 'state-2', true);
  assert.equal(result.assistantText, 'Opening question');
  assert.equal(api.calls[0][0], '/api/learner/sessions/session-1/voice/opening');
  assert.equal(api.calls[0][1].textOnly, true);
  assert.equal(api.calls[0][1].stateId, 'state-2');
});

test('voice opening retains speech as its default', async () => {
  const api = adapter({ assistantText: 'Hello' });
  await api.startVoiceOpening('session-1', 'state-2');
  assert.equal(api.calls[0][1].textOnly, false);
});

test('voice preparation sends only state and consumption forwards prepared id', async () => {
  const api = adapter({ preparedOpeningId: 'prepared-1', assistantText: 'Question' });
  await api.prepareVoiceOpening('session-1', 'state-2');
  assert.deepEqual(Object.keys(api.calls[0][1]), ['stateId']);
  assert.equal(api.calls[0][0], '/api/learner/sessions/session-1/voice/opening/prepare');
  await api.startVoiceOpening('session-1', 'state-2', false, 'prepared-1');
  assert.equal(api.calls[1][1].preparedOpeningId, 'prepared-1');
});
