# 多教师在线策略蒸馏（MOPD）· 领域研究与教学站

档位：**L2**　交付：2026-11-13　目录：`/home/whu/workspace/ai_workspace/mopd-teaching-20261113`

在线：**https://zhangjianbang-nb.github.io/mopd-teaching/**（GitHub Pages）　仓库：**https://github.com/zhangjianbang-nb/mopd-teaching**

## 规模（正文可见字符口径）

| 模块 | 件数 | 可见正文 |
|---|---:|---:|
| 论文知识库 | 36 篇 | 276,482 |
| 实验与算法库 | 60 个 | 297,673 |
| 理论深入 | 58 张卡 | 172,650 |
| 考试与练习 | 1,126 题 | 3,806,663 |
| 全书 | 24 章 | 385,604 |
| 附录 | 1 卷 | 209,242 |
| 方向地图 | 8 个方向 | 19,105 |
| 入门故事 | 5 篇 | 5,335 |
| 总结/演进/领域/覆盖 | 4 份 | 6,441 |
| **合计** | | **5,179,195** |

- 下限 5,000,000，余量 179,195（**+3.6%**）。
- 2026-11-13 去重：论文/理论/算法/题库/附录/书章删掉与页面结构化字段逐字重复的段落与列表，正文从 688.8 万降到 517.9 万，仍高于下限。
- 口径：去 `<script>/<style>` → 标签直接删除（不插空格）→ 空白折叠 → strip；字段名不计。
- 每个内容单元 ≥500 字（`E-THIN`）；全站 ≥500 万字（`E-VOLUME`）。

## 视觉密度（2026-11-13 去重后实测）

| 模块 | 公式（页面渲染） | 表（带表头） | 内联 SVG 图 |
|---|---:|---:|---:|
| 论文 36 | 36（结构化 formula 字段） | 72 | 72 |
| 算法 60 | 60（结构化 formula 字段） | 192 | 60 |
| 理论 58 | 58 | 58 | 58 |
| 方向 8 | — | 8 | 8 |
| 故事 5 | — | — | 5 |
| 全书 24 章 | 69 | 71 | 6 |
| 附录 | — | 3 | 1 |
| 题库 1,126 | 576 | 216 | — |
| **合计** | **799** | **620** | **210** |

- 799 = 正文 `$$` 块 703 + 论文/算法结构化 `formula` 字段 96；两者都由页面 KaTeX 渲染。
- 图全部是**数据驱动示意图**：论文用 `pipeline` + `problem/core_idea/results`，算法用
  `flow`，理论用 `prereq` 反查，方向用 `question/core_tech/key_papers`，故事用
  `roles/plot/mapping`；图注写明"依据 XX 字段绘制，非论文原图"。
- 公式全部是 KaTeX 可渲染的 `$$...$$`；14 张理论卡的 Unicode 公式（θ/Σ/−/∼/⇒/⟨⟩）
  已转成 LaTeX 命令，运行时 `katex-error=0`。
- 闸门：`verify_site.py --phase all` 的 `E-VISUAL` / `E-FORMULA` / `E-VISUAL-TOTAL`。

## 2026-11-13 去重修复（用户令「修复多师蒸馏的调研 html」）

- **题库**：每张题卡曾把章节级的「逐步解析 / 代码锚点 / 数字核算 / 边界清单 / 评分细则 /
  追问 / 变体」整段塞进 `long_html`，与页面已渲染的答案/解析/评分表逐字重复。现在删掉
  页面已渲染的小节，只保留扩展内容并折进默认收起的 `<details class="long-extra">`；
  L 层「关键知识点」改用「10. 面试追问」，不再和「常见错误」同源。
- **论文/理论/算法**：`long_html` 第 1 节与第 2–8/10 节首块是页面结构化字段的同文复制，
  已按节删除；算法 `flow` 与页面「数据流」重复的列表也删除，保留点评、图与独有段落。
- **方向页**：同一论文的章节实验卡与 EP 复现卡 `idea` 相同，JS 按 `papers[0]` 去重并优先
  保留 EP 卡。
- **附录**：880 条术语原来全部展开（页高 49.6 万 px），现折进 `<details class="term">`；
  60 个工匠笔记补回被 `md2html` 丢掉的 H1 标题并折进 `<details class="case">`；删掉 880
  条「相关：见本节末尾的链接」空话；页高降到 49,353 px。
- **书章**：6.1–6.4 重复的「关键行」列表按 `<li>` 文本去重。
- **结果**：可见重复审计（`main p, main li` 归一化后计数）所有主路由 0 重复；题库卡片
  展开后 0 重复。

## 内容结构

- **11 个内容模块**（不含首页/领域总览）：方向地图、实验与算法库、论文知识库、算法演进、领域总结、全书 24 章、入门故事、理论深入、论文精读、考试与练习、附录。
- **5 篇故事**：旗舰《四个师傅和一辆抖动的车》（覆盖 24 章）+《夜班的录音机》《派单员的表格》《账房的算盘》《考场的三道门》。
- **8 个方向**：蒸馏目标、多教师路由、能力整合、长程 agent、教师资格、效率与系统、评测诊断、失败治理。
- **首页五层 SVG**：目标 → 采样 → 路由 → 预算 → 治理。
- **外部评审**：ChatGPT 对抗性评审 2026-11-13，全文 `research/chatgpt/review-20261113.txt`，处置 `decisions.md`。

## 怎么打开

```bash
# 方式一：直接双击 / file://（完全离线，KaTeX 在 site/vendor/）
file:///home/whu/workspace/ai_workspace/mopd-teaching-20261113/site/index.html

# 方式二：本地静态服务
cd /home/whu/workspace/ai_workspace/mopd-teaching-20261113
python3 -m http.server 8931
# http://127.0.0.1:8931/site/index.html
```

不访问任何 CDN，不依赖登录服务；学习进度只写本机 `localStorage`。

## 复现与验收

```bash
bash tools/verify_all.sh        # 6 步全链
python3 -I tools/ledger.py      # 正文账（5,179,195）
python3 -I tools/assert_all.py  # 75 项独立断言
node tools/smoke.js             # 20 条路由 + 交互 + 无外链
python3 -I tools/fig_dump_all.py && node tools/fig_probe.js shots/figtest-all.html  # 210 张图几何
node tools/visual_probe.js      # KaTeX/图/表运行时断言 + 截图
node tools/mobile_probe.js      # 390px 窄屏
node tools/shoot.js             # 5 张截图到 shots/
```

2026-11-13 实测：`verify_site --phase all` **0 errors / 0 warnings PASS**；ledger **5,179,195 PASS**；assert_all **75/75**；smoke **20/20**（题库 1,126 卡，答案展开 1,510 字，无 http(s) 请求）；fig_probe **210 张图 0 问题**；visual_probe **7 页 0 问题**；mobile_probe **5/5**；`verify_all.sh` **全部 PASS**。可见重复审计所有主路由 **0 重复**。

视觉：`shots/fix-final-paper.png`、`fix-final-exam.png`、`fix-final-appendix.png`、`fix-final-direction.png`、`fix-final-composite.png`，以及附录案例 `fix-appx-case2.png`；均已亲眼核对标题、正文、公式、图注与折叠状态。

## 目录

```
research/chatgpt/   外部评审全文 + 处置
content/            构建脚本（md2html / build_mopd / build_meta / extra_assess / add_visuals）
site/index.html     单页应用（内联 CSS/JS）
site/data/*.json    唯一真源；bundle.js 由 bundle_data.py 生成
site/vendor/katex/  本地 KaTeX
tools/              ledger / assert / smoke / fig_dump_all / fig_probe / visual_probe / mobile / shoot / verify_all
shots/              验收截图
```

## 已知边界

- 检索：Google Scholar 部分可用（验证码时退 Semantic Scholar/OpenAlex/DBLP）；YouTube 渠道 blocked，顶会 talk 未逐条核验。
- 36 篇中 31 篇全文精读、5 篇页面核验；数字来自论文表格或显式算术，**未复现实验**。
- 36 篇里有 7 篇长程 agent 论文与若干工业报告，属相邻技术，不全是 MOPD 的直接组成。
- 检索截止 2026-11-13；之后的预印本未收录。
- 题库由书稿/论文卡的程序化抽取与改写生成，覆盖五层，但不等于人工命题的等值难度。
- 未做打印分页优化，浏览器直接打印会得到连续长页。

## 禁止

- 空白卡片 / TODO 占位 / 假论文 / 假引用 / AI 生成图冒充论文原图
- 只跑断言不看截图就交付
- 总量不到 500 万字就交付 / 单页不到 500 字就上站
- 把「检索不到」写成「该领域没有」
