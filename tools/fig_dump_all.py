# -*- coding: utf-8 -*-
"""把站内所有数据驱动图（论文/算法/理论/方向/故事/书章/附录）抽成一张测试页。

首页图由 fig_dump.py 单独处理；本脚本覆盖长文里的 210 张 figure。
用法：python3 -I tools/fig_dump_all.py [输出路径]
"""
import json
import os
import re
import sys

RUN = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(RUN, "shots", "figtest-all.html")
os.makedirs(os.path.dirname(OUT), exist_ok=True)
DATA = os.path.join(RUN, "site", "data")

CSS = """
body{font-family:-apple-system,'PingFang SC','Noto Sans SC',sans-serif;background:#fbfaf7;margin:0;padding:20px}
figure.diagram{margin:20px 0;border:1px solid #d8d3c6;border-radius:10px;overflow:hidden;background:#fff}
figure.diagram svg{display:block;width:100%;height:auto}
figure.diagram figcaption{padding:8px 14px;font-size:12px;color:#68727d;border-top:1px solid #d8d3c6}
h2{font-size:14px;color:#163a5a;margin:28px 0 6px}
"""


def load(name):
    with open(os.path.join(DATA, name + ".json"), encoding="utf-8") as f:
        return json.load(f)


def figs(html):
    return re.findall(r"<figure\b[\s\S]*?</figure>", html or "", re.I)


parts = []
for name, field in [("papers", "long_html"), ("algorithms", "long_html"),
                    ("theory", "long_html"), ("directions", "long_html"),
                    ("stories", "long_html")]:
    for item in load(name):
        for i, f in enumerate(figs(item.get(field))):
            parts.append((name + "/" + item["id"] + "#" + str(i), f))
for sec in load("book").get("sections", []):
    for i, f in enumerate(figs(sec.get("html"))):
        parts.append(("book/" + sec["id"] + "#" + str(i), f))
for i, f in enumerate(figs(load("appendix").get("long_html"))):
    parts.append(("appendix#" + str(i), f))

body = []
for key, f in parts:
    body.append('<h2>' + key + '</h2>' + f)
page = ('<!doctype html><html lang="zh"><head><meta charset="utf-8"><style>' + CSS +
        '</style></head><body>' + "".join(body) + '</body></html>')
open(OUT, "w", encoding="utf-8").write(page)
print("figtest-all:", OUT, "·", len(parts), "张")
