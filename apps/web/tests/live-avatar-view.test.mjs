import { test } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';
import ts from 'typescript';

function view() {
  const effects = [], errors = [], timers = new Map();
  const sandbox = { exports: {}, queueMicrotask() {}, window: {
    setTimeout(fn, ms) { timers.set(fn, ms); return fn; }, clearTimeout(fn) { timers.delete(fn); },
  }, require(name) {
    if (name === 'react/jsx-runtime') return { jsx: () => ({}), jsxs: () => ({}) };
    if (name === 'react') return { useState: initial => [initial, () => {}], useRef: initial => ({ current: initial }), useCallback: fn => fn, useEffect: fn => effects.push(fn) };
    if (name.includes('avatar-session-manager')) return { releaseAvatarSession() {} };
    return {};
  }};
  const source = fs.readFileSync(new URL('../src/components/training/live-avatar-view.tsx', import.meta.url), 'utf8');
  vm.runInNewContext(ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.CommonJS, jsx: ts.JsxEmit.ReactJSX } }).outputText, sandbox);
  sandbox.exports.LiveAvatarView({ sessionId: 'session', stateId: 'state', onAvatarError: error => errors.push(error) });
  const cleanups = effects.map(fn => fn()).filter(fn => typeof fn === 'function');
  return { timers, errors, cleanup: () => cleanups.forEach(fn => fn()) };
}

test('avatar without a first frame stops waiting after 30 seconds', () => {
  const current = view();
  assert.equal(current.timers.size, 1);
  for (const [timeout, ms] of current.timers) { assert.equal(ms, 30000); timeout(); }
  assert.equal(current.errors.length, 1);
});

test('unmount cancels first frame watchdog', () => {
  const current = view(); current.cleanup();
  assert.equal(current.timers.size, 0);
  assert.equal(current.errors.length, 0);
});
