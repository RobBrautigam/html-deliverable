// Drive the line chart component and report what the browser actually drew.
//
//   node chartcheck.js <playwright-module-path> <file-url>
//
// A chart is the component a screenshot lies about most: a path can be drawn from the wrong
// numbers, a band can be invisible, and a crosshair can read one series while looking like it
// reads all of them. Everything below is measured from the rendered document. Prints one JSON
// object; a check that could not run reports false rather than being omitted.
const { chromium } = require(process.argv[2]);

(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1500, height: 1000 } });
  const consoleErrors = [];
  page.on('pageerror', (e) => consoleErrors.push(String(e)));
  page.on('console', (m) => { if (m.type() === 'error') consoleErrors.push(m.text()); });
  await page.goto(process.argv[3]);
  await page.waitForTimeout(500);

  const results = { consoleErrors };

  // the figure has to exist before anything else means anything
  const present = await page.evaluate(() => !!document.querySelector('figure.chart[data-chart] svg'));
  results.present = present;
  if (!present) { console.log(JSON.stringify(results)); await browser.close(); return; }

  // ---- 1. every value comes from the JSON block, and the block is the only source
  results.dataInJsonBlock = await page.evaluate(() => {
    const fig = document.querySelector('figure.chart[data-chart]');
    const node = fig.querySelector('script[type="application/json"].chart-data');
    if (!node) return false;
    try { const cfg = JSON.parse(node.textContent); return !!(cfg.series && cfg.series.length >= 2); }
    catch (e) { return false; }
  });

  // ---- 2. drawn in REAL PIXELS: the svg's own width matches its layout box, so the axis type
  //        is 11px on screen rather than a scaled viewBox shrinking it to nothing at 390
  results.realPixels = await page.evaluate(() => {
    const svg = document.querySelector('figure.chart[data-chart] svg');
    const box = svg.getBoundingClientRect();
    const attr = Number(svg.getAttribute('width') || 0);
    if (!attr || Math.abs(attr - box.width) > 2) return false;
    const label = svg.querySelector('text.cx');
    if (!label) return false;
    return Math.abs(parseFloat(getComputedStyle(label).fontSize) - 11) < 2;
  });

  // ---- 3. it REDRAWS on resize rather than scaling: the new width is a new drawing, and the
  //        axis type is still 11px afterwards. Direction is not assumed - the reading column can
  //        get wider as the window narrows, because the nav's rail stops being reserved.
  const before = await page.evaluate(() => Number(document.querySelector('figure.chart[data-chart] svg').getAttribute('width')));
  await page.setViewportSize({ width: 760, height: 1000 });
  await page.waitForTimeout(500);
  const after = await page.evaluate(() => {
    const svg = document.querySelector('figure.chart[data-chart] svg');
    const label = svg.querySelector('text.cx');
    return {
      width: Number(svg.getAttribute('width')),
      box: Math.round(svg.getBoundingClientRect().width),
      type: label ? Math.round(parseFloat(getComputedStyle(label).fontSize)) : 0,
    };
  });
  results.redrawsOnResize =
    before > 0 && after.width > 0 && after.width !== before &&
    Math.abs(after.width - after.box) <= 2 && after.type === 11;
  results.widthBefore = before;
  results.widthAfter = after.width;
  await page.setViewportSize({ width: 1500, height: 1000 });
  await page.waitForTimeout(500);

  // ---- 4. the band between the best case and the worst case is a real filled shape
  results.band = await page.evaluate(() => {
    const band = document.querySelector('figure.chart[data-chart] .cband');
    if (!band) return false;
    const box = band.getBBox();
    return box.width > 20 && box.height > 2;
  });

  // ---- 5. the crosshair reads EVERY line, not one of them. Scroll the PLOT into view, not its
  //        section: on a short viewport the plot is still below the fold and the pointer lands
  //        on whatever is actually on screen.
  const plotBox = await page.evaluate(() => {
    const plot = document.querySelector('figure.chart[data-chart] .chart-plot');
    plot.scrollIntoView({ block: 'center' });
    const r = plot.getBoundingClientRect();
    return { x: r.left + r.width * 0.9, y: r.top + r.height * 0.5 };
  });
  await page.mouse.move(plotBox.x, plotBox.y);
  await page.waitForTimeout(250);
  // The readout must list EVERY series that has a value at the hovered date, and there must be
  // more than one, or "reads every line" is indistinguishable from "reads the first line".
  results.crosshairReadsEveryLine = await page.evaluate(() => {
    const fig = document.querySelector('figure.chart[data-chart]');
    const read = fig.querySelector('.chart-read');
    if (!read.classList.contains('on')) return false;
    const cfg = JSON.parse(fig.querySelector('.chart-data').textContent);
    const heading = read.querySelector('b');
    if (!heading) return false;
    const when = Date.parse(heading.textContent + ' UTC');
    if (isNaN(when)) return false;
    const live = cfg.series.filter((s) => {
      const days = s.points.map((p) => Date.parse(p[0] + 'T00:00:00Z'));
      return when >= Math.min.apply(null, days) && when <= Math.max.apply(null, days);
    });
    if (live.length < 2) return false;
    const rows = read.querySelectorAll('.rr');
    if (rows.length !== live.length) return false;
    const text = read.textContent;
    return live.every((s) => text.indexOf(s.name) !== -1);
  });
  results.crosshairKnob = await page.evaluate(
    () => document.querySelectorAll('figure.chart[data-chart] .cknob').length > 0
  );

  // ---- 6. both themes: the ink series must change color when the theme does, because its color
  //        comes from a token and never from a hex baked into the path
  const lightColor = await page.evaluate(() => {
    const line = document.querySelector('figure.chart[data-chart] .cline');
    return getComputedStyle(line).stroke || getComputedStyle(line.parentElement).color;
  });
  await page.evaluate(() => document.documentElement.setAttribute('data-theme', 'dark'));
  await page.waitForTimeout(250);
  const darkColor = await page.evaluate(() => {
    const line = document.querySelector('figure.chart[data-chart] .cline');
    return getComputedStyle(line).stroke || getComputedStyle(line.parentElement).color;
  });
  results.followsTheTheme = !!lightColor && !!darkColor && lightColor !== darkColor;
  results.lightColor = lightColor;
  results.darkColor = darkColor;
  await page.evaluate(() => document.documentElement.setAttribute('data-theme', 'light'));

  // ---- 7. the legend swatch wears its series color: a color set on the ROW outranks the tone
  //        class and rendered every swatch the same shade of ink
  results.legendSwatchColors = await page.evaluate(() => {
    const keys = [].slice.call(document.querySelectorAll('figure.chart[data-chart] .chart-legend .ck i'));
    if (keys.length < 2) return false;
    const colors = keys.map((k) => getComputedStyle(k).borderTopColor);
    return new Set(colors).size > 1;
  });

  console.log(JSON.stringify(results));
  await browser.close();
})().catch((e) => { console.error(String(e)); process.exit(3); });
