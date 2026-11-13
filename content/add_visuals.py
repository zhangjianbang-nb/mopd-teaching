# -*- coding: utf-8 -*-
"""给 MOPD 站补「公式 + 表 + 图」：全部来自 JSON 字段的数据驱动示意图。

用法：python3 -I content/add_visuals.py
幂等：每块图/表带 <!--VIS:key:start--> ... <!--VIS:key:end--> 标记，重跑先删旧块再插。
"""
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
RUN = os.path.dirname(HERE)
DATA = os.path.join(RUN, "site", "data")
SKILL = os.path.expanduser("~/.zcode/skills/ai-domain-research-and-teaching/scripts")
sys.path.insert(0, SKILL)
import svgkit  # noqa: E402


def load(name):
    with open(os.path.join(DATA, name + ".json"), encoding="utf-8") as f:
        return json.load(f)


def save(name, obj):
    with open(os.path.join(DATA, name + ".json"), "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)
        f.write("\n")


def fig(svg, caption):
    return ('<figure class="figure diagram">' + svg +
            '<figcaption>' + caption + '</figcaption></figure>')


def wrap_math(s):
    s = (s or "").strip()
    if not s:
        return s
    if "$$" in s:
        return s
    return "$$" + s + "$$"


def _strip_old(html, key):
    return re.sub(r"<!--VIS:%s:start-->[\s\S]*?<!--VIS:%s:end-->" % (re.escape(key), re.escape(key)),
                  "", html or "")


def inject(html, key, block):
    """幂等插入：删掉旧 key 块，再把新块放最前面。"""
    return ("<!--VIS:%s:start-->" % key) + block + ("<!--VIS:%s:end-->" % key) + _strip_old(html, key)


def inject_at(html, key, block, anchor=None):
    """幂等插入到指定 h3 小节末尾（下一个 h3 之前）；找不到锚点时退回页首。

    图必须长在它解释的那一节里：论文的 pipeline 图跟「5. 结构与流程」走，
    证据链图跟「8. 实验」走；书章的弧线图跟「0. 这一章的位置」走。
    """
    html = _strip_old(html, key)
    if not anchor:
        return inject(html, key, block)
    m = re.search(r"<h3[^>]*>[\s\S]*?" + re.escape(anchor) + r"[\s\S]*?</h3>", html)
    if not m:
        return inject(html, key, block)
    nxt = re.search(r"<h3[^>]*>", html[m.end():])
    pos = m.end() + (nxt.start() if nxt else len(html) - m.end())
    return (html[:pos] + "<!--VIS:%s:start-->" % key + block +
            "<!--VIS:%s:end-->" % key + html[pos:])


def head_title(p, limit=30):
    """论文短名：取冒号前的部分（MOPD / Open-MOPD / Beyond Policy Discrepancy），
    避免把英文标题从单词中间切断。"""
    t = re.sub(r"\s+", " ", str(p.get("title") or p.get("id") or "")).strip()
    head = t.split(":")[0].strip()
    if len(head) <= limit:
        return head
    return head[:limit - 1].rstrip() + "…"


def table(headers, rows):
    head = "".join("<th>" + h + "</th>" for h in headers)
    body = "".join("<tr>" + "".join("<td>" + str(c) + "</td>" for c in row) + "</tr>" for row in rows)
    return ('<div class="table-wrap"><table class="mini"><thead><tr>' + head +
            '</tr></thead><tbody>' + body + '</tbody></table></div>')


def add_papers(papers):
    for p in papers:
        p["formula"] = wrap_math(p.get("formula"))
        pipeline = p.get("pipeline") or []
        svg1 = svgkit.flow_v(pipeline[:6] or ["（pipeline 未录入）"])
        cap1 = "图 1 · 方法流水线：按 papers.json 的 pipeline 字段绘制，箭头表示数据流，不是论文原图。"
        evidence = [
            "问题：" + (p.get("problem") or ""),
            "想法：" + (p.get("core_idea") or ""),
            "证据：" + ((p.get("experiments") or {}).get("results") or ""),
        ]
        svg2 = svgkit.flow_v(evidence, kinds=["in", "mid", "out"])
        cap2 = "图 2 · 证据链：问题 → 核心想法 → 实验证据，文字取自论文卡字段；数字口径见实验表。"
        # 两块图分别落在结构与流程、实验两节末尾，不再堆在长文开头。
        p["long_html"] = _strip_old(p.get("long_html"), "paper-%s" % p["id"])
        p["long_html"] = inject_at(p.get("long_html"), "paper-%s-fig1" % p["id"], fig(svg1, cap1), "5. 结构与流程")
        p["long_html"] = inject_at(p.get("long_html"), "paper-%s-fig2" % p["id"], fig(svg2, cap2), "8. 实验")


def add_algorithms(algs, papers_by_id):
    for a in algs:
        pid = (a.get("papers") or [""])[0]
        src = papers_by_id.get(pid, {})
        a["formula"] = wrap_math(src.get("formula") or a.get("formula"))
        flow = a.get("flow") or []
        svg = svgkit.flow_v(flow[:6] or ["（flow 未录入）"])
        cap = "图 1 · 执行流程：按 algorithms.json 的 flow 字段绘制；编号是执行顺序，箭头是依赖。"
        a["long_html"] = inject_at(a.get("long_html"), "algo-%s" % a["id"], fig(svg, cap), "5. 步骤")


def add_theory(theory):
    by_id = {t["id"]: t for t in theory}
    reverse = {t["id"]: [] for t in theory}
    for t in theory:
        for pre in t.get("prereq") or []:
            if pre in reverse:
                reverse[pre].append(t["id"])
    for t in theory:
        t["formula"] = wrap_math(THEORY_LATEX_FIX.get(t["id"], t.get("formula")))
        prev = [by_id[x].get("title") for x in (t.get("prereq") or []) if x in by_id][:3]
        nxt = [by_id[x].get("title") for x in reverse.get(t["id"], [])][:3]
        svg = svgkit.chain3(prev or ["入口 · 无先修"], t.get("title"), nxt or ["后续 · 见演进图"],
                            cur_sub="理论卡 %s · 先修关系由 theory.json 反查" % t["id"])
        cap = "图 1 · 先修关系：左列是先修卡，右列是反查出的后继卡；箭头表示学习顺序。"
        t["long_html"] = inject_at(t.get("long_html"), "theory-%s" % t["id"], fig(svg, cap), "13. 与其他理论卡的关系")


def h3_texts(html):
    out = []
    for m in re.findall(r"<h3[^>]*>([\s\S]*?)</h3>", html or ""):
        out.append(re.sub(r"<[^>]+>", "", m).strip())
    return out


def add_directions(dirs, papers_by_id):
    for d in dirs:
        rows = []
        for pid in (d.get("key_papers") or [])[:6]:
            p = papers_by_id.get(pid)
            if p:
                rows.append([p.get("title", pid), p.get("year", ""),
                             p.get("summary") or p.get("core_idea") or ""])
        tbl = table(["代表论文", "年份", "在本方向回答什么"], rows)
        tech = "、".join((d.get("core_tech") or [])[:3])
        papers_txt = [head_title(papers_by_id[x]) for x in (d.get("key_papers") or [])[:3] if x in papers_by_id]
        svg = svgkit.chain3([d.get("question")], tech, papers_txt or ["（论文待补）"],
                            cur_sub="方向 %s · 问题→技术→论文（directions.json 字段）" % d["id"])
        cap = "图 1 · 问题→技术→论文：左列是方向要回答的问题，中列是核心技术，右列是代表论文。"
        heads = h3_texts(d.get("long_html"))
        d["long_html"] = _strip_old(d.get("long_html"), "dir-%s" % d["id"])
        d["long_html"] = inject_at(d.get("long_html"), "dir-%s-fig" % d["id"], fig(svg, cap),
                                   heads[0] if heads else None)
        d["long_html"] = inject_at(d.get("long_html"), "dir-%s-table" % d["id"], tbl,
                                   heads[1] if len(heads) > 1 else (heads[0] if heads else None))


def add_stories(stories):
    for s in stories:
        roles = [r.get("role") for r in (s.get("roles") or [])][:3]
        acts = [x.get("act") for x in (s.get("plot") or [])][:4]
        concepts = [m.get("concept") for m in (s.get("mapping") or [])][:3]
        svg = svgkit.chain3(roles or ["角色"], "、".join(acts) or "剧情", concepts or ["概念"],
                            cur_sub="故事 %s · 角色→剧情→概念（stories.json 字段）" % s["id"])
        cap = "图 1 · 故事地图：左列是三个核心角色（完整角色表见下方），中列是四幕剧情，右列是映射到的技术概念。"
        s["long_html"] = inject(s.get("long_html"), "story-%s" % s["id"], fig(svg, cap))


# 理论卡里有 14 张用 Unicode 数学符号写的公式，KaTeX 会报红字。
# 这里按 id 换成等价的 LaTeX 命令，保证 throwOnError=false 下也不出现红字。
THEORY_LATEX_FIX = {
    "t01": r"$$\mathrm{KL}(p_\theta\|p_t) = \sum_y p_\theta(y)\log\frac{p_\theta(y)}{p_t(y)}$$",
    "t02": r"$$L_{\mathrm{OPD}} = -\mathbb{E}_{y\sim\pi_\theta}\sum_t \mathrm{sg}\big(\log\pi_t(y_t\mid\cdot) - \log\pi_\theta(y_t\mid\cdot)\big)\cdot\log\pi_\theta(y_t\mid\cdot)$$",
    "t04": r"$$A_t = \mathrm{clip}\big(\log\pi_t(y_t\mid h_t) - \log\pi_\theta(y_t\mid h_t),\,-c,\,c\big)$$",
    "t05": r"$$\mathrm{gap} = \mathrm{KL}(p_t\|p_\theta^*) - \mathrm{KL}(p_t\|p_t) > 0,\ \text{when}\ \mathrm{cap}(\theta) < \mathrm{cap}(t)$$",
    "t06": r"$$\cos(g_i,g_j) < 0 \Rightarrow \langle g_i,\sum_k w_k g_k\rangle < 0\ \text{for some } i$$",
    "t07": r"$$\mathrm{share}_d = \frac{\mathrm{tokens}_d}{\sum \mathrm{tokens}},\quad \mathrm{var\_share}_d = \frac{\mathrm{pooled\_var}_d}{\sum \mathrm{pooled\_var}}$$",
    "t08": r"$$\mathrm{align} \Leftrightarrow z_t^{\text{teacher}} = z_t^{\text{student}} = [q, x_t]$$",
    "t09": r"$$L = \mathbb{E}\big[\mathrm{sg}\big(\log\pi_t(a\mid h,\mathrm{priv}) - \log\pi_\theta(a\mid h)\big)\cdot\log\pi_\theta(a\mid h)\big]$$",
    "t10": r"$$\mathrm{elig}(k,x) = \mathbf{1}\big[\mathrm{verify}(\mathrm{ans}_k(x)) = \mathrm{correct}\big]$$",
    "t11": r"$$\mathrm{mass}_K = \sum_{v\in\mathrm{topK}} p(v),\quad \mathrm{hit} = \mathbf{1}[v_{\text{entry}}\in\mathrm{topK}]$$",
    "t12": r"$$\Delta_{\mathrm{proj}} = \Big(I - \sum_k U_k U_k^T\Big)\Delta,\quad U_k = \mathrm{SVD}(\Delta_k)$$",
    "t14": r"$$w = \frac{\alpha_{\mathrm{eff}}}{\alpha_{\mathrm{eff}}+\beta},\quad \alpha_{\mathrm{eff}} = \sum_{e\in E}\mathrm{rel}(e)$$",
    "t15": r"$$\mathrm{waste} = 1 - \frac{\mathrm{used\_turns}}{\mathrm{total\_turns}}$$",
    "t45": r"$$\max_\theta V_{\text{proxy}}(\theta)\quad\text{s.t.}\ \text{true}(\theta)\ \text{must not increase}$$",
}

CH_THEORY = ["t01", "t02", "t06", "t28", "t09", "t08", "t10", "t11", "t33", "t41",
             "t13", "t15", "t22", "t24", "t23", "t30", "t32", "t14", "t47", "t48",
             "t50", "t18", "t42", "t45"]
CH_ARC = {"ch01", "ch05", "ch09", "ch13", "ch17", "ch21"}


def add_book(book, theory_by_id):
    secs = book.get("sections") or []
    for i, sec in enumerate(secs):
        tid = CH_THEORY[i] if i < len(CH_THEORY) else None
        t = theory_by_id.get(tid)
        if t:
            f = wrap_math(t.get("formula"))
            block = '<div class="formula math">' + f + '</div>'
            sec["html"] = inject_at(sec.get("html"), "book-formula-%s" % sec["id"], block, "2. 记号与定义")
        if sec["id"] in CH_ARC:
            prev = secs[i - 1].get("title") if i > 0 else "（开篇）"
            nxt = secs[i + 1].get("title") if i + 1 < len(secs) else "（收束）"
            svg = svgkit.chain3([prev], sec.get("title"), [nxt],
                                cur_sub="第 %02d 章 / 24 · 在全书弧线中的位置" % (i + 1))
            cap = "图 1 · 章节位置：左列上一章，中列本章，右列下一章；用于建立 24 章的整体路线感。"
            sec["html"] = inject_at(sec.get("html"), "book-arc-%s" % sec["id"], fig(svg, cap), "0. 这一章的位置")


def add_appendix(app, book):
    h = app.get("long_html") or ""
    terms = re.findall(r"<summary>(G\d{4}) · ([^<]+)</summary>", h)
    if not terms:
        terms = re.findall(r"<h3>(G\d{4}) · ([^<]+)</h3>", h)
    rows = [[g, name] for g, name in terms[:12]]
    t1 = table(["术语编号", "术语"], rows)
    chapters = book.get("sections") or []
    t2 = table(["章", "标题", "在附录里的用法"], [[c.get("id"), c.get("title"), "术语/案例按章回链"] for c in chapters[:12]])
    t3 = table(["索引", "规模", "说明"],
               [["术语表", "%d 条" % len(terms), "按章分组，含定义/误用/一句话记法"],
                ["工匠笔记", "60 个案例", "症状→取证→根因→修复→防再犯"],
                ["公式速查", "见各章公式块", "由理论卡公式回填到书章"]])
    svg = svgkit.flow_v(["术语表 %d 条" % len(terms), "工匠笔记 60 个案例", "公式与口径索引"],
                        kinds=["in", "mid", "out"])
    cap = "图 1 · 附录结构：术语、案例、公式三条索引的规模与用途；数字取自 appendix.json。"
    app["long_html"] = inject(h, "appendix-vis", fig(svg, cap) + t1 + t2 + t3)


def main():
    papers = load("papers")
    algs = load("algorithms")
    theory = load("theory")
    dirs = load("directions")
    stories = load("stories")
    book = load("book")
    app = load("appendix")

    papers_by_id = {p["id"]: p for p in papers}
    theory_by_id = {t["id"]: t for t in theory}

    add_papers(papers)
    add_algorithms(algs, papers_by_id)
    add_theory(theory)
    add_directions(dirs, papers_by_id)
    add_stories(stories)
    add_book(book, theory_by_id)
    add_appendix(app, book)

    save("papers", papers)
    save("algorithms", algs)
    save("theory", theory)
    save("directions", dirs)
    save("stories", stories)
    save("book", book)
    save("appendix", app)
    print("visuals injected: papers=%d algorithms=%d theory=%d directions=%d stories=%d book=%d appendix=1"
          % (len(papers), len(algs), len(theory), len(dirs), len(stories), len(book.get("sections") or [])))


if __name__ == "__main__":
    main()
