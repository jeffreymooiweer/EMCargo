const test = require('node:test');
const assert = require('node:assert/strict');
const finalize = require('./finalize_release.cjs');

function fixture() {
  const base = 'a'.repeat(40), head = 'b'.repeat(40), merged = 'c'.repeat(40);
  const pr = { number: 34, title: 'Container catalog', state: 'open', merged: false, draft: false,
    user: { login: 'owner' }, head: { ref: 'agent/release-v2.14.0', sha: head, repo: { full_name: 'owner/repo' } },
    base: { ref: 'main', sha: base, repo: { full_name: 'owner/repo' } } };
  const context = { repo: { owner: 'owner', repo: 'repo' }, eventName: 'pull_request', payload: { pull_request: structuredClone(pr) } };
  const calls = [];
  const github = { rest: {
    pulls: { get: async () => ({ data: pr }), merge: async args => { calls.push(['merge', args]); return { data: { merged: true, sha: merged } }; } },
    repos: { getContent: async () => ({ data: { type: 'file', content: Buffer.from('2.14.0\n').toString('base64') } }), getBranch: async () => ({ data: { commit: { sha: base } } }) },
    actions: { createWorkflowDispatch: async args => { calls.push(['dispatch', args]); } },
  } };
  const summary = { addHeading() { return this; }, addRaw() { return this; }, async write() {} };
  return { github, context, core: { summary }, pr, calls, merged };
}

test('merges only the tested head and dispatches both workflows for that merge', async () => {
  const f = fixture(); await finalize(f);
  assert.equal(f.calls[0][1].sha, f.context.payload.pull_request.head.sha);
  assert.equal(f.calls[0][1].merge_method, 'squash');
  assert.deepEqual(f.calls.slice(1).map(x => [x[1].workflow_id, x[1].inputs]), [
    ['ci.yml', { commit: f.merged }], ['tag-release.yml', { version: '2.14.0', commit: f.merged }],
  ]);
});

for (const [name, change] of [
  ['fork', f => { f.pr.head.repo.full_name = 'someone/repo'; }],
  ['other author', f => { f.pr.user.login = 'contributor'; }],
  ['draft', f => { f.pr.draft = true; }],
  ['stale tests', f => { f.pr.head.sha = 'd'.repeat(40); }],
  ['untrusted base', f => { f.pr.base.ref = 'develop'; }],
  ['branch suffix', f => { f.pr.head.ref += '-try'; }],
  ['wrong version', f => { f.pr.head.ref = 'agent/release-v2.15.0'; }],
  ['closed without merge', f => { f.pr.state = 'closed'; }],
  ['main moved', f => { f.context.payload.pull_request.base.sha = 'd'.repeat(40); }],
]) test(`refuses ${name} before any write`, async () => {
  const f = fixture(); change(f); await assert.rejects(finalize(f)); assert.deepEqual(f.calls, []);
});

test('a refused merge never queues publication', async () => {
  const f = fixture(); f.github.rest.pulls.merge = async () => ({ data: { merged: false, message: 'Required review missing' } });
  await assert.rejects(finalize(f), /Required review/); assert.deepEqual(f.calls, []);
});

test('rerunning after a dispatch failure resumes the already merged release', async () => {
  const f = fixture(); f.pr.merged = true; f.pr.state = 'closed'; f.pr.merge_commit_sha = f.merged;
  await finalize(f); assert.equal(f.calls.length, 2); assert.ok(f.calls.every(x => x[0] === 'dispatch'));
});
