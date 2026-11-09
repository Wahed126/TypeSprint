/** Browser-local persistence. Storage failures are surfaced, never silently lost. */
export const KEY = 'typesprint.v1';
const defaults = () => ({ settings: { mode: 'sprint', category: 'english', duration: 30, fontSize: 22 }, sessions: [] });
export class Store {
  constructor(storage) {
    this.storage = storage;
    this.error = null;
    this.data = defaults();
    try {
      const raw = storage.getItem(KEY);
      if (raw !== null) {
        const parsed = JSON.parse(raw);
        if (!parsed || !Array.isArray(parsed.sessions) || !parsed.settings || typeof parsed.settings !== 'object') throw new Error('Invalid saved data');
        this.data = {
          settings: { ...this.data.settings, ...parsed.settings },
          sessions: parsed.sessions.filter(row => row && ['sprint', 'practice', 'survival'].includes(row.mode)
            && ['english', 'german', 'python', 'typescript'].includes(row.category)
            && ['wpm', 'accuracy', 'mistakes', 'elapsed', 'duration'].every(key => Number.isFinite(row[key]))
            && typeof row.createdAt === 'string'),
        };
      }
    } catch (error) { this.error = `Saved browser data could not be read: ${error.message}`; }
  }
  persist() {
    try { this.storage.setItem(KEY, JSON.stringify(this.data)); this.error = null; return true; }
    catch { this.error = 'Browser storage is unavailable or full. This result is kept only until you close the page.'; return false; }
  }
  settings(values) { Object.assign(this.data.settings, values); return this.persist(); }
  best(score) {
    const rows = this.data.sessions.filter(row => row.mode === score.mode && row.category === score.category && row.duration === score.duration);
    return rows.length ? Math.max(...rows.map(row => row.wpm)) : null;
  }
  save(score) {
    const previous = this.best(score);
    const newBest = previous === null || score.wpm > previous;
    this.data.sessions.unshift({ ...score, createdAt: new Date().toISOString() });
    return { newBest, persisted: this.persist() };
  }
  history(mode = '') { return this.data.sessions.filter(row => !mode || row.mode === mode); }
}
