import { test, expect } from '@playwright/test';
const errors = new WeakMap();
test.beforeEach(async ({ page }) => { errors.set(page, []); page.on('pageerror', error => errors.get(page).push(error.message)); });
test.afterEach(async ({ page }) => { expect(errors.get(page)).toEqual([]); });
async function load(page) {
  await page.clock.install();
  await page.goto('./');
  await expect(page.locator('#typing')).toBeFocused();
  await expect(page.locator('#target .char')).not.toHaveCount(0);
}
async function targetText(page) { return page.locator('#target').textContent(); }
async function completeSprint(page) {
  await page.locator('#duration').selectOption('15');
  await page.locator('#typing').focus();
  await page.keyboard.type((await targetText(page)).slice(0, 12));
  await page.clock.runFor(15050);
  await expect(page.locator('#results')).toBeVisible();
}
test('first keystroke, error underline, correction and restart', async ({ page }) => {
  await load(page); await page.screenshot({ path: 'test-results/preview.png', fullPage: true }); await page.clock.runFor(5000);
  await expect(page.locator('#stat-clock')).toHaveText('30.0s');
  await page.keyboard.type('x');
  await expect(page.locator('#target .error')).toHaveCount(1);
  await page.keyboard.press('Backspace'); await page.keyboard.type((await targetText(page))[0]);
  await expect(page.locator('#stat-mistakes')).toHaveText('1');
  await expect(page.locator('#target .error')).toHaveCount(0);
  await expect(page.locator('#stat-accuracy')).toHaveText('50%');
  await page.keyboard.press('Control+r');
  await expect(page.locator('#typing')).toHaveValue('');
  await expect(page.locator('#typing')).toBeFocused();
  await expect(page.locator('#stat-mistakes')).toHaveText('0');
});
test('full timed round, Enter on Play again, persistence and mode filter', async ({ page }) => {
  await load(page); await completeSprint(page);
  await expect(page.locator('#again')).toBeFocused();
  await expect(page.locator('#result-elapsed')).toHaveText('15.0s');
  await expect(page.locator('#personal-best')).toHaveText('New personal best!');
  await page.keyboard.press('Enter');
  await expect(page.locator('#typing')).toBeFocused();
  await page.reload(); await expect(page.locator('#typing')).toBeFocused();
  await page.getByRole('button', { name: 'History', exact: true }).click();
  await expect(page.locator('#history-body tr')).toHaveCount(1);
  await page.locator('#history-filter').selectOption('survival');
  await expect(page.locator('#history-empty')).toBeVisible();
  await page.locator('#history-filter').selectOption('sprint');
  await expect(page.locator('#history-body tr')).toHaveCount(1);
});
test('native selection replacing an identical character is still an attempt', async ({ page }) => {
  await load(page); const char = (await targetText(page))[0];
  await page.keyboard.type(char);
  await page.locator('#typing').evaluate(el => el.setSelectionRange(0, 1));
  await page.keyboard.type(char); await page.clock.runFor(30050);
  await expect(page.locator('#result-detail')).toContainText('2 correct / 2 attempts');
});
test('Survival never re-awards a word position', async ({ page }) => {
  await load(page); await page.locator('#mode').selectOption('survival');
  const word = (await targetText(page)).split(' ')[0] + ' ';
  await page.locator('#typing').focus(); await page.keyboard.type(word);
  await expect(page.locator('#progress')).toContainText('+1s');
  await page.keyboard.press('Backspace'); await page.keyboard.type(' ');
  await expect(page.locator('#progress')).toContainText('+1s');
  await page.clock.runFor(31050); await expect(page.locator('#results')).toBeVisible();
  await expect(page.locator('#result-elapsed')).toHaveText('31.0s');
});
test('German composition commits one Unicode character, not preedit attempts', async ({ page }) => {
  await load(page); await page.locator('#category').selectOption('german');
  await page.locator('#typing').evaluate(el => {
    el.dispatchEvent(new CompositionEvent('compositionstart', { bubbles: true }));
    el.value = 'a'; el.dispatchEvent(new InputEvent('input', { inputType: 'insertCompositionText', data: 'a', isComposing: true, bubbles: true }));
    el.value = 'ä'; el.dispatchEvent(new CompositionEvent('compositionend', { data: 'ä', bubbles: true }));
    el.dispatchEvent(new InputEvent('input', { inputType: 'insertCompositionText', data: 'ä', bubbles: true }));
  });
  await page.clock.runFor(30050);
  await expect(page.locator('#result-detail')).toContainText('/ 1 attempts');
});
test('code practice preserves newlines and indentation; settings survive reload', async ({ page }) => {
  await load(page); await page.locator('#mode').selectOption('practice'); await page.locator('#category').selectOption('python');
  const text = await targetText(page); expect(text).toContain('\n    ');
  await page.locator('#typing').focus(); await page.keyboard.insertText(text.slice(0, 5));
  await page.clock.runFor(2000); await page.keyboard.insertText(text.slice(5));
  await expect(page.locator('#results')).toBeVisible(); await expect(page.locator('#result-accuracy')).toHaveText('100.0%');
  await page.getByRole('button', { name: 'Settings', exact: true }).click();
  await page.locator('#font-size').fill('36'); await page.locator('#font-size').dispatchEvent('input');
  await page.reload(); await page.getByRole('button', { name: 'Settings', exact: true }).click();
  await expect(page.locator('#font-size')).toHaveValue('36');
});
test('stats keep text coordinates fixed; current line visible at small and large sizes', async ({ page }) => {
  await load(page);
  for (const viewport of [{ width: 560, height: 640 }, { width: 1280, height: 950 }]) {
    await page.setViewportSize(viewport); await page.emulateMedia({ colorScheme: viewport.width < 600 ? 'light' : 'dark' });
    await page.locator('#mode').selectOption('practice'); await page.locator('#category').selectOption('python');
    await page.evaluate(() => document.documentElement.style.setProperty('--font-size', '36px'));
    const before = await page.locator('#target').boundingBox();
    await page.locator('#typing').focus(); await page.keyboard.insertText((await targetText(page)).slice(0, -2)); await page.clock.runFor(2000);
    const after = await page.locator('#target').boundingBox(); expect(after.y).toBe(before.y); expect(after.height).toBe(before.height);
    const current = await page.locator('#target .current').boundingBox();
    expect(current.y).toBeGreaterThanOrEqual(after.y); expect(current.y + current.height).toBeLessThanOrEqual(after.y + after.height + 1);
    await page.screenshot({ path: `test-results/play-${viewport.width}.png`, fullPage: true });
    await page.keyboard.press('Control+r');
  }
});
test('Tab moves focus instead of inserting a tab', async ({ page }) => {
  await load(page); await page.keyboard.press('Tab'); await expect(page.locator('#typing')).not.toBeFocused(); await expect(page.locator('#typing')).toHaveValue('');
});
test('built app works offline after its first complete visit', async ({ page, context }) => {
  await page.goto('./'); await expect(page.locator('#typing')).toBeFocused();
  await page.evaluate(async () => { await navigator.serviceWorker.ready; if (!navigator.serviceWorker.controller) await new Promise(resolve => navigator.serviceWorker.addEventListener('controllerchange', resolve, { once: true })); });
  await page.goto('./web/'); await expect(page).toHaveURL('http://127.0.0.1:4173/TypeSprint/');
  await context.setOffline(true); await page.goto('http://127.0.0.1:4173/TypeSprint/web/'); await expect(page).toHaveURL('http://127.0.0.1:4173/TypeSprint/'); await expect(page.locator('#typing')).toBeFocused();
  await page.locator('#mode').selectOption('practice'); await page.locator('#category').selectOption('typescript'); await expect(page.locator('#target')).toContainText(' ');
});

test('repository-root Pages publishing opens a playable game and works offline', async ({ page, context }) => {
  await page.clock.install();
  await page.goto('http://127.0.0.1:4174/TypeSprint/');
  await expect(page).toHaveURL('http://127.0.0.1:4174/TypeSprint/web/');
  await expect(page.locator('#typing')).toBeFocused();
  await page.locator('#mode').selectOption('practice');
  const text = await targetText(page);
  await page.locator('#typing').focus();
  await page.keyboard.insertText(text.slice(0, 5));
  await page.clock.runFor(2000);
  await page.keyboard.insertText(text.slice(5));
  await expect(page.locator('#result-accuracy')).toHaveText('100.0%');
  await expect(page.locator('#again')).toBeFocused();
  await page.evaluate(async () => {
    await navigator.serviceWorker.ready;
    if (!navigator.serviceWorker.controller) await new Promise(resolve => navigator.serviceWorker.addEventListener('controllerchange', resolve, { once: true }));
  });
  await context.setOffline(true);
  await page.reload();
  await expect(page.locator('#typing')).toBeFocused();
  await page.getByRole('button', { name: 'History', exact: true }).click();
  await expect(page.locator('#history-body tr')).toHaveCount(1);
});
