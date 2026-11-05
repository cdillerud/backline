// Synthetic asynchronous request regression tests. No network, accounts or DB.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const source = fs.readFileSync('src/static/app.js', 'utf8');
function extract(begin, end) {
  const start = source.indexOf(begin), finish = source.indexOf(end, start);
  assert(start >= 0 && finish > start, 'workspace function boundaries changed');
  return source.slice(start, finish);
}
const subject = extract('async function refreshStudio()', '\nfunction studio()') +
  '\n' + extract('async function refreshTours()', '\nfunction touring()') +
  '\nglobalThis.subject = { refreshStudio, refreshTours };';

function harness() {
  let session = 'session-a';
  const pending = [];
  const calls = [];
  const state = {
    band: 1, section: 'dashboard', studioGig: 11, selectedTour: 22,
    data: { currentRoute: { old: true } }
  };
  const context = {
    state,
    sessionStorage: { getItem: () => session },
    api: url => new Promise((resolve, reject) => {
      calls.push(url); pending.push({url, resolve, reject});
    }),
    render: () => { context.renders++; },
    toast: () => { context.toasts++; },
    renders: 0, toasts: 0
  };
  vm.runInNewContext(subject, context, { filename: 'workspace-guards.js' });
  const take = fragment => {
    const idx = pending.findIndex(p => p.url.includes(fragment));
    assert(idx >= 0, 'expected outstanding request: ' + fragment);
    return pending.splice(idx, 1)[0];
  };
  return { state, context, calls, pending, take, setSession: value => { session = value; } };
}
async function tick() { await Promise.resolve(); await Promise.resolve(); }

async function studioBandSwitch() {
  const h = harness();
  const request = h.context.subject.refreshStudio();
  h.state.band = 2;
  h.take('/market').resolve([{title: 'private band 1 event'}]);
  h.take('/campaign').resolve([{body: 'private band 1 draft'}]);
  await request;
  assert.equal(h.state.data.studioMarket, undefined);
  assert.equal(h.state.data.studioDrafts, undefined);
  assert.equal(h.state.section, 'dashboard');
  assert.equal(h.context.renders, 0);
}
async function studioNavigationAndSession() {
  for (const change of ['navigation', 'logout']) {
    const h = harness();
    const request = h.context.subject.refreshStudio();
    if (change === 'navigation') h.state.section = 'schedule';
    else h.setSession(null);
    h.take('/market').resolve([]);
    h.take('/campaign').resolve([]);
    await request;
    assert.equal(h.context.renders, 0, change);
    assert.equal(h.state.data.studioMarket, undefined);
  }
}
async function studioLatestWins() {
  const h = harness();
  const first = h.context.subject.refreshStudio();
  h.state.studioGig = 12;
  const second = h.context.subject.refreshStudio();
  h.take('/gigs/12/market').resolve([{title: 'new'}]);
  h.take('/gigs/12/campaign').resolve([]);
  await second;
  h.take('/gigs/11/market').resolve([{title: 'old'}]);
  h.take('/gigs/11/campaign').resolve([]);
  await first;
  assert.equal(h.state.data.studioMarket[0].title, 'new');
  assert.equal(h.context.renders, 1);
}
async function tourBandSwitch() {
  const h = harness();
  const request = h.context.subject.refreshTours();
  h.state.band = 2;
  h.take('/bands/1/tours').resolve([{id: 22}]);
  await request;
  assert.equal(h.calls.length, 1, 'should not request old-band route');
  assert.equal(h.state.data.tours, undefined);
  assert.equal(h.context.renders, 0);
}
async function tourSelectionSwitch() {
  const h = harness();
  const request = h.context.subject.refreshTours();
  h.take('/bands/1/tours').resolve([{id: 22}]);
  await tick();
  h.state.selectedTour = 33;
  h.take('/tours/22/route').resolve({tour: {name: 'old'}});
  await request;
  assert.equal(h.state.data.currentRoute.old, true);
  assert.equal(h.context.renders, 0);
}
async function tourNoSelectionClearsRoute() {
  const h = harness();
  h.state.selectedTour = null;
  const request = h.context.subject.refreshTours();
  h.take('/bands/1/tours').resolve([]);
  await request;
  assert.equal(h.state.data.currentRoute, null);
  assert.equal(h.state.section, 'touring');
  assert.equal(h.context.renders, 1);
}
async function failureAfterLogoutIsSilent() {
  const h = harness();
  const request = h.context.subject.refreshTours();
  h.setSession(null);
  h.take('/bands/1/tours').reject(new Error('late private request failure'));
  await request;
  assert.equal(h.context.toasts, 0);
}
(async () => {
  await studioBandSwitch();
  await studioNavigationAndSession();
  await studioLatestWins();
  await tourBandSwitch();
  await tourSelectionSwitch();
  await tourNoSelectionClearsRoute();
  await failureAfterLogoutIsSilent();
  process.stdout.write('Backline workspace async guards: 7 scenarios passed\n');
})().catch(error => { console.error(error); process.exitCode = 1; });
