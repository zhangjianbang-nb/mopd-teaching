// tools/mobile_probe.js —— 390px 窄屏断言：标题不被截断、首页 SVG 不被压成小字、页面不横向溢出。
// 用法：node tools/mobile_probe.js
const path = require('path');
const puppeteer = require(process.env.PUPPETEER_CORE ||
  '/home/whu/workspace/servers/chatgpt-browser/node_modules/puppeteer-core');

const RUN = path.resolve(__dirname, '..');
const CASES = [
  { hash: '', sel: '.hero h1', fig: true },
  { hash: '#/papers/mopd', sel: '.detail-head h1' },
  { hash: '#/book/ch24', sel: '.detail-head h1' },
  { hash: '#/story/story-four-masters', sel: '.detail-head h1' },
  { hash: '#/algos/e48', sel: '.detail-head h1' },
];

(async () => {
  const browser = await puppeteer.launch({
    executablePath: process.env.CHROME || '/snap/bin/chromium',
    headless: true, pipe: true,
    args: ['--headless=new', '--no-sandbox', '--disable-gpu', '--hide-scrollbars'],
    defaultViewport: { width: 390, height: 844, isMobile: true, deviceScaleFactor: 1 },
  });
  const page = await browser.newPage();
  let fail = 0;
  for (const c of CASES) {
    await page.goto('file://' + path.join(RUN, 'site', 'index.html') + c.hash,
                    { waitUntil: 'load', timeout: 90000 });
    await new Promise(r => setTimeout(r, 900));
    const r = await page.evaluate((sel) => {
      const h1 = document.querySelector(sel);
      const cs = h1 ? getComputedStyle(h1) : null;
      const fig = document.querySelector('figure.diagram');
      const svg = fig ? fig.querySelector('svg') : null;
      const sb = svg ? svg.getBoundingClientRect() : null;
      const fb = fig ? fig.getBoundingClientRect() : null;
      const txt = svg ? svg.querySelector('text') : null;
      return {
        h1: h1 ? h1.textContent.trim().slice(0, 40) : null,
        clamp: cs ? cs.webkitLineClamp : null,
        clipped: h1 ? (h1.scrollHeight > h1.clientHeight + 2) : null,
        svgW: sb ? Math.round(sb.width) : 0,
        svgH: sb ? Math.round(sb.height) : 0,
        figW: fb ? Math.round(fb.width) : 0,
        figScrollW: fig ? fig.scrollWidth : 0,
        fontPx: txt ? parseFloat(getComputedStyle(txt).fontSize) : 0,
        pageOverflow: document.documentElement.scrollWidth - 390,
      };
    }, c.sel);
    const okClamp = r.clamp === 'none' && r.clipped === false;
    const okPage = r.pageOverflow <= 1;
    const okSvg = !c.fig || (r.svgW >= 560 && r.figScrollW > r.figW + 20 && r.svgH >= 90);
    const okFont = !c.fig || r.fontPx >= 10;
    if (!okClamp || !okPage || !okSvg || !okFont) {
      fail++;
      console.log('FAIL ' + (c.hash || '#/home') + ' — clamp=' + r.clamp + ' clipped=' + r.clipped +
        ' svg=' + r.svgW + 'x' + r.svgH + ' font=' + r.fontPx + ' overflow=' + r.pageOverflow);
    } else {
      console.log('PASS ' + (c.hash || '#/home') + ' — h1 ' + r.h1 + ' · overflow ' + r.pageOverflow +
        (c.fig ? (' · svg ' + r.svgW + '×' + r.svgH + ' · font ' + r.fontPx + 'px') : ''));
    }
  }
  await browser.close();
  console.log(fail ? ('\nFAIL ' + fail + ' 项') : '\n全部 PASS');
  process.exit(fail ? 1 : 0);
})().catch(e => { console.error(e); process.exit(1); });
