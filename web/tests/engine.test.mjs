import test from 'node:test';
import assert from 'node:assert/strict';
import { Round } from '../engine.js';
const setup = (config = {}, target = 'hello world again') => {
  let now = 100;
  const round = new Round({ duration: 15, ...config }, target, { clock: () => now });
  return { round, advance: seconds => { now += seconds; } };
};
test('first character starts timer, including an error', () => {
  const { round, advance } = setup(); advance(500); round.tick();
  assert.equal(round.startedAt, null); assert.equal(round.remaining(), 15);
  round.insert('x'); assert.equal(round.startedAt, 600); assert.equal(round.score().mistakes, 1);
});
test('empty input and empty Backspace do not start timer', () => {
  const { round } = setup(); round.insert(''); round.backspace(); assert.equal(round.startedAt, null); assert.equal(round.attempts, 0);
});
test('input at deadline is rejected without attempts', () => {
  const { round, advance } = setup(); round.insert('h'); advance(15);
  assert.equal(round.insert('e'), false); assert.equal(round.text.join(''), 'h'); assert.equal(round.attempts, 1); assert.equal(round.score().elapsed, 15);
});
test('input before deadline counts; delayed tick clamps elapsed', () => {
  const { round, advance } = setup(); round.insert('h'); advance(14.999); assert.ok(round.insert('e')); advance(60); round.tick(); assert.equal(round.score().elapsed, 15);
});
test('correction retains attempt mistakes while final text drives WPM', () => {
  const { round, advance } = setup(); round.insert('x'); round.backspace(); advance(10); round.insert('hello');
  const score = round.score(); assert.equal(score.mistakes, 1); assert.equal(score.attempts, 6); assert.equal(score.correctCharacters, 5); assert.equal(score.wpm, 6); assert.equal(score.accuracy, 5 / 6 * 100);
});
test('deleting correct text reduces final WPM but not attempt history', () => {
  const { round, advance } = setup(); round.insert('hello'); round.backspace(); advance(12); round.insert('x'); assert.equal(round.score().wpm, 4); assert.equal(round.correctAttempts, 5);
});
test('selection replacement and identical re-entry are attempts', () => {
  const { round } = setup(); round.insert('hxllo'); round.edit(1, 2, 'e'); round.edit(0, 1, 'h'); assert.equal(round.text.join(''), 'hello'); assert.equal(round.attempts, 7); assert.equal(round.score().mistakes, 1);
});
test('Unicode code points are counted once', () => {
  const { round } = setup({ category: 'german' }, 'äöüß 😀'); round.insert('äöüß 😀'); assert.equal(round.attempts, 6); assert.equal(round.score().accuracy, 100);
});
test('Practice is untimed and preserves literal code', () => {
  const target = 'def run():\n    return 1'; const { round, advance } = setup({ mode: 'practice', category: 'python' }, target);
  round.insert('def run():\n'); advance(3600); assert.equal(round.tick(), false); assert.equal(round.remaining(), null); round.insert('    return 1'); assert.ok(round.finished); assert.equal(round.text.join(''), target); assert.equal(round.score().elapsed, 3600); assert.equal(round.score().duration, 0);
});
test('Practice ends at passage length even with mistakes', () => { const { round } = setup({ mode: 'practice' }, 'hello'); round.insert('hxllo'); assert.ok(round.finished); assert.equal(round.score().mistakes, 1); });
test('new round resets attempts, text and timing', () => { const { round } = setup(); round.insert('wrong'); const next = new Round(round.config, 'hello'); assert.equal(next.startedAt, null); assert.equal(next.attempts, 0); assert.equal(next.text.length, 0); });
test('Survival requires a correct word and correct separator', () => {
  const { round } = setup({ mode: 'survival' }, 'one two three'); assert.equal(round.remaining(), 30); round.insert('one'); assert.equal(round.bonusSeconds, 0); round.insert(' '); assert.equal(round.bonusSeconds, 1); assert.equal(round.remaining(), 31);
});
test('Survival corrections can earn once; retyping cannot farm bonuses', () => {
  const { round } = setup({ mode: 'survival' }, 'one two three'); round.insert('oxe '); assert.equal(round.bonusSeconds, 0); round.edit(1, 2, 'n'); assert.equal(round.bonusSeconds, 1); round.backspace(); round.insert(' '); assert.equal(round.bonusSeconds, 1); round.edit(0, 4, 'one '); assert.equal(round.bonusSeconds, 1);
});
test('repeated words at distinct positions each earn a bonus', () => {
  const { round } = setup({ mode: 'survival' }, 'one one one next'); round.insert('one one one '); assert.equal(round.bonusSeconds, 3);
});
test('Survival cannot earn at the exact deadline', () => {
  const { round, advance } = setup({ mode: 'survival' }, 'one two'); round.insert('one'); advance(30); assert.equal(round.insert(' '), false); assert.equal(round.bonusSeconds, 0);
});
test('Survival bonus before deadline extends the round', () => {
  const { round, advance } = setup({ mode: 'survival' }, 'one two'); round.insert('one'); advance(29.99); round.insert(' '); advance(.02); assert.equal(round.tick(), false); advance(1); assert.equal(round.tick(), true); assert.equal(round.score().elapsed, 31);
});
test('word supply extends as far as needed', () => {
  const round = new Round({}, 'hi', { moreWords: () => 'word '.repeat(120) }); round.insert('x'.repeat(4000)); assert.ok(round.target.length - round.text.length >= 500); assert.equal(round.finished, false);
});
test('invalid configurations and edits fail clearly', () => {
  assert.throws(() => new Round({ duration: 2 }, 'x')); assert.throws(() => new Round({ mode: 'survival', category: 'python' }, 'x')); assert.throws(() => new Round({}, '')); assert.throws(() => setup().round.edit(2, 3, 'x'));
});
