const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const root = process.cwd();
const previous = '/Users/pedrocollet/.codex/worktrees/broadcast-experience-refinement-v2/NFL Sideline';
const esbuild = require(path.join(root, 'web-ui/node_modules/esbuild'));
function load(directory) {
  const compiled = esbuild.buildSync({ stdin: { contents: "export { games } from './fixtures'; export { readSlice } from './editorial';", resolveDir: path.join(directory, 'web-ui/broadcast-experience') }, bundle: true, platform: 'node', format: 'cjs', write: false, loader: { '.png': 'empty' } });
  const module = { exports: {} };
  vm.runInNewContext(compiled.outputFiles[0].text, { module, exports: module.exports });
  return module.exports;
}
const before = load(previous), after = load(root);
const stable = reading => JSON.parse(JSON.stringify({ decision: reading.decision, context: reading.context, samples: reading.samples, evidence: reading.evidence }));
const results = [];
for (const game of before.games) for (const period of ['game', 'first', 'second']) for (const play of ['all', 'pass', 'rush']) {
  const oldReading = before.readSlice(game, period, play);
  const newReading = after.readSlice(after.games.find(g => g.id === game.id), period, play);
  assert.deepEqual(stable(oldReading), stable(newReading));
  results.push({ game: game.id, period, play, ...stable(newReading), beforeTitle: oldReading.title, afterTitle: newReading.title });
}
const bothNegative = results.filter(r => r.samples.every(s => s.epa !== null && s.epa < 0));
function scenario(values, counts = [20, 20], successes = [10, 10]) {
  return { ...before.games[0], sides: before.games[0].sides.map((s, i) => ({ ...s, halves: [{ ...s.halves[0], pass: { plays: counts[i], success: successes[i], epa: values[i] * counts[i], yards: 120 } }, s.halves[1]] })) };
}
const edges = [scenario([-.1, -.2]), scenario([0, -.2]), scenario([.2, 0]), scenario([.1004, .1001]), scenario([.101, .109]), scenario([.15, -.1], [20, 20], [8, 12]), scenario([0, .1], [0, 20], [0, 10]), scenario([.1, .2], [8, 20], [4, 10])];
for (const game of edges) assert.deepEqual(stable(before.readSlice(game, 'first', 'pass')), stable(after.readSlice(game, 'first', 'pass')));
const immutable = ['fixtures.ts', 'chartScale.ts', 'state.ts', 'experience.css', 'editorial.test.ts', 'fixtures.test.ts'];
for (const file of immutable) assert.equal(fs.readFileSync(path.join(previous, 'web-ui/broadcast-experience', file), 'utf8'), fs.readFileSync(path.join(root, 'web-ui/broadcast-experience', file), 'utf8'));
console.log(JSON.stringify({ fixtureSelections: results.length, controlledEdgeCases: edges.length, immutableFiles: immutable, bothNegativeFixtureSelections: bothNegative, bothNegativePreview: { before: before.readSlice(edges[0], 'first', 'pass'), after: after.readSlice(edges[0], 'first', 'pass') }, results }, null, 2));
