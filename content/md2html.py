# -*- coding: utf-8 -*-
"""Markdown → 站点 HTML（只用 p/h3/h4/ul/ol/table/formula/blockquote）。

约束（skill 硬规则）：
- 禁止 <pre>/<style>/<script>；代码块一律转 <div class="formula">…<br>…</div>。
- 标签直接删除式字数口径；本模块不负责计数，只负责产出干净 HTML。
- 同一单元内重复段落（前 60 字相同）只保留第一份。
"""
import html as H
import re

_CODE = re.compile(r"```([a-zA-Z0-9_+-]*)\n([\s\S]*?)```")
_INLINE_CODE = re.compile(r"`([^`\n]+)`")
_BOLD = re.compile(r"\*\*([^*\n]+)\*\*")
_ITALIC = re.compile(r"(?<![\w*])\*([^*\n]+)\*(?![\w*])")
_LINK = re.compile(r"\[([^\]]+)\]\((https?://[^)\s]+)\)")


def _inline(s):
    """行内格式：先转义，再套标签（数学 $...$ 原样保留给 KaTeX）。"""
    s = H.escape(s, quote=False)
    s = _LINK.sub(r'<a href="\2">\1</a>', s)
    s = _BOLD.sub(r"<strong>\1</strong>", s)
    s = _ITALIC.sub(r"<em>\1</em>", s)
    s = _INLINE_CODE.sub(r"<code>\1</code>", s)
    return s.replace("**", "")  # 跨行/嵌套导致未配对的 ** 直接去掉，不留字面量


def _formula(code):
    lines = [H.escape(x, quote=False) for x in code.rstrip("\n").split("\n")]
    return '<div class="formula">' + "<br>".join(lines) + "</div>"


def _table(lines):
    rows = []
    for ln in lines:
        cells = [c.strip() for c in ln.strip().strip("|").split("|")]
        if all(re.fullmatch(r":?-{2,}:?", c or "-") for c in cells):
            continue
        rows.append(cells)
    if not rows:
        return ""
    head = rows[0]
    body = rows[1:]
    out = ['<div class="table-wrap"><table class="mini">', "<thead><tr>"]
    out += ["<th>%s</th>" % _inline(c) for c in head]
    out.append("</tr></thead><tbody>")
    for r in body:
        out.append("<tr>" + "".join("<td>%s</td>" % _inline(c) for c in r) + "</tr>")
    out.append("</tbody></table></div>")
    return "\n".join(out)


def _list(lines, ordered):
    tag = "ol" if ordered else "ul"
    out = ["<%s>" % tag]
    for ln in lines:
        txt = re.sub(r"^\s*(?:[-*+]|\d+\.)\s+", "", ln)
        out.append("<li>%s</li>" % _inline(txt))
    out.append("</%s>" % tag)
    return "\n".join(out)


def md2html(md, drop_first_h1=True):
    md = md.replace("\r\n", "\n")
    # 保护代码块（先换成占位符，避免被段落逻辑拆散）
    codes = []

    def stash(m):
        codes.append(m.group(2))
        return "\n\n@@CODE%d@@\n\n" % (len(codes) - 1)

    md = _CODE.sub(stash, md)
    lines = md.split("\n")
    out = []
    seen = set()
    i = 0
    n = len(lines)
    dropped_h1 = False

    def emit_para(buf):
        if not buf:
            return
        txt = " ".join(x.strip() for x in buf).strip()
        if not txt:
            return
        key = re.sub(r"<[^>]+>", "", _inline(txt))[:60]
        if key in seen:
            return
        seen.add(key)
        out.append("<p>%s</p>" % _inline(txt))

    para = []
    while i < n:
        ln = lines[i]
        s = ln.strip()

        if s.startswith("@@"):
            emit_para(para); para = []
            idx = int(re.search(r"@@CODE(\d+)@@", s).group(1))
            out.append(_formula(codes[idx]))
            i += 1
            continue

        if not s:
            emit_para(para); para = []
            i += 1
            continue

        m = re.match(r"^(#{1,6})\s+(.*)$", s)
        if m:
            emit_para(para); para = []
            level = len(m.group(1))
            title = m.group(2).strip()
            if level == 1 and drop_first_h1 and not dropped_h1:
                dropped_h1 = True  # 页面模板已渲染 h1，源稿的一级标题丢弃
                i += 1
                continue
            tag = "h3" if level <= 2 else ("h4" if level == 3 else "h5")
            out.append("<%s>%s</%s>" % (tag, _inline(title), tag))
            i += 1
            continue

        if s.startswith("|"):
            emit_para(para); para = []
            tbl = []
            while i < n and lines[i].strip().startswith("|"):
                tbl.append(lines[i]); i += 1
            out.append(_table(tbl))
            continue

        if re.match(r"^\s*[-*+]\s+", ln) or re.match(r"^\s*\d+\.\s+", ln):
            emit_para(para); para = []
            ordered = bool(re.match(r"^\s*\d+\.\s+", ln))
            items = []
            while i < n:
                cur = lines[i]
                if re.match(r"^\s*[-*+]\s+", cur) or re.match(r"^\s*\d+\.\s+", cur):
                    items.append(cur); i += 1
                elif cur.strip() == "":
                    break
                elif cur.startswith(("  ", "\t")) and items:
                    items[-1] += " " + cur.strip(); i += 1
                else:
                    break
            out.append(_list(items, ordered))
            continue

        if s.startswith(">"):
            emit_para(para); para = []
            quote = []
            while i < n and lines[i].strip().startswith(">"):
                quote.append(lines[i].strip()[1:].strip()); i += 1
            out.append("<blockquote>%s</blockquote>" % _inline(" ".join(quote)))
            continue

        para.append(ln)
        i += 1

    emit_para(para)
    return "\n\n".join(out)


def section(md, title):
    """取 `## <title>` 到下一个 `## ` 之间的正文（不含标题）。"""
    m = re.search(r"^##\s+%s\s*$" % re.escape(title), md, re.M)
    if not m:
        return ""
    start = m.end()
    nxt = re.search(r"^##\s+", md[start:], re.M)
    end = start + nxt.start() if nxt else len(md)
    return md[start:end].strip()


def sections(md):
    """按 `## ` 切节：返回 [(标题, 正文)]。"""
    parts = re.split(r"^##\s+", md, flags=re.M)[1:]
    out = []
    for p in parts:
        lines = p.split("\n", 1)
        out.append((lines[0].strip(), lines[1] if len(lines) > 1 else ""))
    return out


def plain(md):
    """取纯文本（去标记/代码/公式），用于填短字段。"""
    t = _CODE.sub("", md)
    t = re.sub(r"\$\$[\s\S]*?\$\$", "", t)
    t = re.sub(r"`[^`\n]+`", "", t)
    t = re.sub(r"^#{1,6}\s+", "", t, flags=re.M)
    t = re.sub(r"^\s*[-*+]\s+", "", t, flags=re.M)
    t = re.sub(r"^\s*\d+\.\s+", "", t, flags=re.M)
    t = t.replace("|", " ").replace("**", "").replace("*", "")
    return re.sub(r"\s+", " ", t).strip()


def dedup_paras(html):
    """跨多次 md2html 拼接后的全局段落去重：同一单元内前 60 字相同的 <p> 只留第一份。"""
    seen = set()
    parts = re.split(r"(<p>[\s\S]*?</p>)", html)
    out = []
    for part in parts:
        if part.startswith("<p>"):
            key = re.sub(r"<[^>]+>", "", part)[:60]
            if key in seen:
                continue
            seen.add(key)
        out.append(part)
    return "".join(out)
