import { test } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';
import ts from 'typescript';

function render(mode, prepared = false) {
  const state = { id: 'state', type: 'avatar', order: 4, title: 'Practice', estimatedMin: 2 };
  const session = { id: 'session', completedStateIds: [], usage: {}, status: 'in_progress' };
  let hook = 0;
  const overrides = new Map([[0, session], [1, [state]], [11, mode], [16, prepared ? { key: "session:state:0", id: "prepared-1" } : null]]);
  const sandbox = { exports: {}, require(name) {
    if (name === 'react/jsx-runtime') return { jsx: (type, props) => ({ type, props }), jsxs: (type, props) => ({ type, props }) };
    if (name === 'react') return {
      useState(initial) { const index = hook++; return [overrides.has(index) ? overrides.get(index) : initial, () => {}]; },
      useRef: value => ({ current: value }), useMemo: fn => fn(), useCallback: fn => fn, useEffect() {},
    };
    if (name.endsWith('/state-machine/engine')) return { getCurrentState: () => state, getSessionProgress: () => ({ percent: 0 }), canMoveNext: () => false, canMovePrevious: () => false };
    if (name.endsWith('/state-machine/utils')) return { sortStatesByOrder: states => states, isAvatarState: () => true, isInteractiveState: () => true };
    return new Proxy({}, { get: (_, key) => key });
  }};
  const source = fs.readFileSync(new URL('../src/components/training/session-runner.tsx', import.meta.url), 'utf8');
  vm.runInNewContext(ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.CommonJS, jsx: ts.JsxEmit.ReactJSX } }).outputText, sandbox);
  const tree = sandbox.exports.SessionRunner({ sessionId: 'session' });
  const nodes = [];
  function visit(node) { if (Array.isArray(node)) return node.forEach(visit); if (!node || typeof node !== 'object') return; nodes.push(node); visit(node.props?.children); }
  visit(tree); return nodes;
}

test('unselected session shows briefing and Start before any avatar or answers', () => {
  const nodes = render(null);
  assert.ok(nodes.some(node => node.type === 'fieldset'));
  assert.ok(nodes.some(node => node.props?.children === 'Egitime Basla'));
  assert.ok(!nodes.some(node => node.type === 'LiveAvatarView' || node.type === 'textarea'));
});

test('locked text mode never mounts the avatar and waits for its opening question', () => {
  const nodes = render('text');
  assert.ok(!nodes.some(node => node.type === 'LiveAvatarView' || node.type === 'fieldset'));
  assert.equal(nodes.find(node => node.type === 'textarea').props.disabled, true);
});

test('voice mode mounts avatar only after speech is prepared', () => {
  assert.ok(!render('voice').some(node => node.type === 'LiveAvatarView'));
  const nodes = render('voice', true);
  assert.ok(nodes.some(node => node.type === 'LiveAvatarView'));
  assert.ok(!nodes.some(node => node.type === 'fieldset'));
});
