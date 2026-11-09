/** Rules and monotonic timing, independent of DOM and storage. Time is seconds. */
export class Round {
  constructor(config, target, { clock = () => performance.now() / 1000, moreWords = null } = {}) {
    const { mode = 'sprint', category = 'english', duration = 30 } = config;
    if (!['sprint', 'practice', 'survival'].includes(mode)) throw new Error('Unknown mode');
    const allowed = mode === 'practice' ? ['english', 'german', 'python', 'typescript'] : ['english', 'german'];
    if (!allowed.includes(category)) throw new Error('Unavailable category');
    if (mode === 'sprint' && ![15, 30, 60].includes(duration)) throw new Error('Invalid duration');
    if (!target) throw new Error('Empty exercise');
    this.config = { mode, category, duration };
    this.target = Array.from(target);
    this.text = [];
    this.clock = clock;
    this.moreWords = moreWords;
    this.startedAt = null;
    this.endedAt = null;
    this.attempts = 0;
    this.correctAttempts = 0;
    this.awardedWords = new Set();
    this.bonusSeconds = 0;
  }
  get finished() { return this.endedAt !== null; }
  get deadline() {
    if (this.startedAt === null || this.config.mode === 'practice') return null;
    return this.startedAt + (this.config.mode === 'sprint' ? this.config.duration : 30) + this.bonusSeconds;
  }
  tick(now = this.clock()) {
    if (!this.finished && this.deadline !== null && now >= this.deadline) this.endedAt = this.deadline;
    return this.finished;
  }
  elapsed(now = this.clock()) {
    if (this.startedAt === null) return 0;
    const stop = this.endedAt ?? now;
    return Math.max(0, Math.min(stop, this.deadline ?? stop) - this.startedAt);
  }
  remaining(now = this.clock()) {
    if (this.config.mode === 'practice') return null;
    if (this.startedAt === null) return this.config.mode === 'sprint' ? this.config.duration : 30;
    return Math.max(0, this.deadline - (this.endedAt ?? now));
  }
  extend(needed) {
    if (this.config.mode === 'practice' || !this.moreWords) return;
    while (this.target.length - needed < 500) {
      const extra = this.moreWords();
      if (!extra) throw new Error('Word source is empty');
      this.target.push(' ', ...Array.from(extra));
    }
  }
  edit(start, end, inserted) {
    const now = this.clock();
    if (this.tick(now)) return false;
    if (!Number.isInteger(start) || !Number.isInteger(end) || start < 0 || start > end || end > this.text.length) {
      throw new RangeError('Edit outside text');
    }
    const characters = Array.from(inserted);
    if (!characters.length && start === end) return false;
    if (characters.length && this.startedAt === null) this.startedAt = now;
    this.extend(this.text.length + characters.length);
    this.attempts += characters.length;
    this.correctAttempts += characters.reduce((n, ch, i) => n + Number(ch === this.target[start + i]), 0);
    this.text.splice(start, end - start, ...characters);
    this.extend(this.text.length);
    if (this.config.mode === 'survival') {
      let wordStart = null;
      for (let i = 0; i < Math.min(this.text.length, this.target.length); i++) {
        if (!/\s/u.test(this.target[i])) { if (wordStart === null) wordStart = i; continue; }
        if (wordStart !== null) {
          const key = `${wordStart}:${i}`;
          if (!this.awardedWords.has(key) && this.text.slice(wordStart, i + 1).every((ch, j) => ch === this.target[wordStart + j])) {
            this.awardedWords.add(key);
            this.bonusSeconds++;
          }
          wordStart = null;
        }
      }
    }
    if (this.config.mode === 'practice' && this.text.length >= this.target.length) this.endedAt = now;
    return true;
  }
  insert(text) { return this.edit(this.text.length, this.text.length, text); }
  backspace() { return this.text.length ? this.edit(this.text.length - 1, this.text.length, '') : (this.tick(), false); }
  score(now = this.clock()) {
    const elapsed = this.elapsed(now);
    const matched = this.text.reduce((n, ch, i) => n + Number(ch === this.target[i]), 0);
    return {
      mode: this.config.mode, category: this.config.category,
      duration: this.config.mode === 'sprint' ? this.config.duration : 0,
      elapsed, correctCharacters: matched, correctAttempts: this.correctAttempts,
      attempts: this.attempts, mistakes: this.attempts - this.correctAttempts,
      wpm: elapsed > 0 ? matched / 5 / (elapsed / 60) : 0,
      accuracy: this.attempts ? this.correctAttempts / this.attempts * 100 : 100,
      bonusSeconds: this.bonusSeconds,
    };
  }
}
