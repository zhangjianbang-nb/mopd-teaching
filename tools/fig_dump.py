# -*- coding: utf-8 -*-
"""把首页 JS 模板里的五层 SVG 抽出来，做成可几何断言的测试页。

首页图在 PAGES.home 的字符串里，fig_dump 常规遍历 JSON 看不到它；
本脚本直接从 site/index.html 抽 SVG，保证「测试页图数 = 站点图数」。
用法：python3 -I tools/fig_dump.py [输出路径]
"""
import os
import re
import sys

RUN = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(RUN, "shots", "figtest.html")
os.makedirs(os.path.dirname(OUT), exist_ok=True)

html = open(os.path.join(RUN, "site", "index.html"), encoding="utf-8").read()
m = re.search(r'<svg viewBox="0 0 1000 170"[\s\S]*?</svg>', html)
if not m:
    sys.exit("未找到首页五层 SVG")

CSS = """
body{font-family:-apple-system,'PingFang SC','Noto Sans SC',sans-serif;background:#fbfaf7;margin:0;padding:20px}
figure.diagram{margin:20px 0;border:1px solid #d8d3c6;border-radius:10px;overflow:hidden;background:#fff}
figure.diagram svg{display:block;width:100%;height:auto}
figure.diagram figcaption{padding:8px 14px;font-size:12px;color:#68727d;border-top:1px solid #d8d3c6}
h2{font-size:14px;color:#163a5a;margin:28px 0 6px}
"""

page = ('<!doctype html><html lang="zh"><head><meta charset="utf-8"><style>' + CSS +
        '</style></head><body><h2>首页五层知识链（1 张）</h2><figure class="diagram" data-fig="home-layers">' +
        m.group(0) +
        '<figcaption>MOPD 的五层知识链：目标定形状，采样定落点，路由定来源，预算定强度，治理定可信度。</figcaption>'
        '</figure></body></html>')
open(OUT, "w", encoding="utf-8").write(page)
print("figtest:", OUT, "· 1 张")
