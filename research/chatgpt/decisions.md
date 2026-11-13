# 外部评审处置 · 2026-11-13

评审全文：`review-20261113.txt`（ChatGPT，对抗性评审，2026-11-13）。

## 采纳（已落到内容）

1. **年份口径统一**：论文年份一律取 arXiv 首次提交年，会议年份另见 `venue`；不把预印本年与会议年混排。已写入 `evolution.long_html` 的「年份口径与并行关系」段。
2. **区分直接研究与相邻技术**：36 篇里有一部分是 agent memory、harness、工业报告，属于相邻技术，不是 MOPD 的直接组成。已在 `coverage.long_html` 增加「哪些不是 MOPD 的直接组成」段，并保留方向标签。
3. **2026 年论文不是一条单链**：CA-MOPD、Open-MOPD、DivOPD、MemOPD 分别在修路由、预算、异步、状态对齐，存在并行关系。已在演进页加并行说明；图上已有 `parallel` 边。
4. **失败案例与性能论文同等重要**：第 18 章与附录 60 个案例专讲「什么时候不该蒸馏 / 为什么会掉域」；已在 `summary.long_html` 的「外部评审与边界」段明示。
5. **补基础理论对照**：ensemble distillation、parameter merging、gradient surgery 作为对照线，指向理论卡 T37（教师集成权重）、T51（序列级与 token 级）与第 11 章参数更新对照；本轮不另开章节。

## 驳回（附理由）

1. **「你只提供了 28 篇」**：实际发送 36 条论文记录，评审计数有误；以 `papers.json` 的 36 条为准。
2. **把文献库整体重排成 Core/Adjacent 审查矩阵**：方向标签已提供粗分，重排需要逐篇重读并改 schema，超出本轮范围；列为后续工作，不在交付里假装完成。
3. **新增六个专题章节**：需要新的检索与写作，本轮不扩章；已把「教师资格自动判定、跨域路由训练信号、容量缩放律、可回滚性」列在 `summary.open_problems` 与第 24 章清单。

## 遗留

- 评审建议的「36 篇审查矩阵（核心/关联/背景、前置论文、实验局限、是否精读）」尚未落盘为独立表；当前由 `papers.json` 的 direction/type/tier 与论文卡承担。
- 评审提到的「Policy Distillation / Sequence-level KD / Ensemble Distillation」原始论文未逐篇入 `papers.json`，只作为理论对照出现。
