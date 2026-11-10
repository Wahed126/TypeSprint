import { Round } from './engine.js';
import { Store } from './storage.js';
import { roundFeedback } from './feedback.js';

const $ = id => document.getElementById(id);
const names = { english: 'English', german: 'Deutsch', python: 'Python', typescript: 'TypeScript' };
let browserStorage;
try { browserStorage = window.localStorage; } catch { browserStorage = { getItem: () => null, setItem: () => { throw new Error('Storage denied'); } }; }
const store = new Store(browserStorage);
let exercises, feedbackCatalog, game, saved = false, composing = false, compositionBase = null, before = null, page = 'play';
let referenceLength = 0, currentSpan = null;
const typing = $('typing');
const target = $('target');
const randomPassage = category => exercises.practice[category][Math.floor(Math.random() * exercises.practice[category].length)];
const words = category => Array.from({ length: 180 }, () => {
  const list = exercises.words[category]; return list[Math.floor(Math.random() * list.length)];
}).join(' ');
function notice(message) { $('notice').textContent = message; $('notice').hidden = !message; }
function persistSettings() {
  if (!store.settings({ mode: $('mode').value, category: $('category').value, duration: Number($('duration').value) })) notice(store.error);
}
function categories(preferred = $('category').value) {
  const keys = $('mode').value === 'practice' ? Object.keys(names) : ['english', 'german'];
  $('category').replaceChildren(...keys.map(key => new Option(names[key], key)));
  $('category').value = keys.includes(preferred) ? preferred : 'english';
  $('duration').disabled = $('mode').value !== 'sprint';
}
function setPage(name, focus = true) {
  page = name;
  for (const key of ['play', 'history', 'settings']) $(`page-${key}`).hidden = key !== name;
  for (const button of document.querySelectorAll('[data-page]')) {
    const active = button.dataset.page === name;
    button.classList.toggle('active', active);
    if (active) button.setAttribute('aria-current', 'page'); else button.removeAttribute('aria-current');
  }
  if (name === 'history') renderHistory();
  if (focus && name === 'play') (game?.finished ? $('results-heading') : typing).focus({ preventScroll: true });
  if (name === 'play' && game) render();
}
function newRound(focus = true) {
  // Restart may arrive before the timer callback or pending results paint.
  if (game && game.tick() && !saved) finish();
  const config = { mode: $('mode').value, category: $('category').value, duration: Number($('duration').value) };
  game = new Round(config, config.mode === 'practice' ? randomPassage(config.category) : words(config.category), {
    moreWords: () => words(config.category),
  });
  saved = false; composing = false; compositionBase = null; before = null;
  typing.value = ''; typing.disabled = false;
  typing.classList.toggle('code', ['python', 'typescript'].includes(config.category));
  typing.wrap = typing.classList.contains('code') ? 'off' : 'soft';
  target.classList.toggle('code', typing.classList.contains('code'));
  target.replaceChildren(); referenceLength = 0; currentSpan = null;
  target.scrollTop = 0; target.scrollLeft = 0;
  $('round-view').hidden = false; $('results').hidden = true;
  $('feedback').textContent = '';
  $('instructions').textContent = typing.classList.contains('code')
    ? 'Four spaces per indent. Enter for a new line. Tab moves focus.'
    : config.mode === 'survival' ? 'Correct word + Space = +1s. Each position earns once.' : 'Start typing to begin. Backspace to correct.';
  persistSettings(); render();
  if (focus) { setPage('play', false); typing.focus({ preventScroll: true }); }
}
function cursorPosition() { return Array.from(typing.value.slice(0, typing.selectionStart)).length; }
function showCurrent() {
  const position = Math.min(cursorPosition(), game.target.length - 1);
  const next = target.children[position];
  if (currentSpan !== next) {
    currentSpan?.classList.remove('current');
    next?.classList.add('current'); currentSpan = next;
  }
  if (next && page === 'play' && !game.finished) {
    const rect = next.getBoundingClientRect(), view = target.getBoundingClientRect(), pad = 12;
    if (rect.bottom > view.bottom - pad) target.scrollTop += rect.bottom - view.bottom + pad;
    if (rect.top < view.top + pad) target.scrollTop += rect.top - view.top - pad;
    if (rect.right > view.right - pad) target.scrollLeft += rect.right - view.right + pad;
    if (rect.left < view.left + pad) target.scrollLeft += rect.left - view.left - pad;
  }
  return game.target[position];
}
function render() {
  if (!game) return;
  if (referenceLength < game.target.length) {
    const fragment = document.createDocumentFragment();
    for (let i = referenceLength; i < game.target.length; i++) {
      const span = document.createElement('span'); span.className = 'char'; span.textContent = game.target[i]; fragment.append(span);
    }
    target.append(fragment); referenceLength = game.target.length;
  }
  for (let i = 0; i < target.children.length; i++) {
    const span = target.children[i], entered = i < game.text.length;
    span.classList.toggle('correct', entered && game.text[i] === game.target[i]);
    span.classList.toggle('error', entered && game.text[i] !== game.target[i]);
    if (entered && game.text[i] !== game.target[i]) span.title = `You typed ${JSON.stringify(game.text[i])}`;
    else span.removeAttribute('title');
  }
  const next = showCurrent();
  stats(next);
  requestAnimationFrame(() => { if (game && !game.finished) showCurrent(); });
}
function stats(next = game.target[Math.min(cursorPosition(), game.target.length - 1)]) {
  const score = game.score();
  $('stat-wpm').textContent = game.startedAt !== null && score.elapsed < 1 ? '—' : score.wpm.toFixed(0);
  $('stat-accuracy').textContent = `${score.accuracy.toFixed(0)}%`;
  $('stat-mistakes').textContent = score.mistakes;
  const remaining = game.remaining();
  $('stat-clock').textContent = remaining === null ? `${score.elapsed.toFixed(0)}s` : `${remaining.toFixed(1)}s`;
  $('state').textContent = game.startedAt === null ? 'Ready when you are' : 'Keep your rhythm';
  const hint = `Next: ${{ ' ': 'Space', '\n': 'Enter', '\t': 'Tab' }[next] ?? `“${next}”`}`;
  $('progress').textContent = game.config.mode === 'practice' ? `${hint} · ${Math.min(game.text.length, game.target.length)}/${game.target.length}`
    : game.config.mode === 'survival' ? `${hint} · +${score.bonusSeconds}s`
    : game.startedAt === null ? 'Clock starts on your first character' : hint;
}
function finish() {
  if (!game.finished || saved) return;
  saved = true;
  const score = game.score();
  const result = store.save(score);
  const feedback = roundFeedback(score, feedbackCatalog);
  if (!result.persisted) notice(store.error);
  $('result-mode').textContent = `${score.mode[0].toUpperCase() + score.mode.slice(1)} · ${names[score.category]}${score.mode === 'sprint' ? ` · ${score.duration}s` : ''}`;
  $('result-wpm').textContent = score.wpm.toFixed(1);
  $('result-accuracy').textContent = `${score.accuracy.toFixed(1)}%`;
  $('result-mistakes').textContent = score.mistakes;
  $('result-elapsed').textContent = `${score.elapsed.toFixed(1)}s`;
  $('round-feedback').dataset.profile = feedback.key;
  $('round-feedback-title').textContent = feedback.title;
  $('round-feedback-message').textContent = feedback.message;
  $('personal-best').textContent = result.newBest ? 'New personal best!' : result.persisted ? 'Saved to your history' : 'Result kept for this visit only';
  $('result-detail').textContent = `${score.correctCharacters} matched characters · ${score.correctAttempts} correct / ${score.attempts} attempts. Corrected mistakes stay in your stats.`;
  typing.disabled = true;
  $('round-view').hidden = true; $('results').hidden = false;
  // Continued typing (especially Space/Enter) must not activate a new round.
  // Announce the result, then let Tab or a click deliberately reach Play again.
  if (page === 'play') $('results-heading').focus({ preventScroll: true });
  if (page === 'history') renderHistory();
}
function tick() { if (game) { if (game.tick()) finish(); else if (page === 'play') stats(); } }
function snapshot() { return { value: typing.value, start: typing.selectionStart, end: typing.selectionEnd }; }
function commit(base, event) {
  if (!game || saved) return;
  const value = typing.value, old = base?.value ?? game.text.join('');
  let start, end, inserted;
  if (event?.inputType === 'insertText' && event.data !== null && base
      && value === old.slice(0, base.start) + event.data + old.slice(base.end)) {
    start = Array.from(old.slice(0, base.start)).length;
    end = Array.from(old.slice(0, base.end)).length;
    inserted = event.data;
  } else {
    const a = Array.from(old), b = Array.from(value);
    let prefix = 0, suffix = 0;
    while (prefix < a.length && prefix < b.length && a[prefix] === b[prefix]) prefix++;
    while (suffix < a.length - prefix && suffix < b.length - prefix && a[a.length - 1 - suffix] === b[b.length - 1 - suffix]) suffix++;
    start = prefix; end = a.length - suffix; inserted = b.slice(prefix, b.length - suffix).join('');
  }
  game.edit(start, end, inserted);
  if (game.text.join('') !== value) typing.value = game.text.join('');
  before = null;
  render();
  if (inserted && Array.from(inserted).some((ch, i) => ch !== game.target[start + i])) {
    const expected = game.target[start];
    $('feedback').textContent = `Check the underlined text. Expected ${expected === ' ' ? 'a space' : expected === '\n' ? 'a new line' : JSON.stringify(expected ?? 'the end of the passage')}. Backspace to correct.`;
  } else $('feedback').textContent = '';
  if (game.finished) finish();
}
typing.addEventListener('beforeinput', event => {
  if (!game || saved) return;
  if (event.inputType === 'historyUndo' || event.inputType === 'historyRedo') { event.preventDefault(); return; }
  if (game.tick()) { event.preventDefault(); typing.value = game.text.join(''); finish(); return; }
  if (!composing) before = snapshot();
});
typing.addEventListener('input', event => {
  if (composing || event.isComposing) return;
  // Some IMEs emit a final input after compositionend. It is already committed.
  if (event.inputType?.includes('Composition') && typing.value === game?.text.join('')) return;
  commit(before, event);
});
typing.addEventListener('compositionstart', () => { composing = true; compositionBase = snapshot(); });
typing.addEventListener('compositionend', () => { composing = false; commit(compositionBase); compositionBase = null; });
for (const name of ['click', 'keyup', 'select']) typing.addEventListener(name, () => { if (game && !composing) { showCurrent(); stats(); } });
document.addEventListener('keydown', event => {
  if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 'r' && !event.shiftKey) { event.preventDefault(); if (game) newRound(); return; }
  const focused = document.activeElement;
  if (game?.finished && [' ', 'Enter'].includes(event.key)
      && (focused === $('results-heading') || (focused === $('again') && event.repeat))) {
    event.preventDefault();
  }
});
for (const button of document.querySelectorAll('[data-page]')) button.addEventListener('click', () => setPage(button.dataset.page));
$('mode').addEventListener('change', () => { categories(); newRound(false); });
$('category').addEventListener('change', () => newRound(false));
$('duration').addEventListener('change', () => newRound(false));
$('restart').addEventListener('click', () => newRound());
$('again').addEventListener('click', () => newRound());
$('history-filter').addEventListener('change', renderHistory);
function renderHistory() {
  const rows = store.history($('history-filter').value);
  $('history-empty').hidden = rows.length !== 0; $('history-table').hidden = rows.length === 0;
  $('history-body').replaceChildren(...rows.map(row => {
    const tr = document.createElement('tr');
    const title = document.createElement('td');
    title.textContent = `${row.mode[0].toUpperCase() + row.mode.slice(1)} · ${names[row.category]}${row.mode === 'sprint' ? ` · ${row.duration}s` : ''}`;
    const date = document.createElement('small'); date.textContent = new Date(row.createdAt).toLocaleString(); title.append(date); tr.append(title);
    for (const value of [row.wpm.toFixed(1), `${row.accuracy.toFixed(1)}%`, row.mistakes, `${row.elapsed.toFixed(1)}s`]) {
      const td = document.createElement('td'); td.textContent = value; tr.append(td);
    }
    return tr;
  }));
}
function fontSize(value) {
  const size = Math.min(36, Math.max(16, Number(value) || 22));
  document.documentElement.style.setProperty('--font-size', `${size}px`);
  $('font-size').value = size; $('font-value').textContent = `${size} px`;
}
$('font-size').addEventListener('input', event => { fontSize(event.target.value); if (!store.settings({ fontSize: Number(event.target.value) })) notice(store.error); });
document.addEventListener('visibilitychange', tick);
window.addEventListener('pagehide', () => { if (game && game.tick() && !saved) finish(); });
window.addEventListener('resize', () => { if (game) showCurrent(); });
try {
  const [response, feedbackResponse] = await Promise.all([
    fetch('./data/exercises.json'), fetch('./data/feedback.json'),
  ]);
  if (!response.ok) throw new Error(`Exercise load failed (${response.status})`);
  if (!feedbackResponse.ok) throw new Error(`Feedback load failed (${feedbackResponse.status})`);
  [exercises, feedbackCatalog] = await Promise.all([response.json(), feedbackResponse.json()]);
  $('mode').disabled = false; $('category').disabled = false; $('restart').disabled = false;
  const settings = store.data.settings;
  $('mode').value = ['sprint', 'practice', 'survival'].includes(settings.mode) ? settings.mode : 'sprint';
  $('duration').value = [15, 30, 60].includes(settings.duration) ? settings.duration : 30;
  categories(settings.category); fontSize(settings.fontSize);
  if (store.error) notice(store.error);
  newRound();
  setInterval(tick, 50);
  if ('serviceWorker' in navigator && window.isSecureContext) {
    navigator.serviceWorker.register('./sw.js').then(() => {
      navigator.serviceWorker.ready.then(() => { $('offline-status').textContent = 'Ready for your next offline round.'; });
    }).catch(() => { $('offline-status').textContent = 'Offline caching unavailable in this browser.'; });
  }
} catch (error) { typing.disabled = true; notice(`${error.message}. Serve this directory over HTTP; see the README.`); }
