import { test } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';
import ts from 'typescript';

function deferred() { let resolve; const promise = new Promise(r => { resolve = r; }); return { promise, resolve }; }
function manager({ tokenGate, connectGate, startGate } = {}) {
  const calls = [], timers = [];
  class Room {
    remoteParticipants = new Map();
    on() {} removeAllListeners() {}
    async connect() { calls.push('connect'); await connectGate?.promise; }
    async disconnect() { calls.push('disconnect'); }
  }
  const sandbox = { exports: {}, setTimeout(fn) { timers.push(fn); return fn; }, clearTimeout(fn) { timers.splice(timers.indexOf(fn), 1); }, require(name) {
    if (name === 'livekit-client') return { Room, RoomEvent: {} };
    if (name.includes('sessionAdapter')) return {
      async getAvatarSessionToken() { await tokenGate?.promise; return { metadata: { livekitUrl: 'wss://example.test', livekitClientToken: 'ephemeral', avatarSessionId: 'avatar-1' } }; },
      async sendAvatarSessionAction(id, body) { calls.push(body.action); if (body.action === 'start') await startGate?.promise; },
    };
    throw new Error(name);
  }};
  const source = fs.readFileSync(new URL('../src/lib/avatar-session-manager.ts', import.meta.url), 'utf8');
  vm.runInNewContext(ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2020 } }).outputText, sandbox);
  return { ...sandbox.exports, calls, expire: () => timers.splice(0).forEach(fn => fn()) };
}

for (const stage of ['token', 'connect', 'start']) {
  test(`release while ${stage} is pending prevents an orphan avatar`, async () => {
    const gate = deferred(); const api = manager({ [`${stage}Gate`]: gate });
    const pending = api.acquireAvatarSession('session', 'state', () => {}, () => {});
    const rejection = assert.rejects(pending, /cancelled/);
    await new Promise(resolve => setImmediate(resolve));
    api.releaseAvatarSession('session', 'state'); api.expire();
    gate.resolve(); await rejection;
    assert.ok(api.calls.includes('stop'));
    assert.ok(api.calls.includes('disconnect'));
    if (stage !== 'start') assert.ok(!api.calls.includes('start'));
  });
}

test('StrictMode release/reacquire shares one pending connection', async () => {
  const gate = deferred(); const api = manager({ tokenGate: gate });
  const first = api.acquireAvatarSession('session', 'state', () => {}, () => {});
  api.releaseAvatarSession('session', 'state');
  const second = api.acquireAvatarSession('session', 'state', () => {}, () => {});
  gate.resolve();
  assert.equal(await first, await second);
  assert.deepEqual(api.calls, ['connect', 'start']);
});
