# -*- coding: utf-8 -*-
"""
Embedded web server (standard library only) for the generated domain skill.

Serves:
  GET  /                     domain home (list of aggregates + entry/query links)
  GET  /entry/<alias>        data-entry form (single: 2-col grid / master-detail)
  GET  /detail/<alias>/<id>  record detail view
  GET  /query                SQL / natural-language query console
  GET  /api/objects/<alias>  list (enriched: FK ids -> names)
  GET  /api/schema           model metadata for the NL-query layer
  POST /api/sql              run a read-only SQL, return rows
  POST /api/objects/<alias>  create
  PUT  /api/objects/<alias>/<id>   update
  DELETE /api/objects/<alias>/<id> delete
"""
import json
import sqlite3
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs

import loader
import db
import crud
import query

CSS = """
:root{--primary:#2266e3;--nav:#111827;--border:#e2edf2;--bg:#f0f2f6;--txt:#111827;}
*{box-sizing:border-box;}
body{margin:0;font-family:-apple-system,'Microsoft YaHei',Segoe UI,Roboto,sans-serif;
  background:var(--bg);color:var(--txt);}
.nav{background:var(--nav);color:#fff;padding:12px 20px;font-size:16px;font-weight:600;}
.nav a{color:#cfe0ff;text-decoration:none;margin-left:16px;font-weight:400;font-size:13px;}
.wrap{padding:20px;max-width:1100px;margin:0 auto;}
.card{background:#fff;border:1px solid var(--border);border-radius:8px;padding:18px;margin-bottom:16px;}
h2{margin-top:0;color:var(--primary);font-size:18px;}
.grid2{display:grid;grid-template-columns:1fr 1fr;gap:12px 20px;}
label{display:block;font-size:12px;color:#475569;margin-bottom:4px;}
input,select,textarea{width:100%;padding:8px 10px;border:1px solid var(--border);
  border-radius:6px;font-size:14px;background:#fff;}
.btn{background:var(--primary);color:#fff;border:none;padding:9px 18px;border-radius:6px;
  cursor:pointer;font-size:14px;margin-right:8px;}
.btn.ghost{background:#fff;color:var(--primary);border:1px solid var(--primary);}
table{width:100%;border-collapse:collapse;font-size:13px;}
th,td{border:1px solid var(--border);padding:7px 9px;text-align:left;}
th{background:#eef3fb;}
.row-del{color:#dc2626;cursor:pointer;}
.pill{display:inline-block;background:#eef3fb;color:var(--primary);border-radius:12px;
  padding:2px 10px;font-size:12px;margin:2px;}
"""

TPL = """<!doctype html><html lang="zh"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title}</title><style>{css}</style></head><body>
<div class="nav">本体驱动应用 · {domain}<a href="/">首页</a><a href="/query">查询</a></div>
<div class="wrap">{body}</div></body></html>"""


def page(domain, title, body):
    return TPL.format(domain=domain, title=title, body=body, css=CSS)


# ----------------------------------------------------------------- rendering
def render_index(model, conn):
    masters, others = [], []
    for agg in model.aggregates:
        item = f'<a class="pill" href="/entry/{agg.get("alias")}">{agg.get("name")}</a>'
        (masters if "核心域" in (agg.get("tags") or []) else others).append(item)
    body = '<div class="card"><h2>核心对象 / 业务单据</h2>' + " ".join(masters) + "</div>"
    body += '<div class="card"><h2>主数据</h2>' + " ".join(others) + "</div>"
    body += ('<div class="card"><p style="color:#64748b;font-size:13px">'
             '点击对象进入录入与维护；或在「查询」页用自然语言/SQL 查询数据。</p></div>')
    return page(model.m1.get("domain", ""), "首页", body)


def _field_input(model, conn, col, value=""):
    if col.get("systemField"):
        return ""  # system fields not shown in entry form
    name = col["name"]
    label = col["label"]
    if col.get("ref"):
        t = model.get_aggregate(col["ref"])
        opts = ""
        if t:
            tn = model.table_name(t)
            ncol = query.get_name_column(model, t) or model.pk_column(t)
            rows = conn.execute(f'SELECT "{model.pk_column(t)}","{ncol}" FROM "{tn}"').fetchall()
            for r in rows:
                sel = " selected" if str(r[0]) == str(value) else ""
                opts += f'<option value="{r[0]}"{sel}>{r[1]}（{r[0]}）</option>'
        return (f'<div><label>{label}</label><select name="{name}"><option value="">—</option>'
                f'{opts}</select></div>')
    if col.get("dict_ref"):
        items = model.dict_items(col["dict_ref"]["dictionaryId"], col["dict_ref"]["typeCode"])
        opts = "".join(
            f'<option value="{it["code"]}"{" selected" if it["code"]==value else ""}>'
            f'{it["label"]}</option>' for it in items if it["enabled"])
        return f'<div><label>{label}</label><select name="{name}"><option value="">—</option>{opts}</select></div>'
    if col.get("enum"):
        opts = "".join(f'<option value="{v}"{" selected" if v==value else ""}>{v}</option>'
                       for v in col["enum"])
        return f'<div><label>{label}</label><select name="{name}"><option value="">—</option>{opts}</select></div>'
    if col["sql_type"] == "INTEGER" and col.get("enum") is None and not col.get("ref"):
        return f'<div><label>{label}</label><input name="{name}" value="{value}"></div>'
    if col["sql_type"] == "REAL":
        return f'<div><label>{label}</label><input name="{name}" value="{value}" step="0.01"></div>'
    return f'<div><label>{label}</label><input name="{name}" value="{_esc(value)}"></div>'


def render_entry(model, conn, alias):
    agg = model.get_aggregate(alias)
    if not agg:
        return page(model.m1.get("domain", ""), "录入", "<div class='card'>未找到对象</div>")
    cols = model.columns(agg)
    # Filter: skip system fields and PK (auto-generated) from entry form
    form_cols = [c for c in cols if not c.get("systemField") and not (c.get("unique") and c.get("required"))]
    fields = "".join(_field_input(model, conn, c) for c in form_cols)
    children_html = ""
    child_specs = [(e, spec) for kind, e, spec in model.child_tables(agg) if kind == "child"]
    if child_specs:
        rows_js = []
        for e, spec in child_specs:
            cfields = "".join(_field_input(model, conn, c) for c in spec["cols"][1:])
            rows_js.append("{alias:%s,html:%s}" % (json.dumps(e.get("alias")), json.dumps(
                f'<tr>{"".join("<td>"+_field_input(model,conn,c)+"</td>" for c in spec["cols"][1:])}'
                f'<td><span class="row-del" onclick="this.closest(' + "'tr'" + ').remove()">删除</span></td></tr>')))
        detail_block = ""
        for e, spec in child_specs:
            header = "".join(f"<th>{c['label']}</th>" for c in spec["cols"][1:]) + "<th></th>"
            detail_block += (f'<h3 style="margin:14px 0 6px">{e.get("name")}</h3>'
                              f'<table id="tbl_{e.get("alias")}"><thead><tr>{header}</tr></thead>'
                              f'<tbody></tbody></table>'
                              f'<button class="btn ghost" type="button" onclick="addRow('
                              f'{json.dumps(e.get("alias"))})">+ 添加{e.get("name")}</button>')
        # Master-detail layout: form on top, detail table at bottom (UI布局规范: form-top-table-bottom)
        body = (f'<div class="card"><h2>录入 / 维护：{agg.get("name")}</h2>'
                f'<form id="mainForm"><div class="grid2">{fields}</div></form>'
                f'{detail_block}'
                f'<div style="margin-top:14px"><button class="btn" type="button" '
                f'onclick="submitForm({json.dumps(alias)})">保存</button></div></div>')
        body += f"""
        <script>
        var CHILDREN = {json.dumps([{"alias":e.get("alias"),"name":e.get("name"),
            "cells":[ {"name":c["name"],"html":_field_input(model,conn,c)} for c in spec["cols"][1:] ]}
            for e,spec in child_specs])};
        function addRow(alias){{
          var def = CHILDREN.find(c=>c.alias==alias);
          var tr = document.createElement('tr');
          def.cells.forEach(function(c){{ var td=document.createElement('td'); td.innerHTML=c.html; tr.appendChild(td); }});
          var td=document.createElement('td');
          td.innerHTML='<span class="row-del" onclick="this.closest(\'tr\').remove()">删除</span>';
          tr.appendChild(td);
          document.querySelector('#tbl_'+alias+' tbody').appendChild(tr);
        }}
        function submitForm(alias){{
          var data={{}};
          document.querySelectorAll('#mainForm [name]').forEach(function(el){{
            if(el.name) data[el.name]=el.value;
          }});
          CHILDREN.forEach(function(def){{
            var rows=[];
            document.querySelectorAll('#tbl_'+def.alias+' tbody tr').forEach(function(tr){{
              var row={{}}; tr.querySelectorAll('[name]').forEach(function(el){{ row[el.name]=el.value; }});
              if(Object.keys(row).length) rows.push(row);
            }});
            if(rows.length) data[def.alias]=rows;
          }});
          fetch('/api/objects/'+alias,{{method:'POST',headers:{{'Content-Type':'application/json'}},
            body:JSON.stringify(data)}}).then(r=>r.json()).then(function(res){{
            alert(res.ok? '保存成功，ID='+res.id : '失败：'+res.error);
            if(res.ok) location.href='/detail/'+alias+'/'+res.id;
          }});
        }}
        </script>"""
    else:
        # Single entity: grid-2-columns layout (UI布局规范)
        body = (f'<div class="card"><h2>录入 / 维护：{agg.get("name")}</h2>'
                f'<form id="mainForm"><div class="grid2">{fields}</div>'
                f'<div style="margin-top:14px"><button class="btn" type="button" '
                f'onclick="submitForm({json.dumps(alias)})">保存</button></div></form></div>')
        body += """
        <script>
        function submitForm(alias){
          var data={};
          document.querySelectorAll('#mainForm [name]').forEach(function(el){ if(el.name) data[el.name]=el.value; });
          fetch('/api/objects/'+alias,{method:'POST',headers:{'Content-Type':'application/json'},
            body:JSON.stringify(data)}).then(r=>r.json()).then(function(res){
            alert(res.ok? '保存成功，ID='+res.id : '失败：'+res.error);
            if(res.ok) location.href='/detail/'+alias+'/'+res.id;
          });
        }
        </script>"""
    return page(model.m1.get("domain", ""), "录入", body)


def render_detail(model, conn, alias, pid):
    agg = model.get_aggregate(alias)
    if not agg:
        return page(model.m1.get("domain", ""), "详情", "<div class='card'>未找到对象</div>")
    rec = crud.get(model, conn, agg, pid)
    if not rec:
        return page(model.m1.get("domain", ""), "详情", "<div class='card'>未找到记录</div>")
    enr = query.enrich_row(model, conn, agg, rec)
    rows = ""
    for c in model.columns(agg):
        disp = enr.get(c["name"] + "__label") or enr.get(c["name"])
        rows += f"<tr><td>{c['label']}</td><td>{_esc(disp)}</td></tr>"
    body = f'<div class="card"><h2>{agg.get("name")} 详情</h2><table>{rows}</table>'
    for kind, e, spec in model.child_tables(agg):
        if kind == "child":
            cr = enr.get(e.get("alias") or e.get("name"), [])
            if cr:
                th = "".join(f"<th>{c['label']}</th>" for c in spec["cols"][1:])
                trs = "".join("<tr>" + "".join(f"<td>{_esc(r.get(c['name']))}</td>"
                                               for c in spec["cols"][1:]) + "</tr>" for r in cr)
                body += f'<h3 style="margin:14px 0 6px">{e.get("name")}</h3><table><thead><tr>{th}</tr></thead><tbody>{trs}</tbody></table>'
    body += (f'<div style="margin-top:12px"><button class="btn ghost" '
             f'onclick="if(confirm(\'确认删除(逻辑作废)?\'))del(\'{alias}\',\'{pid}\')">删除/作废</button></div></div>')
    body += f"""
    <script>
    function del(a,id){{ fetch('/api/objects/'+a+'/'+id,{{method:'DELETE'}}).then(r=>r.json())
      .then(function(res){{ alert(res.ok? '已处理('+res.mode+')' : '失败：'+res.error); location.href='/'; }}); }}
    </script>"""
    return page(model.m1.get("domain", ""), "详情", body)


def render_query(model):
    body = ('<div class="card"><h2>查询控制台</h2>'
            '<p style="color:#64748b;font-size:13px">可在自然语言对话中由 AI 生成 SQL 后填入此处执行；'
            '也可直接输入只读 SELECT 语句。</p>'
            '<textarea id="sql" rows="5" style="width:100%;font-family:monospace"></textarea>'
            '<div style="margin-top:10px"><button class="btn" onclick="runSql()">执行</button></div>'
            '<div id="result" style="margin-top:14px"></div></div>')
    body += """
    <script>
    function runSql(){
      var sql=document.getElementById('sql').value;
      fetch('/api/sql',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({sql:sql})})
        .then(r=>r.json()).then(function(res){
          if(!res.ok){ document.getElementById('result').innerHTML='<p style="color:#dc2626">'+res.error+'</p>'; return; }
          if(!res.columns.length){ document.getElementById('result').innerHTML='<p>无结果</p>'; return; }
          var h='<table><thead><tr>'+res.columns.map(c=>'<th>'+c+'</th>').join('')+'</tr></thead><tbody>';
          res.rows.forEach(function(r){ h+='<tr>'+res.columns.map(c=>'<td>'+(r[c]===null?'':r[c])+'</td>').join('')+'</tr>'; });
          h+='</tbody></table>';
          document.getElementById('result').innerHTML=h;
        });
    }
    </script>"""
    return page(model.m1.get("domain", ""), "查询", body)


def _esc(v):
    if v is None:
        return ""
    return str(v).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


# ----------------------------------------------------------------- handler
class Handler(BaseHTTPRequestHandler):
    model = None
    db_path = None

    def _conn(self):
        return db.connect(self.db_path)

    def _send(self, code, body, ctype="application/json; charset=utf-8"):
        data = body.encode("utf-8") if isinstance(body, str) else body
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _json(self, obj):
        self._send(200, json.dumps(obj, ensure_ascii=False, default=str))

    def _body(self):
        n = int(self.headers.get("Content-Length", 0) or 0)
        if not n:
            return {}
        try:
            return json.loads(self.rfile.read(n).decode("utf-8"))
        except ValueError:
            return {}

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.send_header("Access-Control-Max-Age", "86400")
        self.send_header("Content-Length", "0")
        self.end_headers()

    def do_GET(self):
        p = urlparse(self.path)
        path = p.path
        conn = self._conn()
        try:
            if path == "/":
                self._send(200, render_index(self.model, conn), "text/html; charset=utf-8")
            elif path == "/query":
                self._send(200, render_query(self.model), "text/html; charset=utf-8")
            elif path.startswith("/entry/"):
                alias = path.split("/")[2]
                self._send(200, render_entry(self.model, conn, alias), "text/html; charset=utf-8")
            elif path.startswith("/detail/"):
                _, _, alias, pid = path.split("/")[:4]
                self._send(200, render_detail(self.model, conn, alias, pid), "text/html; charset=utf-8")
            elif path == "/api/schema":
                schema = query.schema(self.model)
                schema["dictionaries"] = self.model.dictionaries
                self._json(schema)
            elif path.startswith("/api/objects/"):
                alias = path.split("/")[3]
                agg = self.model.get_aggregate(alias)
                if not agg:
                    return self._json({"ok": False, "error": "未知对象"})
                rows = crud.list_rows(self.model, conn, agg)
                self._json({"ok": True, "rows": query.enrich_rows(self.model, conn, agg, rows)})
            else:
                self._send(404, "not found")
        finally:
            conn.close()

    def do_POST(self):
        p = urlparse(self.path)
        conn = self._conn()
        try:
            if p.path == "/api/sql":
                b = self._body()
                try:
                    cols, rows = query.run_readonly_sql(conn, b.get("sql", ""))
                    self._json({"ok": True, "columns": cols, "rows": rows})
                except ValueError as e:
                    self._json({"ok": False, "error": str(e)})
                return
            if p.path.startswith("/api/objects/"):
                alias = p.path.split("/")[3]
                agg = self.model.get_aggregate(alias)
                if not agg:
                    return self._json({"ok": False, "error": "未知对象"})
                res = crud.create(self.model, conn, agg, self._body())
                self._json(res)
                return
            self._send(404, "not found")
        finally:
            conn.close()

    def do_PUT(self):
        p = urlparse(self.path)
        parts = p.path.split("/")
        if len(parts) >= 5 and parts[1] == "api" and parts[2] == "objects":
            alias, pid = parts[3], parts[4]
            conn = self._conn()
            try:
                agg = self.model.get_aggregate(alias)
                if not agg:
                    return self._json({"ok": False, "error": "未知对象"})
                self._json(crud.update(self.model, conn, agg, pid, self._body()))
            finally:
                conn.close()
        else:
            self._send(404, "not found")

    def do_DELETE(self):
        p = urlparse(self.path)
        parts = p.path.split("/")
        if len(parts) >= 5 and parts[1] == "api" and parts[2] == "objects":
            alias, pid = parts[3], parts[4]
            conn = self._conn()
            try:
                agg = self.model.get_aggregate(alias)
                if not agg:
                    return self._json({"ok": False, "error": "未知对象"})
                self._json(crud.delete(self.model, conn, agg, pid))
            finally:
                conn.close()
        else:
            self._send(404, "not found")

    def log_message(self, *a):
        pass


def make_server(model, db_path, host="127.0.0.1", port=8765):
    Handler.model = model
    Handler.db_path = db_path
    return HTTPServer((host, port), Handler)


if __name__ == "__main__":
    pass
