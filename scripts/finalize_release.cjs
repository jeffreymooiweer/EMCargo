/** Finish an owner-created release PR after its test and image jobs succeed. */
async function finalizeRelease({ github, context, core }) {
  const { owner, repo } = context.repo;
  const event = context.payload.pull_request;
  const sameRepo = value => value?.toLowerCase() === `${owner}/${repo}`.toLowerCase();
  const check = (value, message) => { if (!value) throw new Error(message); };
  check(context.eventName === 'pull_request' && event, 'Expected a pull request event');
  const { data: pr } = await github.rest.pulls.get({ owner, repo, pull_number: event.number });
  check(sameRepo(pr.head.repo?.full_name) && sameRepo(pr.base.repo?.full_name), 'Release must stay in this repository');
  check(pr.user.login.toLowerCase() === owner.toLowerCase(), 'Only the repository owner can request automatic releases');
  check(!pr.draft && pr.base.ref === 'main', 'Release must be ready and target main');
  check(pr.head.sha === event.head.sha, 'Head changed since the tests started');
  const match = /^agent\/release-v(\d+\.\d+\.\d+)$/.exec(pr.head.ref);
  check(match, 'Branch must be exactly agent/release-vX.Y.Z');
  const version = match[1];
  const { data: file } = await github.rest.repos.getContent({ owner, repo, path: 'VERSION', ref: pr.head.sha });
  check(file.type === 'file' && Buffer.from(file.content, 'base64').toString('utf8').trim() === version,
    'Release branch and VERSION disagree');
  let commit = pr.merge_commit_sha;
  if (!pr.merged) {
    check(pr.state === 'open', 'Pull request was closed without merging');
    const { data: main } = await github.rest.repos.getBranch({ owner, repo, branch: 'main' });
    check(main.commit.sha === event.base.sha, 'Main changed since the tests started; update the release branch');
    const { data: merge } = await github.rest.pulls.merge({
      owner, repo, pull_number: pr.number, sha: event.head.sha, merge_method: 'squash',
      commit_title: `Release v${version}: ${pr.title.replace(/^Release v[0-9.]+[: ]*/, "")}`,
    });
    check(merge.merged, merge.message || 'GitHub did not merge the pull request');
    commit = merge.sha;
  }
  check(/^[a-f0-9]{40}$/.test(commit || ''), 'GitHub did not return a merge commit');
  // GITHUB_TOKEN merges do not trigger push/closed workflows. Dispatch both
  // explicitly, pinned to the same commit. A rerun safely resumes after a merge.
  for (const [workflow_id, inputs] of [
    ['ci.yml', { commit }], ['tag-release.yml', { version, commit }],
  ]) {
    await github.rest.actions.createWorkflowDispatch({ owner, repo, workflow_id, ref: 'main', inputs });
  }
  await core.summary.addHeading(`Release v${version} queued`)
    .addRaw(`Merged ${commit}. Main CI and release publication continue in GitHub Actions. This does not yet mean published.`)
    .write();
  return { version, commit };
}
module.exports = finalizeRelease;
