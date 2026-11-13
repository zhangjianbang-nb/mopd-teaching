// tools/shoot.js —— 视觉验收截图（1440×900）。输出在 shots/。
const path = require('path');
const fs = require('fs');
const puppeteer = require('/home/whu/workspace/servers/chatgpt-browser/node_modules/puppeteer-core');
const RUN = path.resolve(__dirname, '..');
const OUT = path.join(RUN, 'shots');
fs.mkdirSync(OUT, { recursive: true });
const SHOTS = [
  { name: '01-home.png', hash: '' },
  { name: '02-paper.png', hash: '#/papers/mopd' },
  { name: '03-book.png', hash: '#/book/ch01' },
  { name: '04-story.png', hash: '#/story/story-four-masters' },
  { name: '05-exam.png', hash: '#/exam', reveal: true },
];
(async () => {
  const browser = await puppeteer.launch({
    executablePath: '/snap/bin/chromium', headless: true, pipe: true,
    args: ['--headless=new', '--no-sandbox', '--disable-gpu', '--hide-scrollbars',
           '--force-device-scale-factor=1'],
    defaultViewport: { width: 1440, height: 900 },
  });
  const page = await browser.newPage();
  const errs = [];
  page.on('pageerror', e => errs.push(e.message));
  for (const s of SHOTS) {
    await page.goto('file://' + path.join(RUN, 'site', 'index.html') + s.hash,
                    { waitUntil: 'load', timeout: 90000 });
    await new Promise(r => setTimeout(r, s.reveal ? 3000 : 1200));
    if (s.reveal) {
      await page.evaluate(() => {
        const b = document.querySelector('#view [data-reveal]');
        if (b) b.click();
        document.documentElement.style.scrollBehavior = 'auto';
        window.scrollTo(0, 0);
      });
      await new Promise(r => setTimeout(r, 600));
    }
    await page.screenshot({ path: path.join(OUT, s.name) });
    const t = await page.evaluate(() => (document.querySelector('#view') || {}).innerText.length || 0);
    console.log('shot ' + s.name + ' · view ' + t + ' 字');
  }
  if (errs.length) { console.error('JS 错误：' + errs.slice(0, 2).join(' | ')); process.exitCode = 1; }
  await browser.close();
})();
