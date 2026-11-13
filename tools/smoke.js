// tools/smoke.js —— 全页冒烟：路由、渲染、交互、无外链、无 JS 错误。
// 用法：node tools/smoke.js
const path = require('path');
const fs = require('fs');
const puppeteer = require(process.env.PUPPETEER_CORE ||
  '/home/whu/workspace/servers/chatgpt-browser/node_modules/puppeteer-core');

const RUN = path.resolve(__dirname, '..');
const OUT = path.join(RUN, 'shots');
fs.mkdirSync(OUT, { recursive: true });

const PAGES = [
  { hash: '', name: 'home', min: 800 },
  { hash: '#/map', name: 'map', min: 600 },
  { hash: '#/map/code-capability-integration', name: 'map-detail', min: 800 },
  { hash: '#/algos', name: 'algos', min: 600 },
  { hash: '#/algos/e48', name: 'algo-detail', min: 1200 },
  { hash: '#/papers', name: 'papers', min: 600 },
  { hash: '#/papers/mopd', name: 'paper-detail', min: 1500 },
  { hash: '#/evolution', name: 'evolution', min: 500 },
  { hash: '#/summary', name: 'summary', min: 600 },
  { hash: '#/book', name: 'book', min: 400 },
  { hash: '#/book/ch01', name: 'book-ch01', min: 1500 },
  { hash: '#/book/ch24', name: 'book-ch24', min: 1500 },
  { hash: '#/story', name: 'story', min: 400 },
  { hash: '#/story/story-four-masters', name: 'story-detail', min: 1200 },
  { hash: '#/theory', name: 'theory', min: 600 },
  { hash: '#/theory/t01', name: 'theory-detail', min: 1200 },
  { hash: '#/deepdive', name: 'deepdive', min: 400 },
  { hash: '#/deepdive/mopd', name: 'deepdive-detail', min: 1200 },
  { hash: '#/appendix', name: 'appendix', min: 2000 },
  { hash: '#/exam', name: 'exam', min: 800, wait: 5000 },
];

(async () => {
  const browser = await puppeteer.launch({
    executablePath: process.env.CHROME || '/snap/bin/chromium',
    headless: true, pipe: true,
    args: ['--headless=new', '--no-sandbox', '--disable-gpu',
           '--hide-scrollbars', '--force-device-scale-factor=1'],
    defaultViewport: { width: 1440, height: 900 },
  });
  const page = await browser.newPage();
  const errs = [];
  const externals = [];
  page.on('pageerror', e => errs.push('pageerror: ' + e.message));
  page.on('console', m => { if (m.type() === 'error') errs.push('console: ' + m.text()); });
  page.on('request', r => { if (/^https?:/.test(r.url())) externals.push(r.url()); });

  let fails = 0;
  for (const p of PAGES) {
    errs.length = 0;
    await page.goto('file://' + path.join(RUN, 'site', 'index.html') + p.hash,
                    { waitUntil: 'load', timeout: 90000 });
    await new Promise(r => setTimeout(r, p.wait || 900));
    const info = await page.evaluate(() => {
      const v = document.getElementById('view');
      return {
        text: v ? v.innerText : '',
        missing: v ? /未找到该页面|数据缺失|尚未录入/.test(v.innerText) : true,
        svg: !!document.querySelector('#view figure.diagram svg'),
        h1: (document.querySelector('#view h1') || {}).innerText || '',
      };
    });
    const bad = [];
    if (info.missing) bad.push('页面缺数据');
    if (info.text.length < p.min) bad.push('正文 ' + info.text.length + ' < ' + p.min);
    if (errs.length) bad.push(errs.slice(0, 2).join(' | '));
    if (bad.length) { fails++; console.log('FAIL ' + p.name + ' — ' + bad.join('; ')); }
    else console.log('PASS ' + p.name + ' — ' + info.text.length + ' 字 · ' + info.h1.slice(0, 30));
    if (p.name === 'home') {
      if (!info.svg) { fails++; console.log('FAIL home — 五层 SVG 未渲染'); }
      const dom = await page.evaluate(() => '<!doctype html>' + document.documentElement.outerHTML);
      fs.writeFileSync(path.join(OUT, 'home-dom.html'),
        dom.replace('<head>', '<head><base href="file://' + path.join(RUN, 'site') + '/">'));
    }
    if (p.name === 'book') {
      const n = await page.evaluate(() =>
        Array.from(document.querySelectorAll('#view a[href^="#/book/"]')).length);
      if (n < 24) { fails++; console.log('FAIL book — 章节链接 ' + n + ' < 24'); }
      else console.log('  章节链接 ' + n);
    }
    if (p.name === 'exam') {
      const r = await page.evaluate(() => {
        const cards = document.querySelectorAll('#view .qcard');
        const btn = document.querySelector('#view [data-reveal]');
        if (btn) btn.click();
        const ans = btn ? btn.closest('.qcard').querySelector('.answer') : null;
        return { cards: cards.length, revealed: ans && !ans.hidden,
                 answerLen: ans ? ans.innerText.length : 0 };
      });
      await new Promise(r => setTimeout(r, 500));
      if (r.cards < 1000) { fails++; console.log('FAIL exam — 题卡 ' + r.cards); }
      if (!r.revealed || r.answerLen < 100) { fails++; console.log('FAIL exam — 答案未展开'); }
      console.log('  题卡 ' + r.cards + ' · 答案 ' + r.answerLen + ' 字');
    }
  }
  if (externals.length) {
    fails++;
    console.log('FAIL 外链请求 ' + externals.length + ' 条：' + externals.slice(0, 3).join(' '));
  } else {
    console.log('PASS 无 http(s) 外链请求');
  }
  await browser.close();
  console.log(fails ? ('\nFAIL ' + fails + ' 项') : '\n全部 PASS');
  process.exit(fails ? 1 : 0);
})().catch(e => { console.error(e); process.exit(1); });
