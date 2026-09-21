// DOM-level structural checks a regex cannot make honestly.
//
//   node domcheck.js <playwright-module-path> <file-url>
//
// A snippet printed inside <pre><code> contains the same attribute TEXT as the live element it
// documents, so a grep over the source reports duplicate ids that the browser never builds.
// Only the parsed document can answer this, which is why it is measured here.
const { chromium } = require(process.argv[2]);
(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1600, height: 1000 } });
  await page.goto(process.argv[3]);
  await page.waitForTimeout(300);
  const out = await page.evaluate(() => {
    const counts = {};
    document.querySelectorAll('[id]').forEach((el) => {
      counts[el.id] = (counts[el.id] || 0) + 1;
    });
    const duplicateIds = Object.keys(counts).filter((k) => counts[k] > 1);
    return {
      duplicateIds,
      sidenavs: document.querySelectorAll('#sidenav, nav[id=sidenav]').length,
      grips: document.querySelectorAll('.grip').length,
      themeToggles: document.querySelectorAll('.theme-toggle').length,
      nativeTitles: document.querySelectorAll('[title]').length,
      // NOT a <ul> inside a <p>: the parser closes the paragraph before the list, so that can
      // never exist in the DOM and a counter for it would be pinned at 0 forever. lint.py's
      // regex over the SOURCE is what catches that rule. What the DOM can answer is whether a
      // stylesheet or script is rendering as visible text, which is the failure an unclosed
      // <style> produces and which no string check can see.
      leakedSource: (document.body.innerText.match(/\{[^}]*(?:background|font-size|display)\s*:/g) || []).length,
      sections: document.querySelectorAll('section[id]').length,
      navButtons: document.querySelectorAll('#sidenav button').length,
    };
  });
  await browser.close();
  console.log(JSON.stringify(out, null, 1));
})().catch((e) => { console.error(String(e)); process.exit(3); });
