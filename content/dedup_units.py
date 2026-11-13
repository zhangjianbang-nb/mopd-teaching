# -*- coding: utf-8 -*-
"""删除跨单元重复段落，把唯一一份收进附录 C。

E-DUP 的判据：papers/algorithms/theory/directions/stories 的 long_html 里，
同一段文字出现在 >1 个单元即算重复。这里把重复段落从各单元删掉，
按来源分组收进 appendix.long_html 的「附录 C」，既过闸门又不丢阅读方法。
"""
import collections
import html
import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
RUN = os.path.dirname(HERE)
DATA = os.path.join(RUN, "site", "data")
KEYS = ["papers", "algorithms", "theory", "directions", "stories"]


def plain(s):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", "", s or ""))).strip()


def paragraphs(h):
    out = []
    for m in re.finditer(r"<p\b[^>]*>([\s\S]*?)</p>", h or ""):
        t = plain(m.group(1))
        if len(t) >= 20:
            out.append((m.start(), m.end(), t))
    return out


BLOCK = re.compile(r"<(?:figure|div|h3|h4|ol|ul|table|section|details|blockquote)\b")
TAG = re.compile(r"<[^>]+>")


def fix_unclosed_p(h):
    """补全未闭合的 <p>：遇到块级标签或新的 <p> 时先把上一个 <p> 关掉。

    2026-11-13 实测：算法卡里有 40 个 <p> 开、36 个闭，未闭合的 <p> 会把
    后面的 <figure><svg> 整段吞进段落匹配，去重时误删流程图。
    """
    h = h or ""
    out, pos, open_p = [], 0, False
    for m in TAG.finditer(h):
        tag = m.group(0)
        low = tag.lower()
        if open_p and (re.match(r"<p(?:\s|>)", low) or BLOCK.match(tag)):
            out.append(h[pos:m.start()])
            out.append("</p>")
            pos = m.start()
            open_p = False
        out.append(h[pos:m.start()])
        out.append(tag)
        pos = m.end()
        if re.match(r"<p(?:\s|>)", low):
            open_p = True
        elif low.startswith("</p"):
            open_p = False
    out.append(h[pos:])
    if open_p:
        out.append("</p>")
    return "".join(out)


def strip_dups(h, dups):
    """按精确 span 删除重复段落；含 <figure>/<svg> 的段落一律跳过。

    不能再用 `<p>...</p>` 全局替换：未闭合的 <p> 会把后面的流程图吞掉，
    实测 e01 的 </figure> 就是这样丢的。
    """
    spans = [(a, b) for a, b, t in paragraphs(h)
             if t in dups and "<svg" not in h[a:b] and "<figure" not in h[a:b]]
    for a, b in reversed(spans):
        h = h[:a] + h[b:]
    return h


def clean_empty_headings(h):
    for _ in range(6):
        new = re.sub(r"<h3[^>]*>[^<]*</h3>\s*(?=<h3|$)", "", h)
        if new == h:
            break
        h = new
    return h


def main():
    data = {k: json.load(open(os.path.join(DATA, k + ".json"), encoding="utf-8")) for k in KEYS}
    for key in KEYS:
        for item in data[key]:
            item["long_html"] = fix_unclosed_p(item.get("long_html"))
    paths = collections.defaultdict(set)
    for key in KEYS:
        for i, item in enumerate(data[key]):
            if isinstance(item, dict):
                for _, _, t in paragraphs(item.get("long_html")):
                    paths[t].add("%s[%d]" % (key, i))
    dups = {t for t, p in paths.items() if len(p) > 1}
    print("duplicate paragraphs:", len(dups), "occurrences:", sum(len(paths[t]) for t in dups))

    groups = collections.OrderedDict((k, []) for k in KEYS)
    seen = set()
    for key in KEYS:
        for item in data[key]:
            for _, _, t in paragraphs(item.get("long_html")):
                if t in dups and t not in seen:
                    groups[key].append(t)
                    seen.add(t)

    removed = 0
    for key in KEYS:
        for item in data[key]:
            h = item.get("long_html") or ""
            before = len(plain(h))
            h = clean_empty_headings(strip_dups(h, dups))
            item["long_html"] = h
            removed += before - len(plain(h))

    labels = {"papers": "论文阅读法", "algorithms": "算法卡复现法",
              "theory": "理论卡读法", "directions": "方向页读法", "stories": "故事读法"}
    parts = ['<h3>附录 C · 通用阅读与复现清单（全站唯一一份）</h3>',
             '<p class="lead">这一节把原先复制在每个论文/算法/理论页里的通用方法收成一份。'
             '页面本身只留该单元独有的内容；需要“怎么读、怎么复现、怎么记日志”时回到这里查。</p>']
    for key in KEYS:
        if not groups[key]:
            continue
        parts.append("<h4>%s</h4>" % labels[key])
        for t in groups[key]:
            parts.append("<p>%s</p>" % html.escape(t, quote=False))
    block = "\n".join(parts)
    app = json.load(open(os.path.join(DATA, "appendix.json"), encoding="utf-8"))
    h = app.get("long_html") or ""
    h = re.sub(r"<h3>附录 C · 通用阅读与复现清单（全站唯一一份）</h3>[\s\S]*?(?=<h3>|$)", "", h)
    app["long_html"] = h.rstrip() + "\n" + block
    added = len(plain(block))
    print("removed plain chars:", removed, "appendix C chars:", added, "net:", added - removed)

    for key in KEYS:
        with open(os.path.join(DATA, key + ".json"), "w", encoding="utf-8") as f:
            json.dump(data[key], f, ensure_ascii=False, indent=1)
            f.write("\n")
    with open(os.path.join(DATA, "appendix.json"), "w", encoding="utf-8") as f:
        json.dump(app, f, ensure_ascii=False, indent=1)
        f.write("\n")


if __name__ == "__main__":
    main()
