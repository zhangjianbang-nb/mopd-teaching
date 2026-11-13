# 外部依赖说明

本站是静态单页应用，`index.html` 只读取本地 `data/bundle.js` 与 `vendor/katex/`，
双击即可打开（file:// 可用），**完全离线，不访问任何 CDN，不依赖登录服务**。

| 依赖 | 版本 | 用途 | 位置 | 离线行为 |
|---|---|---|---|---|
| KaTeX | 0.16.9 | 数学公式渲染 | `site/vendor/katex/`（内置 JS/CSS/字体） | 本地加载，无需网络 |
| 关系图 | 内置 SVG 渲染器 | 算法演进图（按 `evolution.edges` 自动布局） | `index.html` 内联 JS | 无第三方依赖 |
| 字体 | 系统字体 | 中文排版 | 无 | 使用系统 Noto/PingFang/雅黑 |

不依赖任何需要登录的外部服务；不上传任何数据。学习进度只写本机 `localStorage`。

## 更新 KaTeX

替换 `site/vendor/katex/` 下的同名文件即可（保持目录结构：`katex.min.js`、
`katex.min.css`、`contrib/auto-render.min.js`、`fonts/*.woff2`）。

## 关系图

不再使用 Mermaid。`evolution.json` 只需提供 `timeline` 与 `edges`，前端按五类关系
自动布局成 SVG；若关系边为空，页面显示"尚未录入关系边"。
