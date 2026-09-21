#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把需求规格说明书 Markdown 转换为符合 V10.0 交付要求的单文件 HTML。

特性：
    - 顶栏常驻文档标题 / 版本标签 / 需求来源与「导出 PDF」按钮
    - 左侧「一级 → 二级 → 三级」可折叠目录树（自动生成，逐级折叠、全部展开/折叠）
    - 目录滚动定位：高亮当前章节并自动展开其祖先，长文档随时知道身处何处
    - 稳定短锚点：第N部分→pN、9.13.1→s9-13-1、附录A→ap-a（改标题不失效）
    - 章节卡片式排版；宽表自动保底宽度（横向滚动而不是把中文挤成竖排）、数字列右对齐
    - 稳定编号自动着色为胶囊：FUNC/Q/REP 蓝、B/B-APP 绿、REF/INV/R 黄、ROLE/PROC 灰
    - 状态标记自动着色：[已确认] 绿、[AI自动补全] 蓝、[待确认] 橙
    - ```html 围栏与裸 HTML 块原样透传，用于装配静态界面原型（.mock 样式库内置）
    - Mermaid 图三种方式：默认 CDN 异步加载；`--mermaid inline` 把 mermaid 库整段内联（交付件自包含、离线也渲染）；`--mermaid off` 仅保留源码。
      三者都带失败降级（保留源码 + 明示提示），深浅主题各配一套配色
    - 若正文没有 ```mermaid 代码块，`inline` 模式不会注入库（避免无谓增大体积）
    - 打印 / 导出 PDF 友好（自动隐藏顶栏与侧栏、取消宽表保底宽度）

用法：
    python md_to_requirement_html.py 需求规格说明书-销售合同执行管理.md
    python md_to_requirement_html.py 输入.md -o 输出.html --theme dark --title "某系统需求规格说明书"
    python md_to_requirement_html.py 输入.md --mermaid off      # 离线环境不引入 CDN
    python md_to_requirement_html.py 输入.md --mermaid inline   # 把 mermaid 库内联：自包含、离线也渲染成图
    python md_to_requirement_html.py 输入.md --mermaid inline --mermaid-lib /path/to/mermaid.min.js
    python md_to_requirement_html.py 输入.md --version V10.4 --meta "需求来源：《合同需求.txt》"

`--mermaid inline` 需要一份 mermaid.min.js，按以下顺序查找：
    1) 命令行 `--mermaid-lib`
    2) 环境变量 `MERMAID_JS_PATH`
    3) `~/.workbuddy/vendor/mermaid.min.js`
    4) 当前工作目录下的 `mermaid.min.js`
获取方式（一次即可，之后所有文档共用）：
    curl -sL -o ~/.workbuddy/vendor/mermaid.min.js \\
      https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.min.js

仅使用标准库，无需安装依赖。
"""
import argparse
import html
import os
import re
import sys
from pathlib import Path

# ---------------------------------------------------------------- 行内与行级解析

_CODE_SPAN = re.compile(r"`([^`]+)`")
_LINK = re.compile(r"\[([^\]]+)\]\(([^)\s]+)\)")
_BOLD = re.compile(r"\*\*([^*]+)\*\*")
_ITALIC = re.compile(r"(?<!\*)\*([^*\n]+)\*(?!\*)")
_STATUS = {
    "[已确认]": "s-ok",
    "[AI自动补全]": "s-ai",
    "[待确认]": "s-todo",
}

# 稳定编号自动 chip 化：把裸文本编号渲染为彩色胶囊，便于在长表格中快速定位。
# 分色语义：蓝=业务能力 绿=系统自动行为/审批 黄=规则约束 灰=主体与流程
_ID_TOKEN = re.compile(
    r"(?<![\w\-/])((?:B-APP|PROC-APP|FUNC|ROLE|REF|INV|REP|APR|PROC|GW|R|Q|B)-\d{1,3})(?![\w\-])"
)
_ID_CLS = {
    "B-APP": "g", "PROC-APP": "g", "APR": "g", "B": "g",
    "REF": "y", "INV": "y", "R": "y",
    "ROLE": "n", "PROC": "n", "GW": "n", "Q": "n",
}


def _id_chip(m: re.Match) -> str:
    tok = m.group(1)
    if tok.startswith("B-APP") or tok.startswith("PROC-APP"):
        key = tok.split("-")[0] + "-APP"
    else:
        key = tok.split("-")[0]
    cls = _ID_CLS.get(key, "")
    return f'<span class="id{" " + cls if cls else ""}">{tok}</span>'


_CN_DIGIT = {"零": 0, "一": 1, "二": 2, "三": 3, "四": 4, "五": 5,
             "六": 6, "七": 7, "八": 8, "九": 9}


def _cn2int(s: str) -> int:
    """中文数字转整数，覆盖「一」到「九十九」的常见写法。"""
    if "十" not in s:
        return _CN_DIGIT.get(s, 0)
    if s.startswith("十"):
        return 10 + _CN_DIGIT.get(s[1:], 0)
    a, _, b = s.partition("十")
    return _CN_DIGIT.get(a, 1) * 10 + (_CN_DIGIT.get(b, 0) if b else 0)


def _slug(text: str, used: dict) -> str:
    """结构化短锚点：优先用章节编号，稳定、简短、跨版本可分享。

    - 「第九部分 UI 原型」   → p9
    - 「9.13.1 UI 界面说明」 → s9-13-1
    - 「附录 A 术语表」      → ap-a
    - 无编号标题             → 回退到标题文本 slug（中文保留）
    """
    t = text.strip()
    base = ""

    m = re.match(r"^第\s*([一二三四五六七八九十零]+)\s*[部章]", t)
    if m:
        base = "p" + str(_cn2int(m.group(1)))

    if not base:
        m = re.match(r"^(\d+(?:\.\d+)+)", t)
        if m:
            base = "s" + m.group(1).replace(".", "-")

    if not base:
        m = re.match(r"^附录\s*([A-Za-z])", t)
        if m:
            base = "ap-" + m.group(1).lower()

    if not base:
        m = re.match(r"^(\d+)\s*[\.、\s]", t)
        if m:
            base = "s" + m.group(1)

    if not base:
        base = re.sub(r"[^\w\u4e00-\u9fff]+", "-", t).strip("-").lower()[:60] or "sec"

    n = used.get(base, 0)
    used[base] = n + 1
    return base if n == 0 else f"{base}-{n}"


def inline(text: str) -> str:
    """行内元素渲染。先转义，再处理 code / 链接 / 粗斜体 / 状态标记 / 编号胶囊。"""
    out = html.escape(text, quote=False)
    spans: list[str] = []

    def _stash(m):
        spans.append(m.group(1))
        return f"\x00{len(spans) - 1}\x00"

    out = _CODE_SPAN.sub(_stash, out)
    out = _LINK.sub(r'<a href="\2" target="_blank" rel="noopener">\1</a>', out)
    out = _BOLD.sub(r"<strong>\1</strong>", out)
    out = _ITALIC.sub(r"<em>\1</em>", out)
    for tag, cls in _STATUS.items():
        out = out.replace(tag, f'<span class="tag {cls}">{tag}</span>')
    out = _ID_TOKEN.sub(_id_chip, out)
    out = re.sub(r"\x00(\d+)\x00", lambda m: f"<code>{spans[int(m.group(1))]}</code>", out)
    return out


def _is_table_sep(line: str) -> bool:
    return bool(re.match(r"^\s*\|?[\s:|-]+\|[\s:|-]*$", line)) and "-" in line


def _split_row(line: str) -> list[str]:
    line = line.strip()
    if line.startswith("|"):
        line = line[1:]
    if line.endswith("|"):
        line = line[:-1]
    return [c.strip() for c in line.split("|")]


def parse_blocks(text: str):
    """把 Markdown 拆成块：heading / para / ul / ol / table / code / quote / hr。"""
    lines = text.splitlines()
    blocks, i, n = [], 0, len(lines)

    while i < n:
        line = lines[i]

        if line.startswith("```"):
            lang = line[3:].strip().lower()
            i += 1
            buf = []
            while i < n and not lines[i].startswith("```"):
                buf.append(lines[i])
                i += 1
            i += 1
            blocks.append({"t": "code", "lang": lang, "body": "\n".join(buf)})
            continue

        m = re.match(r"^(#{1,6})\s+(.*)$", line)
        if m:
            blocks.append({"t": "h", "level": len(m.group(1)), "text": m.group(2).strip()})
            i += 1
            continue

        if re.match(r"^\s*([-*_])\s*\1\s*\1[\s\1]*$", line) or line.strip() in ("---", "***", "___"):
            blocks.append({"t": "hr"})
            i += 1
            continue

        if line.lstrip().startswith(">") and line.strip():
            buf = []
            while i < n and (lines[i].lstrip().startswith(">") or (lines[i].strip() == "" and i + 1 < n and lines[i + 1].lstrip().startswith(">"))):
                buf.append(re.sub(r"^\s*>\s?", "", lines[i]))
                i += 1
            blocks.append({"t": "quote", "body": "\n".join(buf)})
            continue

        if line.strip().startswith("|") and i + 1 < n and _is_table_sep(lines[i + 1]):
            rows = [_split_row(line)]
            i += 2
            while i < n and lines[i].strip().startswith("|"):
                rows.append(_split_row(lines[i]))
                i += 1
            blocks.append({"t": "table", "rows": rows})
            continue

        if re.match(r"^\s*[-*+]\s+", line):
            buf = []
            while i < n and re.match(r"^\s*[-*+]\s+", lines[i]):
                buf.append(re.sub(r"^\s*[-*+]\s+", "", lines[i]))
                i += 1
            blocks.append({"t": "ul", "items": buf})
            continue

        if re.match(r"^\s*\d+[.)]\s+", line):
            buf = []
            while i < n and re.match(r"^\s*\d+[.)]\s+", lines[i]):
                buf.append(re.sub(r"^\s*\d+[.)]\s+", "", lines[i]))
                i += 1
            blocks.append({"t": "ol", "items": buf})
            continue

        if not line.strip():
            i += 1
            continue

        # Markdown 原生 HTML 块：以 < 开头且自成一体的连续非空行，原样透传
        # （用于 <p class="fig-cap">…</p>、<div class="mock">…</div> 等直接内嵌的片段）
        if line.lstrip().startswith("<") and not line.lstrip().startswith("<!"):
            buf = []
            while i < n and lines[i].strip():
                buf.append(lines[i])
                i += 1
            blocks.append({"t": "raw", "body": "\n".join(buf)})
            continue

        buf = []
        while i < n and lines[i].strip() and not re.match(r"^(#{1,6}\s|```|\s*[-*+]\s|\s*\d+[.)]\s|\s*>|\s*\|)", lines[i]):
            buf.append(lines[i].strip())
            i += 1
        if buf:
            blocks.append({"t": "para", "body": " ".join(buf)})
        else:
            i += 1
    return blocks


# ---------------------------------------------------------------- 渲染

_NUM_CELL = re.compile(
    r"^[¥￥$]?\s*-?[\d,]+(?:\.\d+)?\s*(?:元|万元|亿元|%|人|天|次|条|行|个|个月)?$"
)


def _table_html(rows) -> str:
    """表格渲染：按列数自动给保底宽度（宽表横向滚动而不是被压扁），数字列右对齐。"""
    rows = [list(r) for r in rows if any((c or "").strip() for c in r)]
    if not rows:
        return ""
    nc = max(len(r) for r in rows)
    rows = [r + [""] * (nc - len(r)) for r in rows]

    numcols: set[int] = set()
    if nc > 2:
        for ci in range(nc):
            vals = [r[ci].strip() for r in rows[1:] if r[ci].strip()]
            if len(vals) >= 2 and all(
                _NUM_CELL.match(v.replace("**", "")) for v in vals
            ):
                numcols.add(ci)

    cls = ' class="wide"' if nc >= 8 else (' class="mid"' if nc >= 5 else "")

    def cell(tag: str, c: str, ci: int) -> str:
        k = ' class="num"' if ci in numcols else ""
        return f"<{tag}{k}>{inline(c)}</{tag}>"

    head = "".join(cell("th", c, i) for i, c in enumerate(rows[0]))
    body = "".join(
        "<tr>" + "".join(cell("td", c, i) for i, c in enumerate(r)) + "</tr>"
        for r in rows[1:]
    )
    return f'<div class="tw"><table{cls}><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div>'


def render_body(blocks, used_slugs) -> tuple[str, list]:
    """渲染正文；h1 / h2 自动切分为卡片（.sec），与交付基准版式一致。"""
    headings: list[dict] = []
    sections: list[str] = []
    buf: list[str] = []

    def flush():
        if buf:
            sections.append('<section class="sec">\n' + "\n".join(buf) + "\n</section>")
            buf.clear()

    for b in blocks:
        t = b["t"]
        if t == "h":
            lvl, text = b["level"], b["text"]
            if lvl <= 2:
                flush()
            sid = _slug(text, used_slugs)
            headings.append({"level": lvl, "text": text, "id": sid})
            buf.append(f'<h{lvl} id="{sid}">{inline(text)}</h{lvl}>')
            continue
        if t == "para":
            buf.append(f"<p>{inline(b['body'])}</p>")
        elif t == "ul":
            buf.append("<ul>" + "".join(f"<li>{inline(x)}</li>" for x in b["items"]) + "</ul>")
        elif t == "ol":
            buf.append("<ol>" + "".join(f"<li>{inline(x)}</li>" for x in b["items"]) + "</ol>")
        elif t == "quote":
            inner = "".join(f"<p>{inline(x)}</p>" for x in b["body"].splitlines() if x.strip())
            buf.append(f"<blockquote>{inner}</blockquote>")
        elif t == "hr":
            buf.append("<hr>")
        elif t == "raw":
            buf.append(b["body"])
        elif t == "table":
            buf.append(_table_html(b["rows"]))
        elif t == "code":
            if b["lang"] == "mermaid":
                buf.append(
                    '<div class="mermaid-wrap">'
                    f'<pre class="mermaid">{html.escape(b["body"])}</pre>'
                    "</div>"
                )
            elif b["lang"] in ("html", "raw"):
                # 界面原型 / 任意原始 HTML 片段：原样透传，用于装配合规的静态界面原型
                buf.append(b["body"])
            else:
                cls = f' class="lang-{html.escape(b["lang"])}"' if b["lang"] else ""
                buf.append(f"<pre><code{cls}>{html.escape(b['body'])}</code></pre>")

    flush()
    return "\n".join(sections), headings


def render_toc(headings) -> str:
    """只取 1~4 级标题构造三级可折叠目录树（h1 展开、h2/h3 折叠，h4 为叶子）。"""
    roots, stack = [], []
    for h in headings:
        if h["level"] > 4:
            continue
        node = {"self": h, "children": []}
        while stack and stack[-1]["self"]["level"] >= h["level"]:
            stack.pop()
        (stack[-1]["children"] if stack else roots).append(node)
        stack.append(node)

    def walk(nodes, depth):
        if depth > 3:
            return ""
        html_parts = []
        for nd in nodes:
            h = nd["self"]
            raw = h["text"]
            short = raw if len(raw) <= 30 else raw[:29] + "…"
            label = (
                f'<span class="lv lv{h["level"]}">L{h["level"]}</span>'
                f'<a href="#{h["id"]}" title="{html.escape(raw, quote=True)}">{inline(short)}</a>'
            )
            if depth <= 2 and nd["children"]:
                html_parts.append(
                    f'<li class="br"><details{" open" if depth == 1 else ""}>'
                    f"<summary>{label}</summary>"
                    f'<ul>{walk(nd["children"], depth + 1)}</ul></details></li>'
                )
            else:
                html_parts.append(f'<li class="leaf lv{h["level"]}">{label}</li>')
        return "".join(html_parts)

    return "<ul>" + walk(roots, 1) + "</ul>"


# ---------------------------------------------------------------- 模板

CSS = """
:root{
 --bg:#f5f6f8; --card:#ffffff; --ink:#1d2026; --sub:#5b6270; --line:#e3e6ec;
 --brand:#006393; --accent:#CC0000; --head:#f0f3f7; --zebra:#fafbfd;
 --side:#ffffff; --hh:48px;
 /* 编号胶囊配色（查得到、看得清，不喧宾夺主） */
 --id-bg:#eff6ff; --id-ink:#1e40af; --id-line:#dbeafe;
 --id-bg-g:#dcfce7; --id-ink-g:#166534; --id-line-g:#bbf7d0;
 --id-bg-y:#fef9c3; --id-ink-y:#854d0e; --id-line-y:#fde68a;
 --id-bg-n:#f1f5f9; --id-ink-n:#475569; --id-line-n:#e2e8f0;
}
html[data-theme="dark"]{
 --bg:#0f1319; --card:#161b22; --ink:#e8ecf2; --sub:#9aa4b2; --line:#28303b;
 --brand:#4cc2ff; --accent:#ff6b6b; --head:#1d2430; --zebra:#141a22; --side:#111721;
 --id-bg:#16283f; --id-ink:#8fc3ff; --id-line:#24405f;
 --id-bg-g:#122c1e; --id-ink-g:#7ee2a8; --id-line-g:#1f4634;
 --id-bg-y:#33280c; --id-ink-y:#f2cf6b; --id-line-y:#4d3c12;
 --id-bg-n:#1c232e; --id-ink-n:#a9b4c2; --id-line-n:#2b3440;
}
*{box-sizing:border-box}
::-webkit-scrollbar{width:9px;height:9px}
::-webkit-scrollbar-thumb{background:#c7cdd8;border-radius:9px}
::-webkit-scrollbar-thumb:hover{background:#aab3c2}
::-webkit-scrollbar-track{background:transparent}
html[data-theme="dark"] ::-webkit-scrollbar-thumb{background:#333d4b}

/* ---------- 顶栏（文档元信息常驻可见，打印时隐藏） ---------- */
.topbar{position:sticky;top:0;z-index:50;height:var(--hh);display:flex;align-items:center;
 justify-content:space-between;gap:16px;padding:0 18px;background:#0f2a3f;color:#fff}
.topbar .left{display:flex;align-items:center;gap:12px;min-width:0}
.topbar .title{font-weight:700;font-size:14px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.topbar .vtag{font-size:11.5px;padding:1px 8px;border-radius:10px;background:rgba(255,255,255,.16);
 border:1px solid rgba(255,255,255,.25);white-space:nowrap}
.topbar .right{display:flex;align-items:center;gap:14px;font-size:11.5px;color:rgba(255,255,255,.72);
 white-space:nowrap;overflow:hidden}
.topbar .right .meta{overflow:hidden;text-overflow:ellipsis}
.tb-btn{cursor:pointer;font-family:inherit;font-size:12px;padding:4px 13px;border-radius:20px;
 background:transparent;border:1px solid rgba(255,255,255,.32);color:#fff}
.tb-btn:hover{background:rgba(255,255,255,.14)}
html{scroll-behavior:smooth}
body{margin:0;background:var(--bg);color:var(--ink);
 font-family:-apple-system,"Segoe UI","Microsoft YaHei",system-ui,sans-serif;
 font-size:15px;line-height:1.75;}
#wrap{display:flex;align-items:flex-start;min-height:calc(100vh - var(--hh))}
#side{width:320px;flex:0 0 320px;position:sticky;top:var(--hh);height:calc(100vh - var(--hh));
 overflow:auto;background:var(--side);border-right:1px solid var(--line);padding:14px 12px 60px}
#side .brand{font-weight:700;font-size:15px;color:var(--brand);margin:0 0 4px}
#side .hint{color:var(--sub);font-size:12px;margin:0 0 12px}
#side .tools{display:flex;gap:8px;margin-bottom:12px;flex-wrap:wrap}
#side button{cursor:pointer;border:1px solid var(--line);background:var(--card);color:var(--sub);
 border-radius:6px;font-size:12px;padding:4px 9px}
#side button:hover{color:var(--brand);border-color:var(--brand)}
#toc ul{list-style:none;margin:0;padding-left:12px}
#toc>ul{padding-left:0}
#toc li{list-style:none;margin:0}
#toc details>summary{cursor:pointer;list-style:none;display:flex;gap:6px;align-items:baseline;
 padding:3px 4px;border-radius:5px}
#toc li.br>details>summary{font-weight:600}
#toc details>summary::-webkit-details-marker{display:none}
#toc details>summary:hover,#toc li.leaf:hover{background:var(--head)}
#toc li.leaf{display:flex;gap:6px;align-items:baseline;padding:3px 4px;border-radius:5px}
#toc a{color:var(--ink);text-decoration:none;font-size:13px;flex:1;
 white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
#toc a:hover{color:var(--brand)}
#toc a.active{color:var(--brand);font-weight:700}
#toc li.leaf.active,#toc details>summary.active{background:var(--head)}
#toc .lv{font-size:10px;color:var(--sub);border:1px solid var(--line);border-radius:3px;
 padding:0 3px;flex:0 0 auto;opacity:.75}
#main{flex:1 1 auto;min-width:0;padding:22px 34px 80px}
main{max-width:1440px;margin:0 auto}
/* 章节卡片：每个一级 / 二级标题自成一张卡 */
.sec{background:var(--card);border:1px solid var(--line);border-radius:10px;
 padding:20px 24px;margin-bottom:16px}
.sec>h1:first-child,.sec>h2:first-child{margin-top:0}
.sec>hr:last-child{margin-bottom:0;border-top:none}
h1,h2,h3,h4{font-family:Georgia,"Songti SC","SimSun",serif;line-height:1.35;
 scroll-margin-top:calc(var(--hh) + 14px)}
h1{font-size:26px;margin:34px 0 14px;padding-bottom:10px;border-bottom:2px solid var(--brand)}
h1:first-child{margin-top:0}
h2{font-size:21px;margin:28px 0 12px;padding-left:11px;border-left:4px solid var(--brand)}
h3{font-size:17px;margin:22px 0 10px;color:var(--brand)}
h4{font-size:15px;margin:18px 0 8px}
p{margin:9px 0}
a{color:var(--brand)}
code{background:var(--head);border:1px solid var(--line);border-radius:4px;
 padding:1px 5px;font-size:13px;font-family:Consolas,"Courier New",monospace}
pre{background:var(--head);border:1px solid var(--line);border-radius:8px;padding:13px 15px;overflow:auto}
pre code{background:none;border:none;padding:0;font-size:13px}
blockquote{margin:12px 0;padding:10px 15px;background:var(--zebra);border-left:4px solid var(--brand);
 border-radius:0 8px 8px 0;color:var(--sub)}
blockquote p{margin:4px 0}
hr{border:none;border-top:1px dashed var(--line);margin:26px 0}
ul,ol{margin:8px 0;padding-left:24px}
li{margin:4px 0}
.tw{overflow:auto;margin:13px 0;border:1px solid var(--line);border-radius:8px;background:var(--card)}
table{border-collapse:collapse;width:100%;font-size:13.5px}
/* 宽表保底宽度：列多时横向滚动，而不是把中文挤成竖排 */
table.mid{min-width:900px}
table.wide{min-width:1180px}
th,td{border-bottom:1px solid var(--line);border-right:1px solid var(--line);
 padding:8px 10px;text-align:left;vertical-align:top}
th{background:var(--head);font-weight:600;white-space:nowrap}
th.num,td.num{text-align:right;font-variant-numeric:tabular-nums}
tr:last-child td{border-bottom:none}
th:last-child,td:last-child{border-right:none}
tbody tr:nth-child(even){background:var(--zebra)}
tbody tr:hover{background:var(--head)}
/* ---------- 稳定编号胶囊（FUNC / REF / INV / R / B / ROLE / REP ...） ---------- */
.id{display:inline-block;font-family:Consolas,"Courier New",monospace;font-size:11.5px;
 padding:1px 6px;border-radius:4px;white-space:nowrap;background:var(--id-bg);
 color:var(--id-ink);border:1px solid var(--id-line)}
.id.g{background:var(--id-bg-g);color:var(--id-ink-g);border-color:var(--id-line-g)}
.id.y{background:var(--id-bg-y);color:var(--id-ink-y);border-color:var(--id-line-y)}
.id.n{background:var(--id-bg-n);color:var(--id-ink-n);border-color:var(--id-line-n)}
.tag{font-size:11.5px;border-radius:4px;padding:1px 6px;white-space:nowrap;border:1px solid}
.s-ok{color:#0a7d40;border-color:#0a7d40;background:rgba(10,125,64,.08)}
.s-ai{color:#006393;border-color:#006393;background:rgba(0,99,147,.08)}
.s-todo{color:#b25e00;border-color:#b25e00;background:rgba(178,94,0,.10)}
/* ---------- mermaid 图容器（渲染失败时降级为源码 + 提示） ---------- */
.mermaid-wrap{margin:14px 0}
pre.mermaid{display:block;margin:0;padding:14px;background:var(--card);border:1px solid var(--line);
 border-radius:8px;overflow:auto;text-align:center;font-size:12.5px;color:var(--sub);line-height:1.5}
pre.mermaid svg{max-width:100%;height:auto}
pre.mermaid.mermaid-fallback,pre.mermaid[data-raw]{text-align:left;white-space:pre;
 background:var(--zebra);font-family:Consolas,"Courier New",monospace}
.mermaid-tip{margin:8px 0 0}
#top{position:fixed;right:22px;bottom:22px;z-index:9}
#top button{cursor:pointer;border:1px solid var(--line);background:var(--card);color:var(--sub);
 border-radius:50%;width:40px;height:40px;font-size:16px;box-shadow:0 3px 10px rgba(0,0,0,.12)}
@media (max-width:980px){
 .topbar .right .meta{display:none}
 #wrap{display:block}
 #side{position:static;width:auto;height:auto;flex:none;border-right:none;
  border-bottom:1px solid var(--line);max-height:46vh}
 #main{padding:16px 12px 70px}
 .sec{padding:16px 14px}
}
@media print{
 .topbar,#side,#top{display:none!important}
 body{background:#fff;font-size:11.5pt}
 #main{padding:0}
 .sec{border:none;border-radius:0;background:#fff;padding:0;margin:0 0 14px}
 .tw{overflow:visible;border:none;border-radius:0}
 table.mid,table.wide{min-width:0}
 tbody tr:hover{background:transparent}
 h1{page-break-after:avoid}
 h2,h3{page-break-after:avoid}
 table,.mermaid-wrap,pre,blockquote,.mock,.mock-modal{page-break-inside:avoid}
 a{color:inherit;text-decoration:none}
 .id,.tag{border-color:#cbd5e1!important}
}
"""

JS = """
(function(){
  var nav=document.getElementById('toc');
  if(!nav)return;
  var links=[].slice.call(nav.querySelectorAll('a[href^="#"]'));
  if(!links.length)return;

  /* 展开某目录项的祖先链 */
  function expand(a){
    var d=a.closest('details');
    while(d){ d.open=true; d=d.parentElement?d.parentElement.closest('details'):null; }
  }
  links.forEach(function(a){ a.addEventListener('click',function(){ expand(a); }); });

  /* 滚动定位：高亮当前章节并展开其祖先，长文档随时知道身处何处 */
  var heads=[].slice.call(document.querySelectorAll('#main h1,#main h2,#main h3,#main h4'))
              .filter(function(h){ return h.id; });
  var map={};
  links.forEach(function(a){ map[a.getAttribute('href').slice(1)]=a; });
  var cur=null;
  function spy(){
    var found=null;
    for(var i=0;i<heads.length;i++){
      if(heads[i].getBoundingClientRect().top<130){ found=heads[i].id; } else { break; }
    }
    if(found===cur)return;
    cur=found;
    links.forEach(function(a){ a.classList.remove('active'); });
    var a=found&&map[found];
    if(a){ a.classList.add('active'); expand(a); }
  }
  window.addEventListener('scroll',spy,{passive:true});
  window.addEventListener('hashchange',spy);
  window.addEventListener('resize',spy);
  spy();
})();
function tocAll(open){
  document.querySelectorAll('#toc details').forEach(function(d){ d.open=open; });
}
"""

# ------------------------------------------------ 静态界面原型样式库（UI 界面说明）
# 与《UI-UE界面设计规范》同源：品牌蓝 #2266e3、9pt 基准字体、扁平卡片、胶囊按钮。
# 用法：在 Markdown 中用 ```html 代码块书写 .mock 结构，转换后原样渲染为界面原型。
MOCK_CSS = """
/* ================= 静态界面原型（UI 界面说明）================= */
:root{
  --primary-color:#2266e3; --primary-hover:#1a56c0;
  --bg-color:#f0f2f6; --card-bg:#ffffff;
  --text-primary:#1e293b; --text-secondary:#5b6e8c;
  --border-color:#e2edf2; --divider-color:#e4e7ec;
  --radius-lg:28px; --radius-md:12px; --radius-sm:8px;
  --shadow-sm:0 8px 20px rgba(0,0,0,.08),0 2px 6px rgba(0,0,0,.06);
  --shadow-md:0 20px 35px -10px rgba(0,0,0,.25);
  --mu-font:'Inter',system-ui,-apple-system,'Segoe UI',Roboto,'Helvetica Neue','Microsoft YaHei',sans-serif;
  --font-size-base:9pt; --field-label-width:96px;
}
.muted{color:var(--text-secondary)}
.small{font-size:8.5pt}
.fig-cap{color:var(--text-secondary);font-size:8.4pt;text-align:center;margin:8px 0 18px}
h5{font-size:9.5pt;font-weight:700;margin:16px 0 8px;color:var(--text-secondary);border:none;padding:0}
.grid2{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:14px}
.grid3{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:14px}
.grid4{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:12px}
.kv b{display:block;color:var(--text-secondary);font-weight:500;font-size:8pt;margin-bottom:4px}
.note{padding:10px 14px;border-radius:var(--radius-sm);margin:12px 0;font-size:8.8pt}
.note.info{background:#eff6ff;border:1px solid #dbeafe;color:#1e40af}
.note.ok{background:#dcfce7;border:1px solid #bbf7d0;color:#166534}
.note.warn{background:#fef9c3;border:1px solid #fde68a;color:#854d0e}
.note.err{background:#fee2e2;border:1px solid #fecaca;color:#991b1b}
.badge{display:inline-block;padding:2px 8px;border-radius:12px;font-weight:500;font-size:8pt;white-space:nowrap}
.b-succ{background:#dcfce7;color:#166534}
.b-warn{background:#fef9c3;color:#854d0e}
.b-danger{background:#fee2e2;color:#991b1b}
.b-info{background:#dbeafe;color:#1e40af}
.b-neutral{background:#f1f5f9;color:#475569}

/* 原型外壳 */
.mock{border:1px solid var(--divider-color);background:#fff;overflow-x:auto;margin:12px 0;
  font-family:var(--mu-font);font-size:var(--font-size-base);color:var(--text-primary);line-height:1.55}
.mock *{box-sizing:border-box}
.mock-head{display:flex;justify-content:space-between;align-items:center;gap:12px;
  padding:12px 16px;border-bottom:1px solid var(--divider-color);flex-wrap:wrap}
.mock-head .mtitle{margin:0;font-size:10pt;font-weight:700;color:var(--text-primary)}
.mock-body{padding:16px}
.mock-actions{display:flex;gap:8px;flex-wrap:wrap}
.mock-foot{display:flex;justify-content:space-between;align-items:center;gap:12px;
  padding:10px 16px;border-top:1px solid var(--divider-color);background:#fafcff;flex-wrap:wrap}
.mock-topbar{display:flex;align-items:center;gap:12px;background:#111827;color:#fff;
  padding:10px 16px;font-size:8.6pt}
.mock-topbar .mtitle{color:#fff;font-weight:700;font-size:9.5pt}
.mock-topbar .sp{flex:1}
.mock-nav{display:flex;gap:0;border-bottom:1px solid var(--divider-color);background:#fff;flex-wrap:wrap}
.mock-nav span{padding:8px 14px;font-size:8.5pt;color:var(--text-secondary);border-bottom:2px solid transparent}
.mock-nav span.on{color:var(--primary-color);font-weight:600;border-bottom-color:var(--primary-color);background:#eff6ff}
.zone{border:1px dashed #cbd5e1;border-radius:var(--radius-sm);padding:12px;margin-bottom:14px}
.zone-title{font-weight:700;color:var(--text-secondary);font-size:8.6pt;margin-bottom:10px}
.toolbar{display:flex;justify-content:space-between;align-items:center;gap:12px;
  padding:12px 16px;border-bottom:1px solid var(--divider-color);flex-wrap:wrap}
.toolbar .filters{display:flex;gap:10px;align-items:center;flex-wrap:wrap}
.pager{display:flex;justify-content:flex-end;gap:6px;padding:10px 16px;border-top:1px solid var(--divider-color)}
.pagination{display:flex;align-items:center;gap:6px;font-size:8.2pt;color:var(--text-secondary)}

/* 表格化表单 */
.form-grid-2{display:grid;grid-template-columns:repeat(2,1fr);gap:10px 20px}
.form-grid-3{display:grid;grid-template-columns:repeat(3,1fr);gap:10px 18px}
.form-item{display:flex;align-items:center;gap:8px;min-width:0}
.form-item .field-label{flex-shrink:0;white-space:nowrap;color:var(--text-secondary);text-align:right;
  width:var(--field-label-width);font-size:8.4pt}
.form-item .field-label.required::before{content:'* ';color:#ef4444}
.form-item .field-control{flex:1;min-width:0}
.form-item.span-2{grid-column:span 2}
.form-item.span-3{grid-column:span 3}
.ctl{padding:5px 9px;border:1px solid var(--border-color);border-radius:6px;background:#fff;
  font-size:8.4pt;color:var(--text-primary);white-space:nowrap;overflow:hidden;text-overflow:ellipsis;display:block}
.ctl.ro{background:#f8fafc;color:var(--text-secondary)}
.ctl.psi{display:flex;gap:4px;align-items:center}
.ctl.psi .bt{border:1px solid #cbd5e1;border-radius:6px;padding:2px 7px;background:#fff;
  color:var(--text-secondary);font-size:8pt}
.ctl.gr{display:flex;justify-content:space-between;gap:8px;align-items:center}
.ctl.ta{background:#fff;min-height:44px;white-space:normal}
.ctl.ph{color:#9aa4b2}
.ck{display:inline-flex;align-items:center;gap:6px;font-size:8.4pt}
.ck i{width:12px;height:12px;border:1px solid #cbd5e1;border-radius:3px;background:#fff;display:inline-block}
.ck i.on{background:var(--primary-color);border-color:var(--primary-color);position:relative}
.ck i.on::after{content:'✓';color:#fff;font-size:8pt;position:absolute;left:1px;top:-2px}

/* 按钮与状态 */
.mbtn{display:inline-flex;align-items:center;gap:5px;padding:5px 14px;border-radius:40px;
  font-size:8.4pt;border:1px solid transparent;white-space:nowrap}
.mbtn.p{background:var(--primary-color);color:#fff}
.mbtn.s{background:#fff;border-color:#cbd5e1;color:var(--text-primary)}
.mbtn.d{background:#fff;border-color:#fecaca;color:#ef4444}
.mbtn.sm{padding:2px 9px;font-size:8pt}

/* 网格 */
.mock .tbl-mini{border-collapse:collapse;width:100%;font-size:8.2pt;background:#fff}
.mock .tbl-mini th{background:#f9fafb;padding:6px 8px;white-space:nowrap;font-weight:600;
  color:var(--text-secondary);border-bottom:1px solid var(--divider-color);border-right:none;vertical-align:middle}
.mock .tbl-mini td{padding:6px 8px;border-bottom:1px solid #f0f2f5;border-right:none;
  font-size:8.2pt;vertical-align:middle;text-align:left}
.mock .tbl-mini tbody tr:nth-child(even){background:#fff}
.mock .tbl-mini tr:hover td{background:#fafcff}
.mock .tbl-mini td input{border:1px solid transparent;background:transparent;padding:3px 5px;
  width:100%;font-size:8.2pt;font-family:var(--mu-font);border-radius:4px}
.mock .tbl-mini td input:hover{border-color:var(--border-color);background:#fff}
.mock .tbl-mini td.ra{text-align:right}
.mock .tbl-mini tr.sum td{background:#f8fafc;font-weight:600}
.mock .tbl-mini tr.chk td:first-child{width:28px}
.mock .tbl-mini input[type=checkbox]{width:auto}

/* 弹窗示意 */
.mock-modal{background:rgba(15,23,42,.42);padding:22px 18px;display:flex;justify-content:center}
.mock-dialog{background:#fff;border-radius:var(--radius-md);box-shadow:var(--shadow-md);
  width:100%;max-width:960px;overflow:hidden}
.mock-dialog .dlg-head{display:flex;justify-content:space-between;align-items:center;
  padding:12px 16px;border-bottom:1px solid var(--divider-color)}
.mock-dialog .dlg-head b{font-size:9.5pt}
.mock-dialog .dlg-head .x{color:var(--text-secondary);font-size:11pt;line-height:1}
.mock-dialog .dlg-body{padding:16px}
.mock-dialog .dlg-foot{display:flex;justify-content:flex-end;gap:10px;
  padding:12px 16px;border-top:1px solid var(--divider-color);background:#fafcff}

@media print{
  .mock,.mock-modal,.zone{page-break-inside:avoid}
  .mock{overflow:visible}
}
"""


_MERMAID_BOOT_TMPL = """
<script>
/* mermaid 渲染：__LOAD_NOTE__；离线 / 超时 / 渲染失败时一律降级为「保留源码 + 明示提示」 */
(function(){
  __CDN_VAR__
  var done=false;
  function fallback(){
    if(done)return; done=true;
    var blocks=document.querySelectorAll('pre.mermaid');
    if(!blocks.length)return;
    blocks.forEach(function(el){
      el.classList.add('mermaid-fallback');
      var tip=document.createElement('div');
      tip.className='note warn mermaid-tip';
      tip.innerHTML='__TIP__';
      el.parentNode.insertBefore(tip,el.nextSibling);
    });
  }
  function boot(){
    if(done)return;
    var dark=document.documentElement.getAttribute('data-theme')==='dark';
    var light={
      fontSize:'13px',primaryColor:'#e8f0fe',primaryTextColor:'#1d2026',
      primaryBorderColor:'#006393',lineColor:'#5b6270',
      secondaryColor:'#f0f3f7',tertiaryColor:'#ffffff',
      clusterBkg:'#fafbfd',clusterBorder:'#cbd5e1',edgeLabelBackground:'#ffffff'
    };
    var night={
      fontSize:'13px',primaryColor:'#16283f',primaryTextColor:'#e8ecf2',
      primaryBorderColor:'#4cc2ff',lineColor:'#9aa4b2',
      secondaryColor:'#1d2430',tertiaryColor:'#161b22',
      clusterBkg:'#141a22',clusterBorder:'#28303b',edgeLabelBackground:'#161b22'
    };
    try{
      mermaid.initialize({
        startOnLoad:false, theme:'base', securityLevel:'loose',
        fontFamily:'"Microsoft YaHei","微软雅黑",-apple-system,sans-serif',
        themeVariables: dark?night:light,
        er:{useMaxWidth:true},
        flowchart:{htmlLabels:true,curve:'basis',useMaxWidth:true}
      });
      mermaid.run({querySelector:'pre.mermaid'})
        .then(function(){ done=true; })
        .catch(function(e){ console.error('[mermaid] run failed',e); fallback(); });
    }catch(e){ console.error('[mermaid] init failed',e); fallback(); }
  }
__TRIGGER__
})();
</script>
"""

_MERMAID_CDN_VAR = "var CDN='https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.min.js';"

_MERMAID_CDN_TRIGGER = ("  var s=document.createElement('script');\n"
                        "  s.src=CDN; s.async=true; s.onload=boot; s.onerror=fallback;\n"
                        "  document.head.appendChild(s);\n"
                        "  setTimeout(function(){ if(!window.mermaid) fallback(); },10000);")

_MERMAID_INLINE_TRIGGER = "  if(window.mermaid){ boot(); } else { fallback(); }"

_MERMAID_TIP_CDN = ("<b>图表未渲染</b>：未能加载 mermaid（离线或网络受限）。"
                    "上方已保留图表源码，联网后刷新本页即可自动渲染成图。")
_MERMAID_TIP_INLINE = ("<b>图表未渲染</b>：mermaid 解析该图失败（图语法有问题）。"
                       "上方已保留图表源码，修正后重新转换即可。")

MERMAID_JS = (_MERMAID_BOOT_TMPL
              .replace("__LOAD_NOTE__", "CDN 异步加载")
              .replace("__CDN_VAR__", _MERMAID_CDN_VAR)
              .replace("__TIP__", _MERMAID_TIP_CDN)
              .replace("__TRIGGER__", _MERMAID_CDN_TRIGGER))

MERMAID_OFF = ("<script>document.querySelectorAll('pre.mermaid').forEach(function(d){"
               "d.setAttribute('data-raw','1');});</script>")

# inline 模式自动查找库的位置（按顺序）
MERMAID_LIB_CANDIDATES = (
    "~/.workbuddy/vendor/mermaid.min.js",
    "mermaid.min.js",
)


def inline_mermaid_tail(lib_js):
    """把 mermaid 库整段内联进 HTML，使交付件自包含、离线也能把图渲染出来。

    两处转义是为「库源码本身可能出现的 HTML 序列」兜底：
      - `</script` 会提前闭合脚本块，一律改写为 `<\\/script`（JS 字符串 / 正则中语义等价）；
      - 若库内含 `<script`，则 HTML 分词器可能因「`<!--` … `<script`」进入 double-escaped
        状态而使真正的 `</script>` 失效，此时再把 `<!--` 改写为 `\\x3C!--` 打断该路径
        （两者在 JS 字符串 / 正则 / 注释里语义等价）。
    """
    safe = lib_js.replace("</script", "<\\/script")
    if "<script" in safe:
        safe = safe.replace("<!--", "\\x3C!--")
    boot = (_MERMAID_BOOT_TMPL
            .replace("__LOAD_NOTE__", "库已内联，无需联网")
            .replace("__CDN_VAR__", "")
            .replace("__TIP__", _MERMAID_TIP_INLINE)
            .replace("__TRIGGER__", _MERMAID_INLINE_TRIGGER))
    return "<script>\n" + safe + "\n</script>\n" + boot


def resolve_mermaid_lib(explicit):
    """取 mermaid 库源码：优先命令行参数，其次环境变量，再次若干默认位置。"""
    tried = []
    if explicit:
        tried.append(explicit)
    elif os.environ.get("MERMAID_JS_PATH"):
        tried.append(os.environ["MERMAID_JS_PATH"])
    if not tried:
        tried.extend(MERMAID_LIB_CANDIDATES)
    for item in tried:
        path = Path(item).expanduser()
        if path.is_file():
            return path.read_text(encoding="utf-8"), str(path)
    raise FileNotFoundError("；".join(str(Path(t).expanduser()) for t in tried))


def build_html(title: str, markdown: str, theme: str, mermaid: bool,
               version: str = "", meta: str = "", mermaid_lib: str = "") -> str:
    blocks = parse_blocks(markdown)
    body, headings = render_body(blocks, {})
    toc = render_toc(headings)

    if mermaid_lib and "```mermaid" in markdown:
        mermaid_tail = inline_mermaid_tail(mermaid_lib)
    elif mermaid:
        mermaid_tail = MERMAID_JS
    else:
        mermaid_tail = MERMAID_OFF

    vtag = f'<span class="vtag">{html.escape(version)}</span>' if version else ""
    meta_html = f'<span class="meta">{html.escape(meta)}</span>' if meta else ""

    return f"""<!DOCTYPE html>
<html lang="zh-CN" data-theme="{theme}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html.escape(title)}</title>
<style>{CSS}{MOCK_CSS}</style>
</head>
<body>
<div class="topbar">
  <div class="left">
    <span class="title">{html.escape(title)}</span>
    {vtag}
  </div>
  <div class="right">
    {meta_html}
    <button class="tb-btn" onclick="window.print()">导出 PDF</button>
  </div>
</div>
<div id="wrap">
  <aside id="side">
    <div class="tools">
      <button onclick="tocAll(true)">展开全部</button>
      <button onclick="tocAll(false)">收起全部</button>
    </div>
    <nav id="toc">{toc}</nav>
  </aside>
  <div id="main"><main>
{body}
  </main></div>
</div>
<div id="top"><button onclick="scrollTo({{top:0,behavior:'smooth'}})" title="回到顶部">↑</button></div>
<script>{JS}</script>
{mermaid_tail}
</body>
</html>
"""


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

    ap = argparse.ArgumentParser(description="需求规格说明书 Markdown → 单文件 HTML")
    ap.add_argument("input", help="输入 .md 文件")
    ap.add_argument("-o", "--output", default=None, help="输出 .html（默认同名同目录）")
    ap.add_argument("--theme", default="light", choices=["light", "dark"], help="配色主题")
    ap.add_argument("--title", default=None, help="文档标题（默认取输入文件首个 h1 或文件名）")
    ap.add_argument("--mermaid", default="on", choices=["on", "off", "inline"],
                    help="图渲染方式：on=引入 CDN（默认，需联网）；"
                         "inline=把 mermaid 库整段内联（自包含、离线也渲染）；off=不引入，仅保留源码")
    ap.add_argument("--mermaid-lib", default=None,
                    help="inline 模式使用的 mermaid.min.js 路径"
                         "（默认依次查找 环境变量 MERMAID_JS_PATH / ~/.workbuddy/vendor/ / 当前目录）")
    ap.add_argument("--version", default=None, help="顶栏版本标签，如 V1.0（默认从正文元信息表自动识别）")
    ap.add_argument("--meta", default=None, help="顶栏右侧元信息（默认自动识别「需求来源」）")
    args = ap.parse_args()

    src = Path(args.input).expanduser().resolve()
    if not src.exists():
        print(f"✗ 找不到输入文件：{src}")
        return 1
    md = src.read_text(encoding="utf-8")
    title = args.title
    if not title:
        m = re.search(r"^#\s+(.+)$", md, re.M)
        title = m.group(1).strip() if m else src.stem
    dst = Path(args.output).expanduser().resolve() if args.output else src.with_suffix(".html")

    # 顶栏元信息：优先命令行参数，其次正文元信息表，最后文件名兜底
    version = args.version
    if version is None:
        m = re.search(r"\|\s*(?:文档版本|版本号|版本)\s*\|\s*(V?\d[\d.]*)", md)
        if m:
            version = m.group(1)
    if not version:
        m = re.search(r"[-_ ](V\d+(?:\.\d+)*)", src.stem)
        version = m.group(1) if m else ""

    meta = args.meta
    if meta is None:
        m = re.search(r"\|\s*(需求来源|编写依据)\s*\|\s*([^|\n]+)", md)
        meta = f"{m.group(1)}：{m.group(2).strip()}" if m else ""

    mermaid_lib = ""
    if args.mermaid == "inline":
        try:
            mermaid_lib, lib_path = resolve_mermaid_lib(args.mermaid_lib)
        except FileNotFoundError as err:
            print("✗ --mermaid inline 需要一份 mermaid.min.js，但以下位置都没有：")
            print("    " + str(err))
            print("  一次获取、所有文档共用：")
            print("    curl -sL -o ~/.workbuddy/vendor/mermaid.min.js \\")
            print("      https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.min.js")
            return 1
        if "```mermaid" not in md:
            mermaid_lib = ""

    dst.write_text(
        build_html(title, md, args.theme, args.mermaid == "on", version, meta, mermaid_lib),
        encoding="utf-8", newline="\n",
    )
    if args.mermaid == "inline":
        mermaid_desc = ("inline（已内联库 %.0f KB）" % (len(mermaid_lib) / 1024)
                        if mermaid_lib else "inline（正文无图，未内联）")
    else:
        mermaid_desc = args.mermaid
    print(f"✅ 已生成：{dst}")
    print(f"   标题：{title}｜主题：{args.theme}｜Mermaid：{mermaid_desc}"
          f"｜版本标签：{version or '（无）'}｜元信息：{meta or '（无）'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
