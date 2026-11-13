// scripts/fig_probe.js —— 图表几何断言：三条判据，任一不过即 exit 1。
//   1) 越界：每段 <text> 的 bbox 必须落在 viewBox 内（±1px）
//   2) 重叠：任意两段文字的 bbox 交集 > 2×2px 即报错
//   3) 撑满：figure.diagram svg 的渲染宽度必须 ≈ 容器宽度（抓 CSS 没生效，SVG 默认 300×150）
//
// 用法：node fig_probe.js <figtest.html>
// 环境变量：CHROME（默认 /snap/bin/chromium）、PUPPETEER_CORE（puppeteer-core 目录）
const path = require('path');
const puppeteer = require(process.env.PUPPETEER_CORE ||
  '/home/whu/workspace/servers/chatgpt-browser/node_modules/puppeteer-core');

(async () => {
  const file = path.resolve(process.argv[2]);
  const browser = await puppeteer.launch({
    executablePath: process.env.CHROME || '/snap/bin/chromium',
    headless: true,
    pipe: true,                       // snap chromium 只能走 pipe，不能走 websocket
    args: ['--headless=new', '--no-sandbox', '--disable-gpu',
           '--hide-scrollbars', '--force-device-scale-factor=1'],
    defaultViewport: { width: 900, height: 900 },
  });
  const page = await browser.newPage();
  await page.goto('file://' + file, { waitUntil: 'load', timeout: 60000 });
  await new Promise(r => setTimeout(r, 800));   // 等字体加载完，getBBox 才准
  const res = await page.evaluate(() => {
    const out = [];
    document.querySelectorAll('figure.diagram').forEach((fig, si) => {
      const svg = fig.querySelector('svg');
      if (!svg) { out.push({ id: fig.getAttribute('data-fig') || ('#' + si), bad: ['无 svg'], nbad: 1, n: 0, W: 0, H: 0 }); return; }
      const vb = svg.viewBox.baseVal;
      const W = vb.width, H = vb.height;
      const id = fig.getAttribute('data-fig') || ('#' + si);
      const texts = [...svg.querySelectorAll('text')].map(t => {
        const b = t.getBBox();
        return { s: t.textContent.slice(0, 40), x: b.x, y: b.y, w: b.width, h: b.height };
      });
      const bad = [];
      texts.forEach(t => {
        if (t.x < -1 || t.y < -1 || t.x + t.w > W + 1 || t.y + t.h > H + 1)
          bad.push('越界: ' + t.s + ' [' + t.x.toFixed(0) + ',' + t.y.toFixed(0) + ' ' +
                   t.w.toFixed(0) + 'x' + t.h.toFixed(0) + ']');
      });
      for (let i = 0; i < texts.length; i++)
        for (let j = i + 1; j < texts.length; j++) {
          const a = texts[i], b = texts[j];
          const ox = Math.min(a.x + a.w, b.x + b.w) - Math.max(a.x, b.x);
          const oy = Math.min(a.y + a.h, b.y + b.h) - Math.max(a.y, b.y);
          if (ox > 2 && oy > 2)
            bad.push('重叠: 「' + a.s + '」×「' + b.s + '」 ' + ox.toFixed(0) + 'x' + oy.toFixed(0));
        }
      // 撑满：svg 渲染宽度 vs 容器宽度
      const rw = svg.getBoundingClientRect().width;
      const pw = fig.getBoundingClientRect().width;
      if (pw > 0 && rw < pw - 40)
        bad.push('未撑满: svg ' + rw.toFixed(0) + 'px / 容器 ' + pw.toFixed(0) + 'px');
      out.push({ id, W, H, n: texts.length, bad: bad.slice(0, 6), nbad: bad.length });
    });
    return out;
  });
  await browser.close();
  let total = 0, badFigs = 0;
  for (const r of res) {
    total += r.nbad;
    if (r.nbad) {
      badFigs++;
      console.log(`[${r.id}] ${r.W}x${r.H} texts=${r.n} 问题=${r.nbad}`);
      r.bad.forEach(b => console.log('   ' + b));
    }
  }
  console.log(`\n共 ${res.length} 张图，${badFigs} 张有问题，问题合计 ${total} 条`);
  process.exit(total ? 1 : 0);
})().catch(e => { console.error('FAIL', e.message); process.exit(2); });
