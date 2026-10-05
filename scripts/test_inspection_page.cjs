// Source-level JavaScript/HTML tests. No browser or network; does not claim visual inspection.
const fs = require('node:fs');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const source = fs.readFileSync(process.argv[2], 'utf8');
const cards = [...source.matchAll(/<article ([^>]+)>/g)].map(match => ({
  dataset: Object.fromEntries([...match[1].matchAll(/data-(\w+)="([^"]*)"/g)].map(m => [m[1], m[2]])), hidden: false,
}));
const selectors = [...source.matchAll(/<select id="([^"]+)">([\s\S]*?)<\/select>/g)].map(m => ({
  id: m[1], value: '', options: [...m[2].matchAll(/<option value="([^"]*)"/g)].map(m => m[1]),
  addEventListener(event, fn) { assert.equal(event, 'change'); this.change = fn; },
}));
assert.equal(selectors.length, 4);
assert.ok(cards.length > 0);
assert.equal((source.match(/<details>/g) || []).length, cards.length + 1);
assert.equal((source.match(/<\/details>/g) || []).length, cards.length + 1);
assert.equal((source.match(/<summary>/g) || []).length, cards.length + 1);
assert.equal((source.match(/<section>/g) || []).length, cards.length * 4);
assert.ok(source.includes('[hidden]{display:none!important}'));
assert.ok(source.includes('repeat(4,minmax(0,1fr))'));
assert.ok(source.includes('@media(max-width:640px)'));
assert.ok(!/<(?:iframe|img|link)\b|\bsrc=/.test(source));
const count = {textContent: ''};
const document = {
  querySelectorAll(type) { return type === 'select' ? selectors : cards; },
  getElementById(id) { assert.equal(id, 'count'); return count; },
};
const scripts = [...source.matchAll(/<script>([\s\S]*?)<\/script>/g)];
assert.equal(scripts.length, 1);
vm.runInNewContext(scripts[0][1], {document}, {timeout: 1000});
assert.equal(cards.filter(c => !c.hidden).length, cards.length);
let checks = 0;
for (const select of selectors) {
  for (const value of select.options) {
    select.value = value;
    select.change();
    const expected = cards.filter(c => !value || (select.id === 'patterns' ? c.dataset.patterns.split(' ').includes(value) : c.dataset[select.id] === value));
    assert.deepEqual(cards.filter(c => !c.hidden), expected);
    assert.equal(count.textContent, `${expected.length} de ${cards.length} casos exibidos`);
    checks++;
  }
  select.value = ''; select.change();
}
const cohort = selectors.find(s => s.id === 'cohort');
const coverage = selectors.find(s => s.id === 'coverage');
cohort.value = 'synthetic'; coverage.value = 'partial'; coverage.change();
assert.ok(cards.filter(c => !c.hidden).every(c => c.dataset.cohort === 'synthetic' && c.dataset.coverage === 'partial'));
console.log(JSON.stringify({mode:'source_unit_test_not_browser', cards:cards.length, filterOptionsTested:checks, combinedFilters:true, detailsMarkup:true, fourBlocks:true, noExternalAssets:true}));
