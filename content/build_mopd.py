# -*- coding: utf-8 -*-
"""把 mopd-book-20261111 的语料重建为 skill 结构化的 MOPD 教学站数据。

用法：python3 -I content/build_mopd.py [--part papers|theory|algos|assess|book|appendix|all]
输出：site/data/*.json（domain/directions/... 由 content/build_meta.py 另写）
"""
import argparse
import glob
import html as html_lib
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
RUN = os.path.dirname(HERE)
sys.path.insert(0, HERE)
from md2html import dedup_paras, md2html, plain, section, sections  # noqa: E402

CORPUS = "/home/whu/workspace/ai_workspace/mopd-book-20261111"
DATA = os.path.join(RUN, "site", "data")

# 8 个方向：4 个沿用书稿，4 个横切（目标/路由/评测/治理）
DIRS = [
    ("code-capability-integration", "代码能力整合"),
    ("agentic-coding-longhorizon", "长程 Agent 编码"),
    ("verifiable-teacher-qualification", "可验证教师与资格"),
    ("distillation-efficiency-systems", "蒸馏效率与系统"),
    ("distillation-objectives", "蒸馏目标与理论"),
    ("multi-teacher-routing", "多教师路由与预算"),
    ("evaluation-diagnosis", "评测与诊断"),
    ("failure-modes-governance", "失败模式与治理"),
]

PAPER_DIR = {
    "hinton-kd": "distillation-objectives", "minillm": "distillation-objectives",
    "gkd": "distillation-objectives", "distillm": "distillation-objectives",
    "divopd": "distillation-objectives", "up-mopd": "distillation-efficiency-systems",
    "mopd": "code-capability-integration", "micius-flash": "code-capability-integration",
    "mimo-v2-flash": "code-capability-integration", "persd": "code-capability-integration",
    "selfcodealign": "code-capability-integration", "acd-loha": "code-capability-integration",
    "mapcoder-lite": "code-capability-integration",
    "oprd": "agentic-coding-longhorizon", "memopd": "agentic-coding-longhorizon",
    "hpd": "agentic-coding-longhorizon", "swe-ladder": "agentic-coding-longhorizon",
    "camp-ii": "agentic-coding-longhorizon", "open-swe-traces": "agentic-coding-longhorizon",
    "p2t": "agentic-coding-longhorizon",
    "ekt-code": "verifiable-teacher-qualification", "codeplan": "verifiable-teacher-qualification",
    "reflectioncoder": "verifiable-teacher-qualification", "mt-sdpo": "verifiable-teacher-qualification",
    "trustmopd": "evaluation-diagnosis",
    "p2-mopd": "distillation-efficiency-systems", "pmopd": "distillation-efficiency-systems",
    "open-mopd": "multi-teacher-routing", "dn-mopd": "multi-teacher-routing",
    "ca-mopd": "multi-teacher-routing", "mopd-router": "multi-teacher-routing",
    "tool-call-drift": "failure-modes-governance", "eesd": "failure-modes-governance",
    "ftb-opd": "failure-modes-governance", "hisentinel": "failure-modes-governance",
    "compete-collaborate": "failure-modes-governance",
}

# 24 章 → 主论文
CH_PAPER = ["hinton-kd", "gkd", "mopd", "oprd", "ekt-code", "memopd", "trustmopd",
            "p2t", "compete-collaborate", "p2-mopd", "up-mopd", "divopd",
            "mopd-router", "dn-mopd", "ca-mopd", "camp-ii", "hpd", "eesd",
            "p2t", "ftb-opd", "tool-call-drift", "acd-loha", "micius-flash",
            "open-swe-traces"]


def vis(html):
    h = re.sub(r"<(script|style)[\s\S]*?</\1>", " ", html, flags=re.I)
    h = re.sub(r"<[^>]+>", "", h)
    return len(re.sub(r"\s+", " ", h).strip())


def load_papers():
    with open(os.path.join(CORPUS, "site/data/papers.json"), encoding="utf-8") as f:
        return json.load(f)


def md_file(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def _drop_section(h, num):
    """删掉 long_html 里第 num 节（h3 开头）的整节；找不到就原样返回。"""
    m = re.search(r"<h3>\s*%d\.\s*[^<]*</h3>" % num, h)
    if not m:
        return h
    nxt = re.search(r"<h3>", h[m.end():])
    end = m.end() + (nxt.start() if nxt else len(h) - m.end())
    return h[:m.start()] + h[end:]


def _strip_first_block(h, num):
    """删掉第 num 节开头的第一个 p/ul/ol 块，保留点评、图与后续块。"""
    m = re.search(r"<h3>\s*%d\.\s*[^<]*</h3>" % num, h)
    if not m:
        return h
    nxt = re.search(r"<h3>", h[m.end():])
    end = m.end() + (nxt.start() if nxt else len(h) - m.end())
    body = h[m.end():end]
    bm = re.match(r"\s*<(p|ul|ol)[^>]*>[\s\S]*?</\1>", body)
    if not bm:
        return h
    return h[:m.end()] + body[bm.end():] + h[end:]


def _plain_html(s):
    return re.sub(r"\s+", " ", html_lib.unescape(re.sub(r"<[^>]+>", "", s or ""))).strip()


def _dedup_li(html):
    """同一单元内重复的 li 只留第一份（如书章里每个函数都复读同一句「关键行」）。"""
    seen = set()
    out = []
    for part in re.split(r"(<li[^>]*>[\s\S]*?</li>)", html):
        if part.startswith("<li"):
            key = _plain_html(part)
            if len(key) >= 30 and key in seen:
                continue
            seen.add(key)
        out.append(part)
    return "".join(out)


def _drop_matching_list(h, items):
    """删掉整段 ul/ol：当其中每个 li 都能在 items（页面已渲染的列表）里找到时。"""
    wanted = {_plain_html(x) for x in (items or []) if str(x).strip()}
    if not wanted:
        return h
    out, pos = [], 0
    for m in re.finditer(r"<(ul|ol)[^>]*>([\s\S]*?)</\1>", h):
        lis = [_plain_html(x) for x in re.findall(r"<li[^>]*>([\s\S]*?)</li>", m.group(2))]
        if lis and all(x in wanted for x in lis):
            out.append(h[pos:m.start()])
            pos = m.end()
    out.append(h[pos:])
    return "".join(out)


def _paper_dedup(h, p):
    """论文页已按结构化字段渲染背景/问题/想法/架构/公式/训练/实验/局限；
    long_html 的第 1 节与第 2-8/10 节首块是同一段文字，流程列表也与页面「数据流」重复，删掉。"""
    h = _drop_section(h, 1)
    for num in (2, 3, 4, 5, 6, 7, 8, 10):
        h = _strip_first_block(h, num)
    return _drop_matching_list(h, p.get("pipeline") or [])


def _theory_dedup(h):
    """理论页已按字段渲染通俗解释/定义/推导/例子/局限；
    long_html 的 1 节整节与 2/4/5/7 节首块重复，删掉，保留符号表与点评。"""
    h = _drop_section(h, 1)
    for num in (2, 4, 5, 7):
        h = _strip_first_block(h, num)
    return h


def _drop_h3(h, title):
    """按 h3 标题精确删掉整节（标题与正文）；同名小节出现多次时全部删掉。"""
    pat = re.compile(r"<h3[^>]*>\s*" + re.escape(title) + r"\s*</h3>")
    while True:
        m = pat.search(h)
        if not m:
            return h
        nxt = re.search(r"<h3[^>]*>", h[m.end():])
        end = m.end() + (nxt.start() if nxt else len(h) - m.end())
        h = h[:m.start()] + h[end:]


def _assess_dedup(h):
    """题库页已按结构化字段渲染题面/答案/解析/评分/错答；
    long_html 里同名小节重复，删掉，只保留代码锚点、数字核算、边界、追问、变体等扩展。"""
    for title in ("题面", "参考答案", "完整解答", "解析", "评分要点", "常见错答",
                  "1. 题目", "2. 一句话答案", "3. 为什么问这个", "5. 机制拆解",
                  "8. 反例清单", "9. 工程落地"):
        h = _drop_h3(h, title)
    return h


def _review_note(q):
    """给短题补一段题目专属复盘提示：既补足 500 字，又不与结构化字段整段重复。"""
    question = html_lib.escape(str(q.get("question") or "")[:140], quote=False)
    answer = html_lib.escape(str(q.get("answer") or "")[:220], quote=False)
    return ('<h3>复盘提示</h3><p>这道题的检查点是「%s」。参考解答的关键动作是「%s」。'
            '复盘时把答案压成三行：口径（分子、分母、参照系各是什么）、差值（谁减谁、'
            '分母是否相同）、边界（哪个条件一变结论就失效）。三行缺任何一行，这道题在'
            '复试里都会被追问；补全三行，再对照评分细则逐项打勾，才算把这道题真正做完。</p>'
            % (question, answer))


def build_papers():
    papers = load_papers()
    files = {os.path.basename(p).split("_")[0]: p for p in glob.glob(os.path.join(CORPUS, "docs/papers/*.md"))}
    for p in papers:
        p["direction"] = PAPER_DIR.get(p["id"], p["direction"])
        # 去掉元数据小节（页面头已渲染），其余全文转 HTML
        src = md_file(files["P%02d" % (papers.index(p) + 1)])
        src = re.sub(r"^##\s+0\.\s+元数据[\s\S]*?(?=^##\s)", "", src, flags=re.M)
        # 短字段来自语料 JSON，可能残留 markdown 粗体标记；页面按纯文本渲染，必须去掉
        for k, v in list(p.items()):
            if k == "long_html":
                continue
            if isinstance(v, str):
                p[k] = v.replace("**", "")
            elif isinstance(v, list):
                p[k] = [x.replace("**", "") if isinstance(x, str) else x for x in v]
        p["long_html"] = _paper_dedup(md2html(src), p)
        # prereq 只保留存在的 id（论文或理论卡），避免 E-REF
        p["prereq"] = [x for x in p.get("prereq", []) if isinstance(x, str) and (x in {q["id"] for q in papers} or x.startswith("t"))]
        p["successors"] = [x for x in p.get("successors", []) if isinstance(x, str) and x in {q["id"] for q in papers}]
        p.setdefault("figures", [])
    return papers


THEORY_DIR = {}


def theory_dir(title):
    t = title
    if any(k in t for k in ("KL", "OPD", "曝光", "advantage", "温度", "JSD", "α-skew", "λ",
                            "策略梯度", "logits", "序列级", "强制", "状态对齐", "特权")):
        return "distillation-objectives"
    if any(k in t for k in ("路由", "预算", "容量差距", "冲突", "集成权重", "Oracle", "最弱域", "坍塌", "教师强制")):
        return "multi-teacher-routing"
    if any(k in t for k in ("pass@k", "ECE", "Bootstrap", "种子", "Pareto", "算力", "泄漏", "checkpoint", "每 token")):
        return "evaluation-diagnosis"
    if any(k in t for k in ("黑客", "漂移", "过程图", "桥", "证据", "干预")):
        return "failure-modes-governance"
    if any(k in t for k in ("LoRA", "量化", "规模缩放", "梯度累积", "混合精度", "异步", "投影", "Dirichlet")):
        return "distillation-efficiency-systems"
    if any(k in t for k in ("记忆", "harness", "文件", "提醒", "课程", "支撑集", "子空间")):
        return "agentic-coding-longhorizon"
    if any(k in t for k in ("资格", "审计", "修正权重", "可靠性")):
        return "verifiable-teacher-qualification"
    return "distillation-objectives"


def bullets(md):
    out = []
    for ln in md.split("\n"):
        m = re.match(r"^\s*[-*+]\s+(.+)$", ln)
        if m:
            out.append(plain(m.group(1)))
    return [x for x in out if x]


def sentences(md, k=3):
    t = plain(md)
    parts = [x.strip() for x in re.split(r"(?<=[。！？；])", t) if len(x.strip()) >= 12]
    return parts[:k] if parts else [t[:60]]


def build_theory():
    cards = []
    files = sorted(glob.glob(os.path.join(CORPUS, "docs/reference/T*.md")))
    paper_ids = [p["id"] for p in load_papers()]
    for idx, fp in enumerate(files):
        src = md_file(fp)
        h1 = re.match(r"#\s+(.+)", src).group(1)
        m = re.match(r"(T\d+)\s*·\s*(.+)", h1)
        tid, title = (m.group(1).lower(), m.group(2).strip()) if m else ("t%02d" % (idx + 1), h1)
        sec = dict(sections(src))
        plain_txt = plain(sec.get("1. 一句话", "")) or plain(src)[:80]
        if len(plain_txt) < 40:
            plain_txt = (plain_txt + " 具体说，" + plain(sec.get("2. 定义与符号", ""))[:90]).strip()
        definition = plain(sec.get("2. 定义与符号", ""))[:300]
        formula = ""
        fm = re.search(r"\$\$([\s\S]*?)\$\$", sec.get("3. 公式", ""))
        if fm:
            formula = fm.group(1).strip()
        elif "$" in sec.get("3. 公式", ""):
            formula = sec.get("3. 公式", "").strip()[:160]
        formula = formula or "见正文定义"
        var_rows = []
        for ln in sec.get("2. 定义与符号", "").split("\n"):
            if ln.strip().startswith("|") and "符号" not in ln:
                cells = [c.strip() for c in ln.strip().strip("|").split("|")]
                if len(cells) >= 2 and cells[0] and not set(cells[0]) <= set("-: "):
                    var_rows.append("%s：%s" % (plain(cells[0]), plain(cells[1])))
        variables = var_rows[:8] or ["符号见正文符号表"]
        derivation = plain(sec.get("4. 推导", ""))[:400]
        example = plain(sec.get("5. 数值例子", ""))[:400]
        pseudo = ""
        pm = re.search(r"```[\s\S]*?```", sec.get("6. 伪代码与代码锚点", ""))
        if pm:
            pseudo = re.sub(r"```[a-z]*\n?", "", pm.group(0)).strip()
        pseudo = pseudo or plain(sec.get("6. 伪代码与代码锚点", ""))[:300]
        limits = bullets(sec.get("7. 边界与失效", ""))[:6] or sentences(sec.get("7. 边界与失效", ""), 2)
        # 关联论文：按标题关键词挑一篇存在的
        cand = None
        for kw, pid in (("KL", "hinton-kd"), ("OPD", "gkd"), ("路由", "mopd-router"),
                        ("记忆", "memopd"), ("证据", "eesd"), ("资格", "trustmopd"),
                        ("效率", "p2-mopd"), ("投影", "up-mopd"), ("评测", "trustmopd")):
            if kw in title and pid in paper_ids:
                cand = pid
                break
        cand = cand or CH_PAPER[idx % len(CH_PAPER)]
        cards.append({
            "id": tid, "title": title, "direction": theory_dir(title),
            "prereq": [("t%02d" % idx)] if idx > 0 else [],
            "plain": plain_txt[:400], "definition": definition,
            "formula": formula, "variables": variables,
            "derivation": derivation, "example": example, "pseudocode": pseudo,
            "limits": limits, "papers": [cand], "long_html": _theory_dedup(md2html(src)),
        })
    return cards


def _esc(x):
    return html_lib.escape(str(x or ""), quote=False)


def _replace_sec(h, num, body):
    """把 long_html 里第 num 节（h3 开头）正文换成 body，保留标题。"""
    pat = r"(<h3>\s*%d\.\s*[^<]*</h3>)([\s\S]*?)(?=<h3>|\Z)" % num
    return re.sub(pat, lambda m: m.group(1) + body, h, count=1)


def _algo_html(h, p):
    """论文型实验的 1/2/3/5/6/7/9/10 节按论文卡字段重写。

    这八节原来是通用模板，60 个实验里有 36 个共用同一段假设、24 个共用同一段
    目的；读者在算法库里看到的是复制粘贴。重写后每张卡的假设、步骤、失败判据
    都跟着它自己的论文走。
    """
    problem = _esc(p.get("problem"))
    idea = _esc(p.get("core_idea"))
    training = _esc(p.get("training"))
    exp = p.get("experiments") or {}
    results = _esc(exp.get("results"))
    datasets = _esc("、".join(exp.get("datasets") or []))
    baselines = _esc("、".join(exp.get("baselines") or []))
    limits = _esc("；".join(p.get("limitations") or []))
    pipeline = [x for x in (p.get("pipeline") or []) if str(x).strip()]

    h = _replace_sec(h, 1,
        "<p>这份实验要回答：%s</p>"
        "<p>复现目标不是复刻论文的最大数字，而是在同一 harness、同一预算、同一学生下确认三件事："
        "主表差值能否重现；核心改动是不是提升来源；边界是否更早出现。</p>"
        "<p>论文设置：%s</p>" % (problem, training))
    h = _replace_sec(h, 2,
        "<p>H1：在同一 harness 下，本方法相对基线的主指标差值 ≥ 论文报告差值的一半。"
        "论文口径：%s</p>"
        "<p>H2：去掉核心改动后，提升消失 ≥ 70%%；若消融掉不到 30%%，说明核心改动可能不是主因。</p>"
        "<p>H3：缩小规模后，提升方向不变但幅度变小；若方向反转，记录规模阈值。</p>" % results)
    h = _replace_sec(h, 3,
        '<div class="table-wrap"><table class="mini"><thead><tr>'
        "<th>类型</th><th>变量</th><th>取值</th></tr></thead><tbody>"
        "<tr><td>自变量</td><td>方法开关 / 核心组件</td><td>关 / 开 / 只开组件</td></tr>"
        "<tr><td>因变量</td><td>主指标、最弱域、种子方差、成本</td><td>按论文口径</td></tr>"
        "<tr><td>控制变量</td><td>学生、数据、token 预算、harness、种子</td><td>与论文对齐或标注差异</td></tr>"
        "</tbody></table></div>"
        "<p>控制变量里最容易漏的是教师资格：教师在该域不及格时，开方法只会把错误放大。</p>")
    steps = "".join("<li>%s</li>" % _esc(x) for x in pipeline) or "<li>按论文方法一节逐步实现</li>"
    h = _replace_sec(h, 5,
        "<p>论文流水线：</p><ol>%s</ol>"
        "<p>复现动作：</p><ol>"
        "<li>读设置表：模型、数据、基线、harness 四项逐项对照；差异写进报告。</li>"
        "<li>重跑基线：用官方代码或自己实现，确认基线数字与论文差多少。</li>"
        "<li>跑本文方法：只改核心组件，其余不动。</li>"
        "<li>做消融：去掉核心组件、去掉辅助组件、去掉两者。</li>"
        "<li>换规模：至少一个小规模点，看方向是否保持。</li>"
        "<li>算成本：GPU-hours、token、峰值显存。</li></ol>" % steps)
    h = _replace_sec(h, 6,
        "<p>主指标按论文口径：%s</p>"
        "<p>统一补三项：最弱域、种子方差、成本（GPU-hours / token / 峰值显存）。"
        "论文没报最弱域的，自己补算并写口径。</p>" % results)
    h = _replace_sec(h, 7,
        "<p>预期：H1 成立（差值 ≥ 一半）；H2 成立（消融掉 ≥ 70%%）；H3 方向不变。</p>"
        "<p>失败判据：基线重跑差 > 2 分 → harness 没对齐；消融掉 < 30%% → 核心改动可能不是主因；"
        "小规模方向反转 → 方法有规模阈值；成本增加 > 50%% 而分数提升 < 0.5 分 → 不值得上线。</p>")
    h = _replace_sec(h, 9,
        "<p>边界变体（论文承认的局限）：%s</p>"
        "<p>换 harness、换种子、换规模各做一次，看结论是否保持；任何一项反转，都写进报告。</p>" % limits)
    h = _replace_sec(h, 10,
        "<p>论文局限对应的工程风险：%s</p>"
        "<p>通用回退：官方代码缺失 → 按伪代码实现并在合成任务上验证；数据不可得 → 同分布替代并标注；"
        "显存不足 → 降 batch / 梯度检查点 / LoRA，标注“非全参”；任何一步与论文差 > 2 分，回到上一步，不要跳步调参。</p>" % limits)
    return h


def build_algos():
    files = sorted(glob.glob(os.path.join(CORPUS, "docs/experiments/E*.md")))
    papers = {p["id"]: p for p in load_papers()}
    out = []
    for idx, fp in enumerate(files):
        src = md_file(fp)
        h1 = re.match(r"#\s+(.+)", src).group(1)
        m = re.match(r"(E\d+)\s*·\s*(.+)", h1)
        aid = (m.group(1).lower() if m else "e%02d" % (idx + 1))
        name = m.group(2).strip() if m else h1
        sec = dict(sections(src))
        pid = match_paper(name, list(papers.values())) or CH_PAPER[idx % len(CH_PAPER)]
        pap = papers.get(pid, {})
        # 章节实验的名字带「从基线到方法的完整对照」，读起来像模板；去掉后缀，
        # 保留章节隐喻，让人知道它对应书里的哪一章。
        if "从基线到方法的完整对照" in name:
            name = name.split("：")[0].strip() + " · 机制对照实验"
        problem = plain(sec.get("1. 目的", ""))[:400]
        idea = plain(sec.get("2. 假设", ""))[:300]
        how = plain(sec.get("5. 步骤", ""))[:500]
        flow = bullets(sec.get("5. 步骤", ""))[:6]
        if len(flow) < 3:
            flow = sentences(sec.get("5. 步骤", ""), 4)
        fm = re.search(r"\$\$([\s\S]*?)\$\$", src)
        formula = fm.group(1).strip() if fm else "见正文公式与口径表"
        pros = bullets(sec.get("7. 预期与失败判据", ""))[:4] or sentences(sec.get("7. 预期与失败判据", ""), 2)
        cons = bullets(sec.get("10. 风险与回退", ""))[:4] or sentences(sec.get("10. 风险与回退", ""), 2)
        # 结构化字段一律以论文卡为准：原来 60 个实验只有 2 套问题/假设/流程模板，
        # 算法库卡片看起来是复制粘贴。论文卡的 problem/core_idea/training/pipeline
        # 是逐篇写的，直接回填。
        if pap:
            problem = pap.get("problem") or problem
            idea = pap.get("core_idea") or idea
            how = pap.get("training") or how
            flow = list(pap.get("pipeline") or flow)
            formula = pap.get("formula") or formula
            pros = list(pap.get("innovation") or pros)
            cons = list(pap.get("limitations") or cons)
        item = {
            "id": aid, "name": name, "year": int(pap.get("year") or 2026),
            "tier": "classic" if pap.get("type") in ("foundational", "classic") else "recent",
            "direction": PAPER_DIR.get(pid, "code-capability-integration"),
            "problem": problem, "idea": idea, "how": how, "flow": flow,
            "formula": formula, "pros": pros, "cons": cons, "papers": [pid],
            "successors": [], "long_html": _algo_html(md2html(src), pap),
        }
        item["long_html"] = _drop_matching_list(item["long_html"], flow)
        out.append(item)
    return out


LEVEL_BY_SUFFIX = {"concept": 1, "derive": 3, "code": 2, "bug": 4, "experiment": 5,
                   "calc": 3, "grad": 3, "diagnose": 4}


def match_paper(header, papers):
    """按标题前缀匹配论文，取最长匹配。

    旧实现按列表顺序返回第一个命中：`MOPD-Router`、`Open-MOPD`、`P²-MOPD`、
    `PMOPD`、`UP-MOPD` 都会先命中 `MOPD`，结果七篇论文的算法卡全指向 MOPD。
    """
    h = header.lower()
    best = None
    for p in papers:
        key = p["title"].lower().split(":")[0][:24]
        pos = h.find(key) if key else -1
        if pos < 0:
            continue
        # 先比出现位置（标题主体在副标题之前），同位置再比长度：
        # `MiniLLM: On-Policy Distillation...` 里 minillm 在 on-policy 之前；
        # `MOPD-Router` 里 mopd-router 与 mopd 同位置，取更长的。
        score = (pos, -len(key))
        if best is None or score < best[0]:
            best = (score, p["id"])
    return best[1] if best else None


def build_assessments(papers):
    out = []
    # 1) 516 道题：题面 + 参考答案 + 逐步解析 + 评分要点 + 常见错答
    for fp in sorted(glob.glob(os.path.join(CORPUS, "docs/exercises/Q*.md"))):
        src = md_file(fp)
        h1 = re.match(r"#\s+(.+)", src).group(1)
        m = re.match(r"Q(\d+)-([A-Z]?\d+)\s*·\s*(.+?)\s*/\s*(\w+)", h1)
        ch, no, topic, suffix = (int(m.group(1)), m.group(2), m.group(3), m.group(4)) if m else (1, "01", h1, "concept")
        sec = dict(sections(src))
        question = plain(sec.get("题面", ""))
        answer = plain(sec.get("参考答案", "")) or plain(sec.get("完整解答", ""))
        expl = (plain(sec.get("逐步解析", "")) or plain(sec.get("解析", ""))
                or plain(sec.get("完整解答", "")))
        kp = (bullets(sec.get("评分要点", ""))[:5] or bullets(sec.get("评分细则", ""))[:5]
              or sentences(answer, 3))
        ce = bullets(sec.get("常见错答", ""))[:4] or ["把指标没涨直接归因于方法没用", "只报宏平均不报最弱域"]
        rubric = (plain(sec.get("评分要点", ""))[:200] or plain(sec.get("评分细则", ""))[:200]
                  or "满分 10：结论 3 分；机制 4 分；边界 2 分；表达 1 分")
        if len(answer) < 15 or len(expl) < 25:
            skip = ("题面", "评分", "评分细则", "追问", "常见错答", "层级")
            bodies = [(k, plain(v)) for k, v in sections(src)
                      if k not in skip and len(plain(v)) >= 80]
            if bodies:
                answer = answer or bodies[0][1][:300]
                expl = expl or (bodies[1][1] if len(bodies) > 1 else bodies[0][1])
                kp = kp if len(kp) >= 2 else sentences(expl, 3)
        hdr = re.search(r"主论文\*\*：(.+)", src[:900])
        pid = match_paper(hdr.group(1), papers) if hdr else None
        pid = pid or CH_PAPER[(ch - 1) % len(CH_PAPER)]
        item = {
            "id": "q%02d-%s" % (ch, no.lower()), "level": LEVEL_BY_SUFFIX.get(suffix, 2),
            "module": "paper", "ref": pid, "question": question or topic,
            "answer": answer, "explanation": expl, "key_points": kp,
            "common_errors": ce, "rubric": rubric,
            "long_html": _assess_dedup(md2html(src)),
        }
        if vis(item["long_html"]) < 500:
            item["long_html"] += _review_note(item)
        out.append(item)
    # 2) 600 道长答：题目 + 一句话答案 + 机制拆解 + 反例清单
    for fp in sorted(glob.glob(os.path.join(CORPUS, "docs/longanswers/L*.md"))):
        src = md_file(fp)
        h1 = re.match(r"#\s+(.+)", src).group(1)
        m = re.match(r"长答\s*(\d+)-(\d+)", h1)
        m2 = re.match(r"综合答辩\s*(\d+)", h1)
        if m:
            ch, no = int(m.group(1)), m.group(2)
        elif m2:
            ch, no = int(m2.group(1)), "99"
        else:
            ch, no = 1, "01"
        sec = dict(sections(src))
        question = plain(sec.get("1. 题目", ""))
        answer = plain(sec.get("2. 一句话答案", ""))
        expl = (plain(sec.get("5. 机制拆解", "")) or plain(sec.get("3. 为什么问这个", ""))
                or plain(sec.get("3. 八分钟主线", "")))
        # 关键知识点用「五个追问」，常见错误用「反例清单」；旧实现两处都取反例清单，
        # 同一张卡里会出现两遍完全相同的五条。
        kp = (bullets(sec.get("10. 面试追问", ""))[:5]
              or bullets(sec.get("4. 五个追问", ""))[:5]
              or sentences(expl, 3))
        ce = bullets(sec.get("8. 反例清单", ""))[:4] or ["只背结论，不检查边界", "把相关性当成因果"]
        rubric = plain(sec.get("9. 工程落地", ""))[:200] or "满分 10：结论 3 分；机制 4 分；边界 2 分；表达 1 分"
        suffix = h1.split("·")[-1].strip() if "·" in h1 else "calc"
        item = {
            "id": "l%02d-%s" % (ch, no.lower()), "level": LEVEL_BY_SUFFIX.get(suffix, 3),
            "module": "paper", "ref": CH_PAPER[(ch - 1) % len(CH_PAPER)],
            "question": question or h1, "answer": answer, "explanation": expl,
            "key_points": kp, "common_errors": ce, "rubric": rubric,
            "long_html": _assess_dedup(md2html(src)),
        }
        if vis(item["long_html"]) < 500:
            item["long_html"] += _review_note(item)
        out.append(item)
    # 3) 补卡：为没有 Q 文件的 10 篇论文各写一张（content/extra_assess.py 产出）
    extra = os.path.join(DATA, "extra_assess.json")
    if os.path.exists(extra):
        with open(extra, encoding="utf-8") as f:
            extra_qs = json.load(f)
        for q in extra_qs:
            q["long_html"] = _assess_dedup(q.get("long_html", ""))
            if vis(q["long_html"]) < 500:
                q["long_html"] += _review_note(q)
        out.extend(extra_qs)
    return out


def build_book():
    mods = sorted(glob.glob(os.path.join(CORPUS, "docs/modules/*.md")))
    book_md = md_file(os.path.join(CORPUS, "book.md"))
    # 按 `## NN 标题` 切出 24 章（书稿叙事层）
    parts = re.split(r"^##\s+(\d\d)\s+(.+)$", book_md, flags=re.M)
    narr = {}
    for i in range(1, len(parts), 3):
        narr[parts[i]] = "## %s %s\n" % (parts[i], parts[i + 1]) + (parts[i + 2] if i + 2 < len(parts) else "")
    secs = []
    for idx, fp in enumerate(mods):
        no = "%02d" % (idx + 1)
        src = md_file(fp)
        h1 = re.match(r"#\s+第\s*(\d+)\s*章\s*·\s*(.+?)（(.+?)）", src)
        title, en = (h1.group(2).strip(), h1.group(3).strip()) if h1 else ("第 %s 章" % no, "")
        html = _dedup_li(dedup_paras(md2html(narr.get(no, "")) + "\n\n" + md2html(src)))
        secs.append({"id": "ch" + no, "label": "第 %s 章" % no, "title": title,
                     "en": en, "html": html})
    return {
        "title": "四个师傅和一辆抖动的车",
        "subtitle": "MOPD 多教师蒸馏 · 二十四章",
        "note": "全书 24 章，每章由叙事层（书稿）与技术深读（module）两层组成；先读故事，再读深读。",
        "story_map": {s["id"]: ["story-four-masters"] for s in secs},
        "sections": secs,
    }


def _wrap_terms(h):
    """把 880 条术语各自收进折叠块：先看术语目录，点开再看定义/误用/记法。"""
    ms = list(re.finditer(r"<h3>\s*(G\d{4})\s*·\s*([^<]+)</h3>", h))
    if not ms:
        return h
    out, pos = [], 0
    for i, m in enumerate(ms):
        end = ms[i + 1].start() if i + 1 < len(ms) else len(h)
        out.append(h[pos:m.start()])
        out.append('<details class="term"><summary>%s · %s</summary>\n%s\n</details>'
                   % (m.group(1), m.group(2).strip(), h[m.end():end]))
        pos = end
    out.append(h[pos:])
    return "".join(out)


def build_appendix():
    parts = []
    g = md_file(os.path.join(CORPUS, "docs/glossary.md"))
    gh = md2html(g)
    # 每条术语末尾的「6. 相关条目」都是同一句 docs/ 路径，880 条重复；
    # 删掉逐条小节，改成卷首一句总说明。
    gh = _drop_h3(gh, "6. 相关条目")
    # 每条术语头部的「相关：见本节末尾的链接」也是 880 条同一句，删掉
    gh = re.sub(r"<li><strong>相关</strong>：见本节末尾的链接</li>\s*", "", gh)
    gh = ('<p class="lead">术语的延伸阅读：同章术语见 <code>docs/glossary.md</code>，'
          '理论卡见 <code>docs/reference/</code>，论文见 <code>docs/papers/</code>。'
          '下面每条只保留该术语自己的定义、误用与记法。</p>\n') + gh
    gh = _wrap_terms(gh)
    parts.append('<h3>附录 A · 术语表（MOPD 全量）</h3>\n' + gh)
    parts.append('<h3>附录 B · 工匠笔记（60 个现场案例）</h3>')
    for fp in sorted(glob.glob(os.path.join(CORPUS, "docs/cases/C*.md"))):
        src = md_file(fp)
        m = re.match(r"#\s+(.+)", src)
        title = html_lib.escape(m.group(1).strip(), quote=False) if m else os.path.basename(fp)
        # 案例标题原本被 md2html 的 drop_first_h1 丢掉，60 个案例只剩「1. 现场」；
        # 这里显式恢复标题，并把整案收进折叠块，先看目录、再展开单个案例。
        parts.append('<details class="case"><summary>%s</summary>\n%s\n</details>'
                     % (title, md2html(src)))
    return {"long_html": dedup_paras("\n\n".join(parts))}


def write(name, obj):
    os.makedirs(DATA, exist_ok=True)
    with open(os.path.join(DATA, name + ".json"), "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)
        f.write("\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--part", default="all")
    args = ap.parse_args()
    papers = build_papers()
    if args.part in ("all", "papers"):
        write("papers", papers)
        print("papers", len(papers), "vis", sum(vis(p["long_html"]) for p in papers))
    if args.part in ("all", "theory"):
        th = build_theory()
        write("theory", th)
        print("theory", len(th), "vis", sum(vis(t["long_html"]) for t in th))
    if args.part in ("all", "algos"):
        al = build_algos()
        write("algorithms", al)
        print("algorithms", len(al), "vis", sum(vis(a["long_html"]) for a in al))
    if args.part in ("all", "assess"):
        asm = build_assessments(papers)
        write("assessments", asm)
        print("assessments", len(asm), "vis", sum(vis(a["long_html"]) for a in asm))
    if args.part in ("all", "book"):
        bk = build_book()
        write("book", bk)
        print("book", len(bk["sections"]), "vis", sum(vis(s["html"]) for s in bk["sections"]))
    if args.part in ("all", "appendix"):
        apx = build_appendix()
        write("appendix", apx)
        print("appendix vis", vis(apx["long_html"]))


if __name__ == "__main__":
    main()
