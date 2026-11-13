// tools/visual_probe.js —— 新增视觉元素的运行时断言 + 关键区域截图。
// 断言：KaTeX 红字=0、公式确实渲染、figure 撑满、表在可横滚容器里、页面不横向溢出。
// 截图：每页第一/第二张图、第一个公式、第一张表，供子代理视觉判读。
const path = require('path');
const fs = require('fs');
const puppeteer = require(process.env.PUPPETEER_CORE ||
  '/home/whu/workspace/servers/chatgpt-browser/node_modules/puppeteer-core');

const RUN = path.resolve(__dirname, '..');
const INDEX = path.join(RUN, 'site', 'index.html');
const OUT = path.join(RUN, 'shots', 'vis-raw');
fs.mkdirSync(OUT, { recursive: true });

const ROUTES = [
  ['paper', '#/papers/mopd'],
  ['algo', '#/algos/e48'],
  ['theory', '#/theory/t01'],
  ['direction', '#/map/code-capability-integration'],
  ['story', '#/story/story-four-masters'],
  ['book', '#/book/ch01'],
  ['appendix', '#/appendix'],
];

(async () => {
  const browser = await puppeteer.launch({
    executablePath: process.env.CHROME || '/snap/bin/chromium',
    headless: true, pipe: true,
    args: ['--headless=new', '--no-sandbox', '--disable-gpu', '--hide-scrollbars'],
    defaultViewport: { width: 1280, height: 1000 },
  });
  const page = await browser.newPage();
  const report = {};
  for (const [name, hash] of ROUTES) {
    await page.goto('file://' + INDEX + hash, { waitUntil: 'load', timeout: 60000 });
    await new Promise(r => setTimeout(r, 1200));
    const m = await page.evaluate(() => {
      const q = s => document.querySelector(s);
      const qa = s => [...document.querySelectorAll(s)];
      const figs = qa('figure.diagram').map(f => {
        const svg = f.querySelector('svg');
        const cap = f.querySelector('figcaption');
        const rw = svg ? svg.getBoundingClientRect().width : 0;
        const pw = f.getBoundingClientRect().width;
        return {
          cap: cap ? cap.textContent.trim().length : 0,
          svg: !!svg, fill: pw > 0 ? +(rw / pw).toFixed(3) : 0,
        };
      });
      // 数学公式 = 已渲染出 .katex，或仍残留 $$（渲染失败）；伪代码没有这两种特征。
      const formulas = qa('.formula').filter(el => el.querySelector('.katex') || el.textContent.includes('$$')).map(el => ({
        text: el.textContent.trim().slice(0, 60),
        katex: !!el.querySelector('.katex'),
        err: !!el.querySelector('.katex-error'),
        ox: getComputedStyle(el).overflowX,
      }));
      const tables = qa('.table-wrap').map(el => ({
        ox: getComputedStyle(el).overflowX,
        sw: el.scrollWidth, cw: el.clientWidth,
        hasHead: !!el.querySelector('thead, th'),
      }));
      return {
        title: (q('h1') || {}).textContent || '',
        figs, formulas, tables,
        katex: qa('.katex').length,
        katexErr: qa('.katex-error').length,
        bodyOverflow: document.documentElement.scrollWidth - window.innerWidth,
      };
    });
    report[name] = m;

    const shots = [];
    const figEls = await page.$$('figure.diagram');
    for (let i = 0; i < Math.min(2, figEls.length); i++) shots.push(['fig' + (i + 1), figEls[i]]);
    await page.evaluate(() => {
      const el = [...document.querySelectorAll('.formula')].find(x => x.querySelector('.katex') || x.textContent.includes('$$'));
      if (el) el.setAttribute('data-vis-math', '1');
    });
    const fEl = await page.$('[data-vis-math]');
    if (fEl) shots.push(['formula', fEl]);
    const tEl = await page.$('.table-wrap');
    if (tEl) shots.push(['table', tEl]);
    for (const [tag, el] of shots) {
      // 先滚到视口中央，避开 sticky 顶栏；再截元素本身。
      await page.evaluate(e => e.scrollIntoView({ block: 'center' }), el);
      await new Promise(r => setTimeout(r, 120));
      await el.screenshot({ path: path.join(OUT, name + '-' + tag + '.png') });
    }
  }
  await browser.close();

  let bad = 0;
  for (const [name, m] of Object.entries(report)) {
    const probs = [];
    if (m.katexErr) probs.push('KaTeX 红字 ' + m.katexErr);
    if (m.bodyOverflow > 1) probs.push('页面横向溢出 ' + m.bodyOverflow + 'px');
    m.figs.forEach((f, i) => {
      if (!f.svg) probs.push('图' + (i + 1) + ' 无 svg');
      if (f.cap < 8) probs.push('图' + (i + 1) + ' 图注 ' + f.cap + ' 字');
      if (f.fill < 0.95) probs.push('图' + (i + 1) + ' 未撑满 ' + f.fill);
    });
    m.formulas.forEach((f, i) => {
      if (!f.katex) probs.push('公式' + (i + 1) + ' 未渲染: ' + f.text);
      if (!/auto|scroll/.test(f.ox)) probs.push('公式' + (i + 1) + ' 无横向滚动');
    });
    m.tables.forEach((t, i) => {
      if (!t.hasHead) probs.push('表' + (i + 1) + ' 无表头');
      if (!/auto|scroll/.test(t.ox)) probs.push('表' + (i + 1) + ' 无横向滚动');
    });
    console.log((probs.length ? 'FAIL ' : 'PASS ') + name +
      ' · figs=' + m.figs.length + ' formulas=' + m.formulas.length +
      ' tables=' + m.tables.length + ' katex=' + m.katex +
      (probs.length ? '\n   ' + probs.join('\n   ') : ''));
    bad += probs.length;
  }
  console.log('\n问题合计 ' + bad + ' 条');
  process.exit(bad ? 1 : 0);
})().catch(e => { console.error('FAIL', e.message); process.exit(2); });
