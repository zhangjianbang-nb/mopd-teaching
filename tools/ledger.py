# -*- coding: utf-8 -*-
"""正文可见字符账：bundle 内所有字符串值 + book.sections[].html，同一套口径。

口径：去 script/style → 标签直接删除（不插空格）→ 空白折叠 → strip。
字段名不算；ledger 口径（整份 JSON）比正文高约 4–5%。

用法：python3 -I tools/ledger.py [--target 5000000]
"""
import argparse
import json
import os
import re
import sys

RUN = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(RUN, "site", "data")
MODS = ["papers", "algorithms", "theory", "assessments", "book", "appendix",
        "directions", "stories", "summary", "evolution", "domain", "coverage"]


def vis(s):
    s = re.sub(r"<(script|style)[^>]*>.*?</\1>", "", s, flags=re.S)
    s = re.sub(r"<[^>]+>", "", s)
    return len(re.sub(r"\s+", " ", s).strip())


def walk(v):
    if isinstance(v, str):
        return vis(v)
    if isinstance(v, dict):
        return sum(walk(x) for x in v.values())
    if isinstance(v, list):
        return sum(walk(x) for x in v)
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--target", type=int, default=5_000_000)
    args = ap.parse_args()
    rows = []
    for m in MODS:
        p = os.path.join(DATA, m + ".json")
        d = json.load(open(p, encoding="utf-8"))
        n = walk(d)
        cjk = len(re.findall(r"[\u4e00-\u9fff]", json.dumps(d, ensure_ascii=False)))
        rows.append((m, n, cjk))
    total = sum(r[1] for r in rows)
    print("%-16s %12s %10s" % ("模块", "可见正文", "CJK(含键)"))
    for k, v, c in rows:
        print("%-16s %12d %10d" % (k, v, c))
    print("%-16s %12d" % ("合计", total))
    print("目标 %d；余量 %d（%.1f%%）；%s" %
          (args.target, total - args.target, (total - args.target) * 100.0 / args.target,
           "PASS" if total >= args.target else "FAIL"))
    return 0 if total >= args.target else 1


if __name__ == "__main__":
    sys.exit(main())
