# -*- coding: utf-8 -*-
"""交付前硬断言（不依赖 verify_site，独立实现，防止同一 bug 两次放过）。

用法：python3 -I tools/assert_all.py
退出码 0 = 全过；1 = 有 FAIL。
"""
import json
import os
import re
import sys

RUN = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(RUN, "site", "data")
TARGET = 5_000_000
UNIT_MIN = 500

MOD_FLOOR = {
    "papers": 200_000, "algorithms": 200_000, "theory": 120_000,
    "assessments": 3_500_000, "book": 350_000, "appendix": 200_000,
    "directions": 8_000, "stories": 4_000, "summary": 1_500,
    "evolution": 1_200, "domain": 1_000, "coverage": 1_000,
}
EXPECT = {"directions": 8, "papers": 36, "algorithms": 60, "theory": 58,
          "stories": 5, "assessments": 1126, "book": 24}

fails = []
checks = []


def ok(name, cond, detail=""):
    checks.append((name, bool(cond), detail))
    if not cond:
        fails.append(name + (" — " + detail if detail else ""))


def vis(html):
    h = re.sub(r"<(script|style)[^>]*>.*?</\1>", "", html, flags=re.S)
    return len(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", h)).strip())


def load(name):
    return json.load(open(os.path.join(DATA, name + ".json"), encoding="utf-8"))


def walk(v):
    if isinstance(v, str):
        return vis(v)
    if isinstance(v, dict):
        return sum(walk(x) for x in v.values())
    if isinstance(v, list):
        return sum(walk(x) for x in v)
    return 0


def paras(html):
    return [re.sub(r"<[^>]+>", "", p)[:60] for p in re.findall(r"<p>(.*?)</p>", html, re.S)]


def main():
    # 1) 总量与模块下限
    total = 0
    for m, floor in MOD_FLOOR.items():
        n = walk(load(m))
        total += n
        ok("模块 %s ≥ %d" % (m, floor), n >= floor, "实际 %d" % n)
    ok("全站正文 ≥ %d" % TARGET, total >= TARGET, "实际 %d" % total)

    # 2) 件数
    for m, n in EXPECT.items():
        d = load(m)
        cnt = len(d["sections"]) if m == "book" else len(d)
        ok("件数 %s = %d" % (m, n), cnt == n, "实际 %d" % cnt)

    # 3) 单件 ≥500 且无重复段落
    for m in ["papers", "algorithms", "theory", "assessments", "directions"]:
        items = load(m)
        thin = [x.get("id") for x in items
                if vis(x.get("long_html", "")) < UNIT_MIN]
        ok("%s 单件 ≥500" % m, not thin, "过短 %s" % thin[:5])
        dup = 0
        for x in items:
            ps = paras(x.get("long_html", ""))
            seen = set()
            for p in ps:
                if p in seen:
                    dup += 1
                seen.add(p)
        ok("%s 无重复段落" % m, dup == 0, "重复 %d" % dup)
    for m, key in [("book", "html"), ("appendix", "long_html")]:
        d = load(m)
        items = d["sections"] if m == "book" else [d]
        thin = [x.get("id", "appendix") for x in items if vis(x.get(key, "")) < UNIT_MIN]
        ok("%s 单件 ≥500" % m, not thin, "过短 %s" % thin[:5])
        dup = 0
        for x in items:
            ps = paras(x.get(key, ""))
            seen = set()
            for p in ps:
                if p in seen:
                    dup += 1
                seen.add(p)
        ok("%s 无重复段落" % m, dup == 0, "重复 %d" % dup)

    # 4) 禁止标签（数据正文）
    bad = []
    for m in MOD_FLOOR:
        txt = json.dumps(load(m), ensure_ascii=False)
        for tag in ("<pre", "<script", "<style"):
            if tag in txt:
                bad.append((m, tag))
    ok("数据正文无 pre/script/style", not bad, str(bad[:3]))

    # 5) 结构：论文/方向/题库/理论/故事
    papers = load("papers")
    dirs = load("directions")
    algs = load("algorithms")
    theory = load("theory")
    assess = load("assessments")
    stories = load("stories")

    pids = {p["id"] for p in papers}
    dids = {d["id"] for d in dirs}
    tids = {t["id"] for t in theory}
    ok("论文方向都存在", all(p["direction"] in dids for p in papers))
    ok("算法方向都存在", all(a["direction"] in dids for a in algs))
    ok("理论论文引用存在", all(pid in pids for t in theory for pid in t.get("papers", [])))
    ok("算法论文引用存在", all(pid in pids for a in algs for pid in a.get("papers", [])))
    ok("方向论文引用存在", all(pid in pids for d in dirs for pid in d.get("key_papers", [])))
    ok("方向关联存在", all(r in dids for d in dirs for r in d.get("related", [])))
    ok("题库引用存在", all(q["ref"] in pids for q in assess if q["module"] == "paper"))
    covered = {q["ref"] for q in assess if q["module"] == "paper"}
    ok("每篇论文有题", covered == pids, "缺 %s" % sorted(pids - covered)[:5])
    ok("五层齐全", {q["level"] for q in assess} == {1, 2, 3, 4, 5})
    ok("每个方向有题", all(any(any(p["id"] == q["ref"] and p["direction"] == d["id"]
                                 for p in papers)
                             for q in assess if q["module"] == "paper")
                         for d in dirs))

    # 理论先修无环 + 有入口
    graph = {t["id"]: [x for x in t.get("prereq", []) if x in tids] for t in theory}
    ok("理论有入口", any(not v for v in graph.values()))
    color = {}

    def dfs(n):
        if color.get(n) == 1:
            return False
        if color.get(n) == 2:
            return True
        color[n] = 1
        for m in graph.get(n, []):
            if not dfs(m):
                return False
        color[n] = 2
        return True
    ok("理论先修无环", all(dfs(n) for n in graph))

    # 故事结构
    for s in stories:
        ok("故事 %s 幕数 ≥4" % s["id"], len(s.get("plot", [])) >= 4)
        ok("故事 %s 每幕 ≥40 字" % s["id"],
           all(len(x.get("text", "")) >= 40 for x in s.get("plot", [])))
        ok("故事 %s 角色 ≥3" % s["id"], len(s.get("roles", [])) >= 3)
        ok("故事 %s 映射 ≥3" % s["id"], len(s.get("mapping", [])) >= 3)
        ok("故事 %s 边界 ≥2" % s["id"], len(s.get("boundaries", [])) >= 2)
    flag = next(s for s in stories if s["id"] == "story-four-masters")
    ok("旗舰故事覆盖 24 章", len(flag.get("covers", [])) == 24)

    # 6) 首页五层图（JS 模板里，按字符串断言）
    html = open(os.path.join(RUN, "site", "index.html"), encoding="utf-8").read()
    ok("首页有五层 SVG", 'figure class="figure diagram"' in html and "<svg viewBox" in html)
    ok("无 CDN 外链", "https://cdn" not in html and "http://cdn" not in html)

    for name, passed, detail in checks:
        print(("PASS  " if passed else "FAIL  ") + name + (("  [" + detail + "]") if detail and not passed else ""))
    print("\n合计 %d 项；FAIL %d 项" % (len(checks), len(fails)))
    return 0 if not fails else 1


if __name__ == "__main__":
    sys.exit(main())
