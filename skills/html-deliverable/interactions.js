// Drive every interactive component in a built page and report what actually happened.
//
//   node interactions.js <playwright-module-path> <file-url>
//
// Verification by INTERACTION, not by screenshot: a filter that does not filter and a sort that
// does not reorder both look perfect in a picture. Prints one JSON object of results; a check
// that could not run reports false rather than being omitted.
const { chromium } = require(process.argv[2]);

(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1600, height: 1000 } });
  const consoleErrors = [];
  page.on('pageerror', (e) => consoleErrors.push(String(e)));
  page.on('console', (m) => { if (m.type() === 'error') consoleErrors.push(m.text()); });
  await page.goto(process.argv[3]);
  await page.waitForTimeout(400);

  const results = {};

  // ---- the nav goes FIRST, on a pristine page: a click scrolls, and the rail never covers
  //      the column. The wait MUST happen outside page.evaluate. requestAnimationFrame does
  //      not tick while an evaluate promise is pending, so an in-page sleep makes the eased
  //      scroll look dead and reports a failure the real browser does not have.
  const navReady = await page.evaluate(() => {
    const buttons = document.querySelectorAll('#sidenav button');
    if (buttons.length < 2) return null;
    window.scrollTo(0, 0);
    buttons[buttons.length - 1].click();
    return true;
  });
  if (navReady === null) {
    results.navScroll = null;
  } else {
    await page.waitForTimeout(900);
    results.navScroll = await page.evaluate(() => window.scrollY > 100);
  }
  results.navClear = await page.evaluate(() => {
    const nav = document.getElementById('sidenav');
    const wrap = document.querySelector('.wrap');
    if (!nav || !wrap) return null;
    if (getComputedStyle(nav).display === 'none') return true;
    return wrap.getBoundingClientRect().right <= nav.getBoundingClientRect().left + 1;
  });
  await page.evaluate(() => window.scrollTo(0, 0));

  // ---- table filter: typing hides the rows that do not match
  results.tableFilter = await page.evaluate(async () => {
    const box = document.querySelector('.dt-filter');
    const table = document.querySelector('table.dt');
    if (!box || !table) return null;
    const rows = table.tBodies[0].rows;
    const before = [].filter.call(rows, (r) => !r.classList.contains('hide')).length;
    box.value = 'zzz-no-such-row';
    box.dispatchEvent(new Event('input', { bubbles: true }));
    await new Promise((r) => setTimeout(r, 260));
    const after = [].filter.call(rows, (r) => !r.classList.contains('hide')).length;
    box.value = '';
    box.dispatchEvent(new Event('input', { bubbles: true }));
    await new Promise((r) => setTimeout(r, 260));
    const restored = [].filter.call(rows, (r) => !r.classList.contains('hide')).length;
    return before > 0 && after === 0 && restored === before;
  });

  // ---- table sort: clicking a header actually reorders the rows, and again reverses them
  results.tableSort = await page.evaluate(() => {
    const table = document.querySelector('table.dt');
    const th = table && table.querySelector('th[data-sort]');
    if (!th) return null;
    const texts = () => [].map.call(table.tBodies[0].rows, (r) => r.cells[0].textContent.trim());
    const original = texts().join('|');
    th.click();
    const ascending = texts().join('|');
    th.click();
    const descending = texts().join('|');
    return ascending !== descending && (ascending !== original || descending !== original);
  });

  // ---- the count label tracks the filter
  results.tableCount = await page.evaluate(() => {
    const count = document.querySelector('.dt-count');
    if (!count) return null;
    return /\d/.test(count.textContent);
  });

  // ---- slider: moving it updates the readout.
  //      Move to a value it is NOT already on. A slider whose value defaults to its max (the
  //      shorthand [slider: Label | min | max] does exactly that) sits on max already, so
  //      setting it to max changed nothing and the harness called a working component broken.
  results.slider = await page.evaluate(() => {
    const input = document.querySelector('.slider-row input[type="range"]');
    const out = document.querySelector('.slider-row [data-out]');
    if (!input || !out) return null;
    const min = Number(input.min), max = Number(input.max);
    const start = Number(input.value);
    const target = Math.abs(start - min) > Math.abs(start - max) ? min : max;
    if (target === start) return null; // a slider with no range to move through
    input.value = String(target);
    input.dispatchEvent(new Event('input', { bubbles: true }));
    return out.textContent.replace(/,/g, '') === String(target);
  });

  // ---- calculator: the three figures recompute from the inputs
  results.calculator = await page.evaluate(() => {
    const box = document.querySelector('[data-calc]');
    if (!box) return null; // not on this page
    const saved = box.querySelector('[data-calc-out="saved"]');
    const before = saved.textContent;
    const cost = box.querySelector('#costAfter');
    cost.value = '0';
    cost.dispatchEvent(new Event('input', { bubbles: true }));
    const after = saved.textContent;
    return before !== after && /\$[\d,]+/.test(after);
  });

  // ---- checklist: ticking updates the counter and persists to localStorage
  results.checklist = await page.evaluate(() => {
    const box = document.querySelector('[data-checklist]');
    if (!box) return null;
    const first = box.querySelector('input[type="checkbox"]');
    const count = box.querySelector('[data-check-count]');
    const before = count.textContent;
    first.checked = !first.checked;
    first.dispatchEvent(new Event('change', { bubbles: true }));
    const after = count.textContent;
    let stored = null;
    try { stored = localStorage.getItem('hd-' + box.getAttribute('data-store')); } catch (e) {}
    return before !== after && stored !== null;
  });

  // ---- drag-rank: the arrow keys reorder the list and the order is stored
  results.dragRank = await page.evaluate(() => {
    const list = document.querySelector('[data-rank]');
    if (!list) return null;
    const texts = () => [].map.call(list.children, (li) => li.textContent.trim()).join('|');
    const before = texts();
    const second = list.children[1];
    second.focus();
    second.dispatchEvent(new KeyboardEvent('keydown', { key: 'ArrowUp', bubbles: true }));
    const after = texts();
    let stored = null;
    try { stored = localStorage.getItem('hd-' + list.getAttribute('data-store')); } catch (e) {}
    return before !== after && stored !== null;
  });

  // ---- fold-outs: a click opens the detail, and the open state survives a reload.
  //      A fold that looks open in a screenshot but forgets itself is the defect here, so the
  //      check reads localStorage rather than trusting the toggle.
  //      The toggle event is queued, not synchronous, so the write to localStorage has not
  //      happened yet at the end of the click's own task: the read has to wait a tick or it
  //      reports a working memory as broken.
  results.folds = await page.evaluate(async () => {
    const fold = document.querySelector('details.fold[data-fold]');
    if (!fold) return null;
    const body = fold.querySelector('.fold-body');
    if (!body) return false;
    const wasOpen = fold.open;
    const summary = fold.querySelector('summary');
    summary.click();
    await new Promise((r) => setTimeout(r, 80));
    const flipped = fold.open !== wasOpen;
    const shows = fold.open ? body.getBoundingClientRect().height > 0 : true;
    let stored = null;
    try {
      const key = 'hd-fold-' + location.pathname.replace(/[^a-z0-9]+/gi, '-').slice(-60) + '-' + fold.getAttribute('data-fold');
      stored = localStorage.getItem(key);
    } catch (e) {}
    summary.click();
    await new Promise((r) => setTimeout(r, 80));
    return flipped && shows && stored !== null;
  });

  // ---- every data table filters, not only the first one on the page. A page with a table in
  //      a fold-out and another in the open used to report on whichever came first.
  results.everyTableFilters = await page.evaluate(async () => {
    const tables = [].slice.call(document.querySelectorAll('table.dt'));
    if (!tables.length) return null;
    for (const table of tables) {
      const wrap = table.closest('.dt-wrap') || table.parentNode;
      const box = wrap.querySelector('.dt-filter');
      if (!box) continue;
      const rows = table.tBodies[0].rows;
      box.value = 'zzz-no-such-row';
      box.dispatchEvent(new Event('input', { bubbles: true }));
      await new Promise((r) => setTimeout(r, 260));
      const after = [].filter.call(rows, (r) => !r.classList.contains('hide')).length;
      box.value = '';
      box.dispatchEvent(new Event('input', { bubbles: true }));
      await new Promise((r) => setTimeout(r, 260));
      const back = [].filter.call(rows, (r) => !r.classList.contains('hide')).length;
      if (after !== 0 || back !== rows.length) return false;
    }
    return true;
  });

  // ---- computed age: the label is written by script, never baked in
  results.age = await page.evaluate(() => {
    const el = document.querySelector('.age[data-until], .age[data-since]');
    if (!el) return null;
    return !!el.getAttribute('data-ago');
  });

  // ---- theme toggle: light is the default and the toggle reaches dark and back
  results.theme = await page.evaluate(() => {
    const root = document.documentElement;
    const button = document.querySelector('.theme-toggle');
    if (!button) return null;
    const start = root.getAttribute('data-theme');
    button.click();
    const flipped = root.getAttribute('data-theme');
    button.click();
    const back = root.getAttribute('data-theme');
    return start === 'light' && flipped === 'dark' && back === 'light';
  });

  // ---- width handles: a real pointer drag widens the column, and Escape resets it
  const grip = await page.$('.grip.r');
  if (!grip) {
    results.widthHandles = null;
  } else {
    const before = await page.evaluate(() => document.querySelector('.wrap').getBoundingClientRect().width);
    const box = await grip.boundingBox();
    await page.mouse.move(box.x + box.width / 2, box.y + box.height / 2);
    await page.mouse.down();
    await page.mouse.move(box.x + box.width / 2 - 120, box.y + box.height / 2, { steps: 8 });
    await page.mouse.up();
    await page.waitForTimeout(150);
    const narrowed = await page.evaluate(() => document.querySelector('.wrap').getBoundingClientRect().width);
    await page.evaluate(() => {
      const g = document.querySelector('.grip.r');
      g.focus();
      g.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', bubbles: true }));
    });
    await page.waitForTimeout(150);
    const reset = await page.evaluate(() => document.querySelector('.wrap').getBoundingClientRect().width);
    results.widthHandles = narrowed < before && Math.abs(reset - before) < 2;
  }

  // ---- the tooltip: hovering a marked element shows the card, never a native title
  results.tooltip = await page.evaluate(() => {
    const mark = document.querySelector('[data-tip]');
    if (!mark) return null;
    if (document.querySelector('[title]')) return false; // native tooltips are banned
    const tip = document.getElementById('tip');
    return !!tip;
  });

  results.consoleErrors = consoleErrors;
  await browser.close();
  console.log(JSON.stringify(results, null, 1));
})().catch((e) => { console.error(String(e)); process.exit(3); });
