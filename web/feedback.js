/** Coaching choices, not skill rankings. Shares catalog and fixture cases with Python. */
export function roundFeedback(score, catalog) {
  const rules = catalog.thresholds;
  const code = ['python', 'typescript'].includes(score.category);
  const steady = rules[code ? 'code_steady_wpm' : 'steady_wpm'];
  const fast = rules[code ? 'code_fast_wpm' : 'fast_wpm'];
  const pace = score.wpm >= fast ? 'fast' : score.wpm >= steady ? 'steady' : 'calm';
  let key;
  if (score.attempts === 0 || score.correctCharacters === 0) key = 'no_matches';
  else if (score.elapsed < rules.minimum_elapsed) key = 'quick_sample';
  else if (score.attempts < rules.minimum_attempts) key = 'small_sample';
  else if (score.accuracy < rules.low_accuracy) key = 'accuracy_reset';
  else if (score.accuracy < rules.target_accuracy) key = pace === 'fast' ? 'fast_errors' : 'steady_errors';
  else if (score.mistakes === 0 && score.accuracy >= rules.high_accuracy) key = `clean_${pace}`;
  else if (score.accuracy >= rules.high_accuracy) key = `accurate_${pace}`;
  else key = pace === 'fast' ? 'polish_fast' : 'polish_calm';

  let tip = null;
  if (!['no_matches', 'quick_sample', 'small_sample'].includes(key)) {
    if (score.accuracy < rules.target_accuracy && score.mistakes >= rules.minimum_mistakes
        && score.mistakes * 60 / score.elapsed >= rules.mistakes_per_minute) tip = 'mistake_load';
    else if (code) tip = 'code';
    else if (score.mode === 'survival' && score.elapsed >= rules.long_elapsed) tip = 'survival_long';
    else if (score.elapsed >= rules.long_elapsed) tip = score.accuracy >= rules.target_accuracy ? 'long_focus' : 'long_practice';
    else if (score.mode === 'sprint' && score.accuracy >= rules.high_accuracy && [15, 30].includes(score.duration)) {
      tip = score.duration === 15 ? 'sprint30' : 'sprint60';
    } else tip = ['practice', 'survival'].includes(score.mode) ? score.mode : 'repeat';
  }
  const profile = catalog.profiles[key];
  const extra = tip ? ' ' + catalog.tips[tip]
    .replaceAll('{mistakes}', String(score.mistakes)).replaceAll('{elapsed}', score.elapsed.toFixed(1)) : '';
  return { key, title: profile.title, message: profile.message + extra, tip };
}
