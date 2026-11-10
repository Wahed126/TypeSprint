import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { roundFeedback } from '../feedback.js';
const catalog = JSON.parse(readFileSync(new URL('../data/feedback.json', import.meta.url)));
const fixtures = JSON.parse(readFileSync(new URL('./fixtures/feedback.json', import.meta.url)));
for (const fixture of fixtures.cases) {
  test(`feedback: ${fixture.id}`, () => {
    const score = { ...fixtures.base, ...fixture.score };
    score.correctCharacters = score.correct_characters;
    const result = roundFeedback(score, catalog);
    assert.equal(result.key, fixture.key);
    assert.equal(result.tip, fixture.tip);
    assert.equal(result.title, catalog.profiles[fixture.key].title);
    assert.ok(result.message.length > 0);
    assert.ok(!result.message.includes('{'));
    if (result.tip === 'mistake_load') {
      assert.ok(result.message.includes(String(score.mistakes)));
      assert.ok(result.message.includes(score.elapsed.toFixed(1)));
    }
  });
}
test('feedback examples cover every message and advice', () => {
  assert.deepEqual(new Set(fixtures.cases.map(row => row.key)), new Set(Object.keys(catalog.profiles)));
  assert.deepEqual(new Set(fixtures.cases.map(row => row.tip).filter(Boolean)), new Set(Object.keys(catalog.tips)));
});
