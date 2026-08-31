#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
generate_ui_workbench.py  v3
用途: 读取目录内全部 *-model.yaml（本体模型元文件，含 m-mapping-model.yaml），
     归一化为 JSON 并注入内嵌 JS 引擎的 HTML 模板，生成"单文件、自包含"的
     UI 调用链追踪工作台（纯前端、无外部依赖、双击即开）。
可复用: 换一套同类 YAML 模型目录即可重新生成，无需改代码。
用法:
    python generate_ui_workbench.py [yaml_dir] [output_html] [--pretty]
默认:
    yaml_dir     = ontology-models-doc
    output_html  = star-hotel-ui-callchain.html
"""
import os
import sys
import glob
import json

try:
    import yaml
except ImportError:
    sys.stderr.write("缺少 PyYAML，请先安装：pip install pyyaml\n")
    sys.exit(1)

DEFAULT_DIR = "ontology-models-doc"
DEFAULT_OUT = "star-hotel-ui-callchain.html"


def parse_args(argv):
    args = {"pretty": False}
    rest = []
    for a in argv:
        if a == "--pretty":
            args["pretty"] = True
        else:
            rest.append(a)
    args["dir"] = rest[0] if len(rest) > 0 else DEFAULT_DIR
    args["out"] = rest[1] if len(rest) > 1 else DEFAULT_OUT
    return args


def load_models(yaml_dir):
    models = {}
    if not os.path.isdir(yaml_dir):
        sys.stderr.write("警告: 目录不存在 %r，将生成空工作台\n" % yaml_dir)
        return models
    for path in sorted(glob.glob(os.path.join(yaml_dir, "*-model.yaml"))):
        name = os.path.basename(path)
        try:
            with open(path, encoding="utf-8") as f:
                data = yaml.safe_load(f)
            if isinstance(data, dict):
                models[name] = data
        except Exception as e:  # noqa: BLE001
            sys.stderr.write("警告: 解析失败 %s: %s\n" % (name, e))
    return models


def compute_stats(models):
    def count(obj, *keys):
        for k in keys:
            if isinstance(obj, dict) and isinstance(obj.get(k), list):
                return len(obj[k])
        return 0

    stats = {"screen": 0, "behavior": 0, "rule": 0, "event": 0, "scenario": 0,
             "aggregate": 0, "permission": 0, "report": 0, "flow": 0, "table": 0,
             "dictionary": 0, "interface": 0, "mapping": 0}
    for data in models.values():
        stats["screen"] += count(data, "screens")
        stats["behavior"] += count(data, "behaviors")
        stats["rule"] += count(data, "rules")
        stats["event"] += count(data, "events")
        stats["scenario"] += count(data, "event_scenarios")
        stats["aggregate"] += count(data, "aggregates")
        stats["permission"] += count(data, "permissions")
        stats["report"] += count(data, "query_reports")
        stats["flow"] += count(data, "flows")
        stats["dictionary"] += count(data, "data_dictionaries")
        stats["interface"] += count(data, "interfaces")
        stats["mapping"] += count(data, "mappings")
        for m in (data.get("mappings") or []):
            stats["table"] += len(m.get("tableMappings") or [])
    return stats


def build_payload(models, pretty):
    payload = {"domain": "本体模型 · UI 调用链追踪工作台",
               "models": models, "stats": compute_stats(models)}
    if pretty:
        return json.dumps(payload, ensure_ascii=False, indent=2)
    return json.dumps(payload, ensure_ascii=False)


TEMPLATE = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>本体模型 · UI 调用链追踪工作台</title>
<style>
:root{--bg:#f3f6fa;--bg2:#ffffff;--panel:#ffffff;--panel2:#eef2f7;--panel3:#e7edf5;
 --line:#d8e1ec;--text:#22303f;--muted:#5a6b80;--dim:#8a98ab;--blue:#2f6fdb;--green:#1f9d55;
 --amber:#b7791f;--cyan:#0f7c83;--red:#d64545;--violet:#6d5a9e;--white:#1f2a3a;--pink:#c65a8a;
 --radius:10px;--shadow:0 4px 16px rgba(30,60,90,.12)}
*{box-sizing:border-box}html,body{height:100%}
body{margin:0;background:var(--bg);color:var(--text);font:14px/1.6 "Segoe UI","Microsoft YaHei",system-ui,sans-serif;overflow:hidden}
a{color:var(--cyan);text-decoration:none;cursor:pointer}a:hover{text-decoration:underline}
.mono{font-family:Consolas,Menlo,monospace}
::-webkit-scrollbar{width:10px;height:10px}::-webkit-scrollbar-thumb{background:#2c4158;border-radius:6px}
.topbar{height:52px;display:flex;align-items:center;gap:14px;padding:0 16px;background:linear-gradient(90deg,#ffffff,#eef3f9);border-bottom:1px solid var(--line);box-shadow:0 1px 6px rgba(30,60,90,.06)}
.topbar .brand{font-weight:700;font-size:15px;white-space:nowrap;color:#1f3864}
.topbar .brand b{color:var(--cyan)}
.searchbox{flex:1;max-width:520px;position:relative}
.searchbox input{width:100%;background:var(--panel);border:1px solid var(--line);border-radius:8px;padding:7px 34px 7px 12px;color:var(--text);outline:none}
.searchbox input:focus{border-color:var(--blue)}
.searchbox .kbd{position:absolute;right:10px;top:50%;transform:translateY(-50%);font-size:11px;color:var(--dim);border:1px solid var(--line);border-radius:4px;padding:0 5px}
.badges{display:flex;gap:8px;flex-wrap:wrap}
.badge{font-size:11px;padding:3px 8px;border-radius:20px;background:var(--panel2);border:1px solid var(--line);color:var(--muted);white-space:nowrap}
.badge b{color:#1f3864;margin-left:4px}
.toolbtn{background:var(--panel);border:1px solid var(--line);color:var(--text);border-radius:8px;padding:7px 12px;cursor:pointer;font-size:12px}
.toolbtn:hover{border-color:var(--blue);color:var(--blue)}
.main{display:flex;height:calc(100vh - 52px)}
.splitter{width:6px;cursor:col-resize;background:transparent;flex:0 0 6px;transition:background .15s;position:relative;z-index:5}
.splitter:hover,.splitter.active{background:var(--blue)}
.left{width:380px;min-width:220px;background:var(--bg2);border-right:1px solid var(--line);overflow:auto;padding:8px}
.right{flex:1;overflow:auto;padding:18px 22px}
.right h2{margin:0 0 4px;font-size:18px}
.right .crumb{font-size:12px;color:var(--dim);margin-bottom:14px;word-break:break-all}
.right .crumb a{color:var(--cyan)}
.node-tag{display:inline-block;font-size:11px;padding:2px 9px;border-radius:12px;margin-left:6px;vertical-align:2px;font-weight:600}
.tag-screen{background:rgba(232,238,245,.15);color:var(--white)}
.tag-childscreen,.tag-subdir{background:rgba(232,238,245,.2);color:var(--white)}
.tag-eltrigger,.tag-element{background:rgba(232,238,245,.25);color:var(--white)}
.tag-moevent,.tag-event,.tag-eventNode{background:rgba(6,182,212,.18);color:var(--cyan)}
.tag-behavior{background:rgba(34,197,94,.18);color:var(--green)}
.tag-rule{background:rgba(245,158,11,.18);color:var(--amber)}
.tag-rdir,.tag-odir,.tag-bdir,.tag-moredir{background:rgba(139,92,246,.16);color:var(--violet)}
.tag-object,.tag-aggregate{background:rgba(139,92,246,.2);color:var(--violet)}
.tag-entity{background:rgba(139,92,246,.14);color:var(--violet)}
.tag-attribute{background:rgba(139,92,246,.12);color:var(--violet)}
.tag-scenario{background:rgba(139,92,246,.2);color:var(--violet)}
.tag-step{background:rgba(6,182,212,.14);color:var(--cyan)}
.tag-chainstep{background:rgba(6,182,212,.2);color:var(--cyan)}
.tag-report{background:rgba(59,130,246,.2);color:var(--blue)}
.tag-table{background:rgba(59,130,246,.18);color:var(--blue)}
.tag-permission{background:rgba(236,72,153,.2);color:var(--pink)}
.tag-flow{background:rgba(59,130,246,.2);color:var(--blue)}
.tag-mapping{background:rgba(59,130,246,.18);color:var(--blue)}
.tag-interface{background:rgba(34,197,94,.2);color:var(--green)}
.tag-dictionary{background:rgba(245,158,11,.2);color:var(--amber)}
.tag-cross{background:rgba(139,92,246,.2);color:var(--violet)}
.tag-role{background:rgba(236,72,153,.2);color:var(--pink)}
.card{background:var(--panel);border:1px solid var(--line);border-radius:var(--radius);box-shadow:var(--shadow);padding:16px;margin-bottom:16px}
.card h3{margin:0 0 12px;font-size:14px;color:#1f3864;display:flex;align-items:center;gap:8px}
.card h3 .hint{font-size:11px;color:var(--dim);font-weight:400}
.kv{display:grid;grid-template-columns:minmax(120px,220px) 1fr;gap:6px 14px}
.kv .k{color:var(--muted);font-size:12px}.kv .v{word-break:break-word}
table.tbl{width:100%;border-collapse:collapse;font-size:12.5px}
table.tbl th,table.tbl td{border:1px solid var(--line);padding:6px 9px;text-align:left;vertical-align:top}
table.tbl th{background:var(--panel2);color:#1f2a3a;font-weight:600;white-space:nowrap}
table.tbl tr:nth-child(even) td{background:rgba(30,60,90,.02)}
.pill{display:inline-block;font-size:11px;padding:1px 8px;border-radius:10px;margin:1px 3px 1px 0;background:var(--panel2);border:1px solid var(--line);cursor:pointer;color:var(--text)}
.pill:hover{border-color:var(--blue);color:var(--blue)}
.pill.dangle{color:var(--dim);text-decoration:line-through;cursor:default}
pre.code{background:#f8fafc;border:1px solid var(--line);border-radius:8px;padding:12px;font-size:12px;overflow:auto;white-space:pre-wrap;word-break:break-all;color:#33455a}
pre.ascii{background:#f8fafc;border:1px solid var(--line);border-radius:8px;padding:14px;font-size:11.5px;line-height:1.35;overflow:auto;color:#2c4a6b}
details{margin:6px 0}summary{cursor:pointer;color:var(--cyan);font-size:12.5px}
.chain{display:flex;flex-wrap:wrap;gap:6px;align-items:center;margin:8px 0}
.chstep{display:inline-flex;align-items:center;gap:5px;background:var(--panel3);border:1px solid var(--line);border-radius:8px;padding:6px 10px;font-size:12px;cursor:pointer}
.chstep:hover{border-color:var(--cyan)}.chstep .stepno{color:var(--dim);font-size:10px}
.chstep .arrow{color:var(--dim)}.charrow{color:var(--dim);font-size:13px}
.tree{user-select:none}
.tree .root-t{font-size:12px;text-transform:uppercase;letter-spacing:1px;color:var(--muted);margin:10px 6px 4px;font-weight:700}
.tnode{margin:1px 0;border-radius:6px}
.tnode>.trow{display:flex;align-items:center;gap:5px;padding:3px 6px;border-radius:6px;cursor:pointer;white-space:nowrap}
.tnode>.trow:hover{background:var(--panel2)}
.tnode>.trow.active{background:var(--panel3);outline:1px solid var(--blue)}
.tnode>.trow .caret{width:14px;color:var(--dim);font-size:11px;text-align:center;flex:0 0 14px}
.tnode>.trow .label{overflow:hidden;text-overflow:ellipsis}
.tnode>.trow .sub{color:var(--dim);font-size:11px;margin-left:auto;flex:0 0 auto;padding-left:6px}
.tchildren{margin-left:14px;border-left:1px dashed var(--line);padding-left:5px}
.trow .ic{width:15px;text-align:center;flex:0 0 15px;font-size:11px;color:var(--muted)}
.ic.s,.ic.e{color:var(--white)}.ic.b{color:var(--green)}.ic.r{color:var(--amber)}
.ic.a{color:var(--violet)}.ic.t{color:var(--blue)}.ic.p{color:var(--pink)}
.ic.f{color:var(--blue)}.ic.o{color:var(--violet)}.ic.c{color:var(--cyan)}
.uv-tools{display:flex;gap:8px;align-items:center;margin-bottom:12px}
.uv-tools button{background:var(--panel);border:1px solid var(--line);color:var(--text);border-radius:7px;padding:5px 11px;cursor:pointer;font-size:12px}
.uv-tools button.active{border-color:var(--cyan);color:var(--cyan);background:rgba(15,124,131,.08)}
.ui-win{background:#f3f6fa;border-radius:12px;box-shadow:0 10px 30px rgba(0,0,0,.5);color:#1c2733;overflow:hidden;font-size:13px}
.ui-titlebar{background:#e8edf3;padding:9px 14px;display:flex;align-items:center;gap:10px;border-bottom:1px solid #d4dce6}
.ui-dots{display:flex;gap:6px}.ui-dots span{width:11px;height:11px;border-radius:50%}
.ui-dot-r{background:#ff5f57}.ui-dot-y{background:#febc2e}.ui-dot-g{background:#28c840}
.ui-titlebar .t{font-weight:700}.ui-titlebar .st{color:#6b7a8c;font-size:11px}
.ui-titlebar .usr{margin-left:auto;background:#dde5ee;padding:2px 10px;border-radius:12px;font-size:11px;color:#3c4b5c}
.ui-toolbar{background:#fff;padding:8px 12px;border-bottom:1px solid #e4e9f0;display:flex;gap:8px;flex-wrap:wrap}
.ui-btn{background:#fff;border:1px solid #c8d2dd;border-radius:6px;padding:5px 13px;cursor:pointer;font-size:12px;color:#26384b}
.ui-btn:hover{border-color:#7aa0c8;background:#f4f8fc}.ui-btn.primary{background:#2f6fdb;color:#fff;border-color:#2f6fdb}
.ui-btn.success{background:#1f9d55;color:#fff;border-color:#1f9d55}
.ui-section{font-size:12px;font-weight:700;letter-spacing:1px;color:#5b6b7d;margin:12px 14px 6px;text-transform:uppercase}
.ui-sepline{height:2px;background:linear-gradient(90deg,#2f6fdb,#10b981);margin:2px 14px 10px;border-radius:2px}
.ui-body{padding:4px 14px 14px}
.ui-row{display:flex;flex-wrap:wrap;gap:14px 18px;margin:10px 0}
.ui-field{display:flex;align-items:center;gap:8px;min-width:200px;flex:1 1 220px}
.ui-field label{font-size:12px;color:#52637a;min-width:64px;text-align:right}
.ui-input{background:#fff;border:1px solid #c8d2dd;border-radius:6px;padding:6px 9px;font-size:12px;color:#22303f;flex:1;min-width:90px}
.ui-combo{position:relative;flex:1;min-width:90px}.ui-combo .ui-input{padding-right:26px}
.ui-combo::after{content:"▾";position:absolute;right:9px;top:50%;transform:translateY(-50%);color:#6b7a8c;pointer-events:none}
.ui-date::after{content:"▦";position:absolute;right:9px;top:50%;transform:translateY(-50%);color:#6b7a8c;pointer-events:none}
.ui-switch{display:inline-flex;align-items:center;gap:7px;cursor:pointer}
.ui-switch .track{width:34px;height:18px;background:#c8d2dd;border-radius:10px;position:relative;transition:.2s}
.ui-switch .track::after{content:"";position:absolute;width:14px;height:14px;border-radius:50%;background:#fff;top:2px;left:2px;transition:.2s}
.ui-switch.on .track{background:#1f9d55}.ui-switch.on .track::after{left:18px}
.ui-list{background:#fff;border:1px solid #d8e0ea;border-radius:8px;overflow:hidden;margin-top:4px}
.ui-list .head{display:flex;background:#eef2f7;font-weight:600;font-size:11.5px;color:#4a5a6c;border-bottom:1px solid #d8e0ea}
.ui-list .head span,.ui-list .row span{padding:7px 10px;flex:1;border-right:1px solid #e8edf3;white-space:nowrap}
.ui-list .row{display:flex;font-size:12px;color:#33455a}.ui-list .row:nth-child(even){background:#f7fafc}
.ui-progress{height:8px;background:#e3e9f1;border-radius:6px;overflow:hidden;margin:18px 0}
.ui-progress .bar{height:100%;width:0;background:linear-gradient(90deg,#2f6fdb,#10b981);border-radius:6px;animation:load 1.4s ease forwards}
@keyframes load{to{width:86%}}
.ui-brand{padding:60px 40px;text-align:center;color:#33455a}
.ui-brand .logo{font-size:30px;font-weight:800;letter-spacing:2px}
.ui-brand .tag{color:#7a8a9d;margin-top:8px;font-size:13px}
.ui-ph{color:#9fb0c1;font-size:11px}
.modal-mask{position:fixed;inset:0;background:rgba(30,60,90,.28);display:none;z-index:99}
.modal{position:fixed;top:12%;left:50%;transform:translateX(-50%);width:640px;max-width:92vw;background:var(--panel);border:1px solid var(--line);border-radius:12px;box-shadow:var(--shadow);z-index:100}
.modal .mhead{padding:12px 16px;border-bottom:1px solid var(--line);display:flex;align-items:center;gap:10px}
.modal input{flex:1;background:var(--bg);border:1px solid var(--line);border-radius:8px;padding:8px 12px;color:var(--text);outline:none}
.modal .mbody{max-height:56vh;overflow:auto;padding:8px}
.sres{padding:8px 12px;border-radius:8px;cursor:pointer;display:flex;gap:10px;align-items:center}
.sres:hover,.sres.sel{background:var(--panel3)}
.sres .rt{font-size:11px;width:58px;flex:0 0 58px}.sres .nm{flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.sres .id{color:var(--dim);font-size:11px;font-family:Consolas,monospace}
.hl{background:rgba(245,158,11,.35);border-radius:2px}
</style>
</head>
<body>
<div class="topbar">
  <div class="brand">本体模型 · <b>UI 调用链追踪工作台</b></div>
  <div class="searchbox"><input id="searchInput" placeholder="全局搜索（名称 / ID / 类型）…"><span class="kbd">Ctrl+K</span></div>
  <div class="badges" id="badges"></div>
  <button class="toolbtn" id="btnExpandAll">▾ 全部展开</button>
  <button class="toolbtn" id="btnCollapseAll">▸ 全部折叠</button>
</div>
<div class="main">
  <div class="left" id="treeRoot"></div>
  <div class="splitter" id="splitter" title="拖动调整左侧宽度"></div>
  <div class="right" id="detailRoot"><div class="card" style="text-align:center;color:var(--muted)">从左侧选择一个节点查看详情</div></div>
</div>
<div class="modal-mask" id="mask" onclick="closeSearch()"></div>
<div class="modal" id="modal" style="display:none">
  <div class="mhead"><b>搜索</b><input id="q" placeholder="输入关键字…" autocomplete="off"><button class="toolbtn" onclick="closeSearch()">关闭</button></div>
  <div class="mbody" id="qres"></div>
</div>

<script>
/* ═════════════ 数据注入（生成程序填充） ═════════════ */
const MODEL = __MODEL_JSON__;
const STATS = MODEL.stats || {};
const M = MODEL.models || {};
const M1=M["m1-object-model.yaml"]||{}, M2=M["m2-behavior-model.yaml"]||{}, M3=M["m3-rule-model.yaml"]||{},
      ME=M["me-event-model.yaml"]||{}, M4=M["m4-scenario-model.yaml"]||{}, M5=M["m5-actor-model.yaml"]||{},
      M6=M["m6-flow-model.yaml"]||{}, M7=M["m7-report-model.yaml"]||{}, MU=M["mu-ui-model.yaml"]||{},
      MM=M["m-mapping-model.yaml"]||{}, MI=M["mi-interface-model.yaml"]||{};

/* ═════════════ 工具 ═════════════ */
function esc(s){return String(s==null?"":s).replace(/[&<>"]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));}
function splitIds(v){if(!v)return[];if(Array.isArray(v))return v.filter(x=>typeof x==="string").flatMap(x=>String(x).split(",").map(t=>t.trim())).filter(Boolean);return String(v).split(",").map(t=>t.trim()).filter(Boolean);}
function cssEsc(s){return String(s).replace(/[^a-zA-Z0-9_-]/g,c=>"\\"+c);}
function findScreen(id){return (MU.screens||[]).find(s=>s.screenId===id);}
function findAgg(id){return (M1.aggregates||[]).find(a=>a.id===id);}
function findBeh(id){return (M2.behaviors||[]).find(b=>b.id===id);}
function findRule(id){return (M3.rules||[]).find(r=>r.id===id);}
function findEvent(id){return (ME.events||[]).find(e=>e.eventId===id);}
function findScenario(id){return (M4.event_scenarios||[]).find(s=>s.id===id);}
function findReport(id){return (M7.query_reports||[]).find(r=>r.id===id);}

/* ═════════════ 树的子节点计算（按需求规则，懒加载） ═════════════ */
function scrChildren(key){ /* scr:{sid} */
  const sid=key.split(":").slice(1).join(":");
  const s=findScreen(sid); if(!s)return[];
  const kids=[];
  const targets=[...new Set((s.navigation||[]).map(n=>n.to).filter(t=>t!=="EXIT"&&findScreen(t)))];
  if(targets.length)kids.push({key:"sub:"+sid,type:"subdir",id:sid+":子界面",label:"子界面",sub:""+targets.length});
  /* 界面 → 直接挂事件（保存合同 / 提交审批 …） */
  (s.events||[]).forEach(e=>kids.push({key:"moev:"+sid+":"+e.eventId,type:"moevent",id:e.eventId,label:e.name||e.eventId,sub:"event"}));
  return kids;
}
function subChildren(key){ /* sub:{sid} */
  const sid=key.split(":").slice(1).join(":");
  const s=findScreen(sid); if(!s)return[];
  return [...new Set((s.navigation||[]).map(n=>n.to).filter(t=>t!=="EXIT"&&findScreen(t)))].map(t=>({key:"chscr:"+sid+":"+t,type:"childscreen",id:t,label:(findScreen(t)?.name||t),sub:t}));
}
function evChildren(key){ /* moev:{sid}:{eventId} → 调用链的每个活动节点 */
  const parts=key.split(":"); const sid=parts[1], eventId=parts.slice(2).join(":");
  const s=findScreen(sid); const ev=s&&(s.events||[]).find(x=>x.eventId===eventId); if(!ev)return[];
  return (ev.callChain||[]).map((st,i)=>chainStepNode(sid,eventId,i,st));
}
function chainStepNode(sid,eventId,i,st){
  const refs=[];
  if(st.behaviorRef&&findBeh(st.behaviorRef))refs.push(findBeh(st.behaviorRef).name||st.behaviorRef);
  if(st.rules&&st.rules.length)refs.push((st.rules||[]).map(r=>findRule(r)?.name||r).join(","));
  if(st.eventRef&&findEvent(st.eventRef))refs.push(findEvent(st.eventRef).eventName||st.eventRef);
  if(st.queryRef&&findReport(st.queryRef))refs.push(findReport(st.queryRef).name||st.queryRef);
  if(st.to&&st.to!=="EXIT"&&findScreen(st.to))refs.push("→ "+((findScreen(st.to).name)||st.to));
  const label=(i+1)+". "+st.step+(refs.length?" · "+refs.join(" · "):"");
  return {key:"cstep:"+sid+":"+eventId+":"+i,type:"chainstep",id:eventId+".步骤"+(i+1),label:label,sub:st.step};
}
function cstepChildren(key){ /* cstep:{sid}:{eventId}:{idx} */
  const p=key.split(":"); const sid=p[1]; const idx=parseInt(p[p.length-1],10);
  const eventId=p.slice(2,p.length-1).join(":");
  const s=findScreen(sid); const ev=s&&(s.events||[]).find(x=>x.eventId===eventId); if(!ev)return[];
  const st=(ev.callChain||[])[idx]; if(!st)return[];
  const kids=[];
  (st.rules||[]).forEach(r=>{if(findRule(r))kids.push({key:"rule:"+r,type:"rule",id:r,label:findRule(r).name||r,sub:"规则"});});
  if(st.behaviorRef&&findBeh(st.behaviorRef))kids.push({key:"beh:"+st.behaviorRef,type:"behavior",id:st.behaviorRef,label:findBeh(st.behaviorRef).name||st.behaviorRef,sub:"行为"});
  if(st.eventRef&&findEvent(st.eventRef))kids.push({key:"ev:"+st.eventRef,type:"eventNode",id:st.eventRef,label:findEvent(st.eventRef).eventName||st.eventRef,sub:"事件"});
  if(st.scenarioRef&&findScenario(st.scenarioRef))kids.push({key:"scn:"+st.scenarioRef,type:"scenario",id:st.scenarioRef,label:findScenario(st.scenarioRef).name||st.scenarioRef,sub:"场景"});
  if(st.queryRef&&findReport(st.queryRef))kids.push({key:"rep:"+st.queryRef,type:"report",id:st.queryRef,label:findReport(st.queryRef).name||st.queryRef,sub:"查询"});
  if(st.reportRef&&findReport(st.reportRef))kids.push({key:"rep:"+st.reportRef,type:"report",id:st.reportRef,label:findReport(st.reportRef).name||st.reportRef,sub:"报表"});
  if(st.to&&st.to!=="EXIT"&&findScreen(st.to))kids.push({key:"scr:"+st.to,type:"screen",id:st.to,label:findScreen(st.to).name+" "+st.to,sub:"跳转"});
  return kids;
}
function behChildren(key){ /* beh:{behaviorId} → 所属对象为子节点 */
  const id=key.split(":").slice(1).join(":");
  const b=findBeh(id); if(!b)return[];
  const kids=[];
  /* 行为 → 所属对象（行为属性中的 ownerEntity）作为子节点 */
  behaviorObjs(b).forEach(o=>{if(findAgg(o))kids.push({key:"agg:"+o,type:"object",id:o,label:findAgg(o).name+" "+findAgg(o).alias,sub:"所属对象"});});
  const rules=splitIds(b.appliedRules).filter(r=>findRule(r));
  if(rules.length)kids.push({key:"rdir:"+id,type:"rdir",id:id+":规则",label:"规则",sub:""+rules.length});
  return kids;
}
function behaviorObjs(b){
  const objs=[];
  if(findAgg(b.ownerEntity))objs.push(b.ownerEntity);
  if(b.queryReportRef){const rep=findReport(b.queryReportRef);
    (rep?.sourceObjects||[]).forEach(so=>{if(findAgg(so.objectRef)&&!objs.includes(so.objectRef))objs.push(so.objectRef);});}
  return objs;
}
function rdirChildren(key){ /* rdir:{behaviorId} */
  const id=key.split(":").slice(1).join(":");
  const b=findBeh(id); if(!b)return[];
  return splitIds(b.appliedRules).filter(r=>findRule(r))
    .map(r=>({key:"rule:"+r,type:"rule",id:r,label:findRule(r).name||r,sub:"规则"}));
}
function odirChildren(key){ /* odir:{behaviorId} */
  const id=key.split(":").slice(1).join(":");
  const b=findBeh(id); if(!b)return[];
  return behaviorObjs(b).map(o=>({key:"agg:"+o,type:"object",id:o,label:(findAgg(o).name+" "+findAgg(o).alias),sub:"对象"}));
}
function aggChildren(key){ /* agg:{aggregateId} */
  const id=key.split(":").slice(1).join(":");
  const a=findAgg(id); if(!a)return[];
  const kids=[];
  (a.entities||[]).forEach(en=>kids.push({key:"ent:"+id+":"+en.name,type:"entity",id:id+"."+en.name,label:"· "+en.name,sub:"子对象"}));
  (a.attributes||[]).forEach(at=>kids.push({key:"atr:"+id+":"+at.name,type:"attribute",id:id+"."+at.name,label:at.label||at.name,sub:at.type}));
  const behs=(M2.behaviors||[]).filter(b=>b.ownerEntity===id);
  if(behs.length)kids.push({key:"bd:"+id,type:"bdir",id:id+":行为",label:"行为",sub:""+behs.length});
  return kids;
}
function bdChildren(key){ /* bd:{aggregateId} */
  const id=key.split(":").slice(1).join(":");
  return (M2.behaviors||[]).filter(b=>b.ownerEntity===id)
    .map(b=>({key:"beh:"+b.id,type:"behavior",id:b.id,label:b.name||b.id,sub:"行为"}));
}
function scnChildren(key){ /* scn:{scenarioId} */
  const id=key.split(":").slice(1).join(":");
  const s=findScenario(id); if(!s)return[];
  return (s.steps||[]).map(st=>({key:"step:"+id+":"+st.stepId,type:"step",id:id+"."+st.stepId,
    label:(st.stepId||"")+" "+st.stepType,sub:(st.behaviorRef||st.eventRef||st.ruleRef||"")}));
}
function stepChildren(key){ /* step:{scenarioId}:{stepId} */
  const parts=key.split(":"); const sid=parts[1], stepId=parts.slice(2).join(":");
  const s=findScenario(sid); const st=s&&(s.steps||[]).find(x=>x.stepId===stepId); if(!st)return[];
  if(st.behaviorRef&&findBeh(st.behaviorRef))return[{key:"beh:"+st.behaviorRef,type:"behavior",id:st.behaviorRef,label:findBeh(st.behaviorRef).name||st.behaviorRef,sub:"行为"}];
  if(st.eventRef&&findEvent(st.eventRef))return[{key:"ev:"+st.eventRef,type:"eventNode",id:st.eventRef,label:findEvent(st.eventRef).eventName||st.eventRef,sub:"事件"}];
  if(st.ruleRef&&findRule(st.ruleRef))return[{key:"rule:"+st.ruleRef,type:"rule",id:st.ruleRef,label:findRule(st.ruleRef).name||st.ruleRef,sub:"规则"}];
  return[];
}
function childrenOf(key){
  const t=key.split(":")[0];
  switch(t){
    case "scr": return scrChildren(key);
    case "chscr": return scrChildren("scr:"+key.split(":").slice(2).join(":"));
    case "sub": return subChildren(key);
    case "moev": return evChildren(key);
    case "cstep": return cstepChildren(key);
    case "beh": return behChildren(key);
    case "rdir": return rdirChildren(key);
    case "odir": return odirChildren(key);
    case "agg": return aggChildren(key);
    case "bd": return bdChildren(key);
    case "scn": return scnChildren(key);
    case "step": return stepChildren(key);
    default: return [];
  }
}

/* 节点描述（供详情/面包屑/定位使用） */
function describe(key){
  const p=key.split(":");
  const t=p[0];
  switch(t){
    case "scr":{const s=findScreen(p.slice(1).join(":"));return{key,type:"screen",id:s.screenId,label:s.name+" "+s.screenId,sub:"screen"};}
    case "chscr":{const s=findScreen(p.slice(2).join(":"));return{key,type:"childscreen",id:p.slice(2).join(":"),label:(s?s.name:p.slice(2).join(":")),sub:p.slice(2).join(":")};}
    case "sub":{const s=findScreen(p.slice(1).join(":"));return{key,type:"subdir",id:s.screenId+":子界面",label:"子界面",sub:"子界面"};}
    case "el":{const sid=p[1],elId=p.slice(2).join(":");const s=findScreen(sid);const el=s&&(s.elements||[]).find(x=>x.id===elId);return{key,type:"eltrigger",id:sid+"."+elId,label:el?(el.label||el.id):elId,sub:el?el.type:""};}
    case "moev":{const sid=p[1],evId=p.slice(2).join(":");const s=findScreen(sid);const ev=s&&(s.events||[]).find(x=>x.eventId===evId);return{key,type:"moevent",id:evId,label:ev?(ev.name||evId):evId,sub:"event"};}
    case "cstep":{const sid=p[1];const idx=parseInt(p[p.length-1],10);const eventId=p.slice(2,p.length-1).join(":");const s=findScreen(sid);const ev=s&&(s.events||[]).find(x=>x.eventId===eventId);const st=ev&&(ev.callChain||[])[idx];return{key,type:"chainstep",id:eventId+".步骤"+(idx+1),label:st?(idx+1)+". "+st.step:eventId+".步骤"+(idx+1),sub:st?st.step:""};}
    case "more":{const s=findScreen(p.slice(1).join(":"));return{key,type:"moredir",id:s.screenId+":更多事件",label:"更多事件",sub:"更多事件"};}
    case "beh":{const b=findBeh(p.slice(1).join(":"));return{key,type:"behavior",id:p.slice(1).join(":"),label:b?(b.name||b.id):p.slice(1).join(":"),sub:"行为"};}
    case "rdir":return{key,type:"rdir",id:p.slice(1).join(":")+":规则",label:"规则",sub:"规则"};
    case "odir":return{key,type:"odir",id:p.slice(1).join(":")+":对象",label:"对象",sub:"对象"};
    case "rule":{const r=findRule(p.slice(1).join(":"));return{key,type:"rule",id:p.slice(1).join(":"),label:r?(r.name||r.id):p.slice(1).join(":"),sub:"规则"};}
    case "agg":{const a=findAgg(p.slice(1).join(":"));return{key,type:"aggregate",id:p.slice(1).join(":"),label:a?(a.name+" "+a.alias):p.slice(1).join(":"),sub:"聚合"};}
    case "ent":{const a=findAgg(p[1]);return{key,type:"entity",id:p[1]+"."+p.slice(2).join("."),label:p.slice(2).join("."),sub:"子对象"};}
    case "atr":{const a=findAgg(p[1]);const at=a&&(a.attributes||[]).find(x=>x.name===p.slice(2).join(":"));return{key,type:"attribute",id:p[1]+"."+p.slice(2).join("."),label:at?(at.label||at.name):p.slice(2).join("."),sub:at?at.type:""};}
    case "bd":return{key,type:"bdir",id:p.slice(1).join(":")+":行为",label:"行为",sub:"行为"};
    case "scn":{const s=findScenario(p.slice(1).join(":"));return{key,type:"scenario",id:p.slice(1).join(":"),label:s?(s.name||s.id):p.slice(1).join(":"),sub:"场景"};}
    case "step":{const s=findScenario(p[1]);const st=s&&(s.steps||[]).find(x=>x.stepId===p.slice(2).join(":"));return{key,type:"step",id:p[1]+"."+p.slice(2).join("."),label:(st?st.stepId:"")+" "+((st&&st.stepType)||""),sub:(st&&(st.behaviorRef||st.eventRef||st.ruleRef))||""};}
    case "ev":{const e=findEvent(p.slice(1).join(":"));return{key,type:"eventNode",id:p.slice(1).join(":"),label:e?(e.eventName||e.eventId):p.slice(1).join(":"),sub:"事件"};}
    case "rep":{const r=findReport(p.slice(1).join(":"));return{key,type:"report",id:p.slice(1).join(":"),label:r?(r.name||r.id):p.slice(1).join(":"),sub:r?r.objectType:""};}
    case "perm":{const q=(M5.permissions||[]).find(x=>x.permissionId===p.slice(1).join(":"));return{key,type:"permission",id:p.slice(1).join(":"),label:q?q.permissionId:p.slice(1).join(":"),sub:"权限"};}
    case "role":{const r=(M5.roles||[]).find(x=>x.roleId===p.slice(1).join(":"));return{key,type:"role",id:p.slice(1).join(":"),label:r?(r.name||r.roleId):p.slice(1).join(":"),sub:"角色"};}
    case "actor":{const a=(M5.actors||[]).find(x=>x.actorId===p.slice(1).join(":"));return{key,type:"actor",id:p.slice(1).join(":"),label:a?a.name:p.slice(1).join(":"),sub:"外部"};}
    case "flow":{const f=(M6.flows||[]).find(x=>x.id===p.slice(1).join(":"));return{key,type:"flow",id:p.slice(1).join(":"),label:f?(f.name||f.id):p.slice(1).join(":"),sub:f?f.flowType:""};}
    case "map":{const mp=(MM.mappings||[]).find(x=>x.id===p.slice(1).join(":"));return{key,type:"mapping",id:p.slice(1).join(":"),label:mp?(mp.objectName+" 映射"):p.slice(1).join(":"),sub:"映射"};}
    case "tbl":{return{key,type:"table",id:p.slice(1).join(":"),label:p.slice(1).join(":"),sub:"表"};}
    case "int":{const it=(MI.interfaces||[]).find(x=>x.interfaceId===p.slice(1).join(":"));return{key,type:"interface",id:p.slice(1).join(":"),label:it?(it.name||it.interfaceId):p.slice(1).join(":"),sub:it?it.interfaceType:""};}
    case "dict":{const d=(M1.data_dictionaries||[]).find(x=>x.id===p.slice(1).join(":"));return{key,type:"dictionary",id:p.slice(1).join(":"),label:d?d.name:p.slice(1).join(":"),sub:"字典"};}
    case "cc":{const c=(MU.cross_cutting||[]).find(x=>x.id===p.slice(1).join(":"));return{key,type:"cross",id:p.slice(1).join(":"),label:c?(c.name||c.id):p.slice(1).join(":"),sub:"横切"};}
    default: return{key,type:"node",id:key,label:key,sub:""};
  }
}

/* ═════════════ 树渲染（懒展开 + 防环） ═════════════ */
let treeState={};
const ICO={screen:"▣",childscreen:"▣",subdir:"▣",eltrigger:"▤",moevent:"⚡",event:"⚡",eventNode:"⚡",chainstep:"➜",
  behavior:"▸",rdir:"▸",odir:"▸",bdir:"▸",moredir:"…",rule:"◆",object:"◉",aggregate:"◉",
  entity:"▥",attribute:"·",scenario:"◈",step:"➤",report:"▤",permission:"✲",flow:"◫",mapping:"▦",
  table:"▦",interface:"⇄",dictionary:"≡",cross:"✳",role:"◍",actor:"◎"};
const TAG={screen:"screen",childscreen:"sub",subdir:"subs",eltrigger:"button",moevent:"event",event:"event",
  eventNode:"event",chainstep:"步骤",behavior:"behavior",rdir:"rules",odir:"objects",bdir:"behaviors",moredir:"more",
  rule:"rule",object:"object",aggregate:"aggregate",entity:"entity",attribute:"attr",scenario:"scenario",
  step:"step",report:"report",permission:"permission",flow:"flow",mapping:"mapping",table:"table",
  interface:"interface",dictionary:"dict",cross:"cross",role:"role",actor:"actor"};
function icon(t){return `<span class="ic ${(ICO[t]||"·").charCodeAt(0)<=128?"o":"o"}">${ICO[t]||"·"}</span>`;}
function tag(t){return `<span class="node-tag tag-${TAG[t]||t}">${TAG[t]||t}</span>`;}
function rowHtml(d,depth,visited){
  visited=visited||{};
  if(visited[d.key])return `<div class="tnode"><div class="trow" style="opacity:.45;cursor:default;padding-left:${6+depth*14}px"><span class="caret"></span>${icon(d.type)}<span class="label">${esc(d.label)}（链路循环）</span></div></div>`;
  const kids=childrenOf(d.key);
  const open=!!treeState[d.key];
  const v=Object.assign({},visited);v[d.key]=true;
  return `<div class="tnode">
    <div class="trow${selKey===d.key?" active":""}" data-trow="${esc(d.key)}" data-depth="${depth}"
      data-label="${esc(d.label)}" data-type="${esc(d.type)}" data-sub="${esc(d.sub||"")}" data-id="${esc(d.id||"")}">
      <span class="caret">${kids.length?(open?"▾":"▸"):""}</span>${icon(d.type)}
      <span class="label">${esc(d.label)}</span>${tag(d.type)}<span class="sub">${esc(d.sub||"")}</span>
    </div>
    ${(kids.length&&open)?`<div class="tchildren">${kids.map(k=>rowHtml(k,depth+1,v)).join("")}</div>`:""}
  </div>`;
}
function rootItems(){
  return [
    {title:"界面模型 UI",items:(MU.screens||[]).map(s=>({key:"scr:"+s.screenId,type:"screen",id:s.screenId,label:s.name+" "+s.screenId,sub:"screen"}))},
    {title:"对象模型 OBJECT",items:(M1.aggregates||[]).map(a=>({key:"agg:"+a.id,type:"aggregate",id:a.id,label:a.name+" "+a.alias,sub:"聚合"}))},
    {title:"场景模型 SCENARIO",items:(M4.event_scenarios||[]).map(s=>({key:"scn:"+s.id,type:"scenario",id:s.id,label:s.name||s.id,sub:"场景"}))},
    {title:"索引 INDEX",items:indexItems()},
  ];
}
function indexItems(){
  const out=[];
  (M2.behaviors||[]).forEach(b=>out.push({key:"beh:"+b.id,type:"behavior",id:b.id,label:(b.name||b.id),sub:"行为"}));
  (M3.rules||[]).forEach(r=>out.push({key:"rule:"+r.id,type:"rule",id:r.id,label:(r.name||r.id),sub:"规则"}));
  (ME.events||[]).forEach(e=>out.push({key:"ev:"+e.eventId,type:"eventNode",id:e.eventId,label:(e.eventName||e.eventId),sub:"事件"}));
  (M7.query_reports||[]).forEach(r=>out.push({key:"rep:"+r.id,type:"report",id:r.id,label:(r.name||r.id),sub:r.objectType}));
  (M5.permissions||[]).forEach(p=>out.push({key:"perm:"+p.permissionId,type:"permission",id:p.permissionId,label:p.permissionId,sub:"权限"}));
  (M6.flows||[]).forEach(f=>out.push({key:"flow:"+f.id,type:"flow",id:f.id,label:(f.name||f.id),sub:f.flowType}));
  (MM.mappings||[]).forEach(mp=>out.push({key:"map:"+mp.id,type:"mapping",id:mp.id,label:(mp.objectName+" 映射"),sub:"映射"}));
  (MI.interfaces||[]).forEach(it=>out.push({key:"int:"+it.interfaceId,type:"interface",id:it.interfaceId,label:(it.name||it.interfaceId),sub:it.interfaceType}));
  (M1.data_dictionaries||[]).forEach(d=>out.push({key:"dict:"+d.id,type:"dictionary",id:d.id,label:d.name,sub:"字典"}));
  (MU.cross_cutting||[]).forEach(c=>out.push({key:"cc:"+c.id,type:"cross",id:c.id,label:(c.name||c.id),sub:"横切"}));
  return out;
}
let selKey=null;
function buildTree(){
  const root=document.getElementById("treeRoot");
  root.innerHTML=rootItems().map(r=>`<div class="tree"><div class="root-t">${r.title}</div>${r.items.map(d=>rowHtml(d,0)).join("")}</div>`).join("");
}
function toggle(key){
  const kids=childrenOf(key);
  const open=!treeState[key];
  treeState[key]=open;
  document.querySelectorAll(`[data-trow="${cssEsc(key)}"]`).forEach(row=>{
    const tnode=row.closest(".tnode"); const depth=parseInt(row.getAttribute("data-depth")||0,10);
    row.querySelector(".caret").textContent=kids.length?(open?"▾":"▸"):"";
    let tc=tnode.querySelector(":scope > .tchildren");
    if(!tc){tc=document.createElement("div");tc.className="tchildren";tnode.appendChild(tc);}
    tc.style.display=open?"block":"none";
    tc.innerHTML=open?kids.map(k=>rowHtml(k,depth+1)).join(""):"";
  });
  selectNode(key);
}
function selectNode(key){
  if(!key)return;
  selKey=key;
  document.querySelectorAll("[data-trow]").forEach(el=>el.classList.toggle("active",el.getAttribute("data-trow")===key));
  const d=describe(key);
  const detail=document.getElementById("detailRoot");
  detail.innerHTML=`<h2>${esc(d.label)} ${tag(d.type)}</h2>
    <div class="crumb" id="crumb"></div>
    <button class="toolbtn" style="margin-bottom:14px" onclick="copyId('${esc(d.id)}')">复制 ID：${esc(d.id)}</button>`+renderDetail(d)+`<div style="height:40px"></div>`;
  crumbs=[d];renderCrumb();
  detail.scrollTop=0;
}
let crumbs=[];
function pushCrumb(key){crumbs.push(describe(key));renderCrumb();}
function renderCrumb(){const el=document.querySelector(".right .crumb");if(!el)return;
  el.innerHTML=crumbs.map((c,i)=>i>0?" <span style='color:var(--dim)'>/</span> "+`<a data-key="${esc(c.key)}">${esc(c.label)}</a>`:`<a data-key="${esc(c.key)}">${esc(c.label)}</a>`).join("");}
function copyId(id){navigator.clipboard?.writeText(id).then(()=>{});}
function expandAll(){
  treeState={}; const seen=new Set(); const q=[];
  rootItems().forEach(r=>r.items.forEach(d=>q.push(d.key)));
  while(q.length){const k=q.shift();if(seen.has(k))continue;seen.add(k);
    const kids=childrenOf(k);if(kids.length){treeState[k]=true;kids.forEach(kd=>q.push(kd.key));}}
  buildTree();
}
function collapseAll(){treeState={};buildTree();}

/* ═════════════ 引用穿透（点击 data-ref 定位） ═════════════ */
function keyOfId(id){
  if(findBeh(id))return"beh:"+id;
  if(findRule(id))return"rule:"+id;
  if(findEvent(id))return"ev:"+id;
  if(findScenario(id))return"scn:"+id;
  if(findReport(id))return"rep:"+id;
  if(findAgg(id))return"agg:"+id;
  if((M5.permissions||[]).some(p=>p.permissionId===id))return"perm:"+id;
  if((M5.roles||[]).some(r=>r.roleId===id))return"role:"+id;
  if((M6.flows||[]).some(f=>f.id===id))return"flow:"+id;
  if((MI.interfaces||[]).some(i=>i.interfaceId===id))return"int:"+id;
  if((M1.data_dictionaries||[]).some(d=>d.id===id))return"dict:"+id;
  if((MM.mappings||[]).some(m=>m.id===id))return"map:"+id;
  // 表
  for(const mp of (MM.mappings||[])){for(const tb of (mp.tableMappings||[])){if(tb.tableName===id)return"tbl:"+tb.tableName;}}
  // 外部实体/角色
  if((M5.actors||[]).some(a=>a.actorId===id))return"actor:"+id;
  // 屏幕
  if(findScreen(id))return"scr:"+id;
  // 屏幕元素（screen.element）
  const dot=id.indexOf(".");
  if(dot>0){const sid=id.slice(0,dot),elId=id.slice(dot+1);
    const s=findScreen(sid);if(s&&(s.elements||[]).some(el=>el.id===elId))return"el:"+sid+":"+elId;}
  // 场景步骤（scenario.stepId）
  if(dot>0){const sid=id.slice(0,dot),stId=id.slice(dot+1);
    const s=findScenario(sid);if(s&&(s.steps||[]).some(st=>st.stepId===stId))return"step:"+sid+":"+stId;}
  // MU 事件
  for(const s of (MU.screens||[])){const ev=(s.events||[]).find(e=>e.eventId===id);if(ev)return"moev:"+s.screenId+":"+id;}
  return null;
}
document.addEventListener("click",e=>{
  const p=e.target.closest("[data-ref]");
  if(p){e.preventDefault();const k=keyOfId(p.getAttribute("data-ref"));if(k){pushCrumb(k);selectNode(k);}return;}
  const r=e.target.closest("[data-key]");
  if(r){e.preventDefault();const k=r.getAttribute("data-key");selectNode(k);return;}
  const row=e.target.closest(".trow");
  if(row){e.stopPropagation();toggle(row.getAttribute("data-trow"));}
});

/* ═════════════ 详情渲染（按节点类型） ═════════════ */
function renderDetail(d){
  switch(d.type){
    case "screen": case "childscreen": return renderScreen(d);
    case "subdir": return renderSubdir(d);
    case "moredir": return renderMoredir(d);
    case "eltrigger": return renderElement(d);
    case "moevent": return renderEvent(d);
    case "chainstep": return renderChainStep(d);
    case "behavior": return renderBehavior(d);
    case "rdir": return renderObjOrRuleDir(d,"rdir");
    case "odir": return renderObjOrRuleDir(d,"odir");
    case "bdir": return renderBdir(d);
    case "rule": return renderRule(d);
    case "object": case "aggregate": return renderAggregate(d);
    case "entity": return renderEntity(d);
    case "attribute": return renderAttribute(d);
    case "scenario": return renderScenario(d);
    case "step": return renderStep(d);
    case "eventNode": return renderEventNode(d);
    case "report": return renderReport(d);
    case "permission": return renderPermission(d);
    case "role": return renderRole(d);
    case "actor": return renderActor(d);
    case "flow": return renderFlow(d);
    case "mapping": return renderMapping(d);
    case "table": return renderTable(d);
    case "interface": return renderInterface(d);
    case "dictionary": return renderDictionary(d);
    case "cross": return renderCross(d);
    default: return card("节点",`<div class="kv">${kvd("ID",esc(d.id))}${kvd("标签",esc(d.label))}</div>`);
  }
}
function card(t,b){return `<div class="card"><h3>${t}</h3>${b}</div>`;}
function kvd(k,v){return `<div class="k">${esc(k)}</div><div class="v">${v}</div>`;}
function ref(id){const k=keyOfId(id);if(!k)return`<span class="pill dangle">${esc(id)}</span>`;return`<span class="pill" data-ref="${esc(id)}">${esc(id)}</span>`;}
function renderObjOrRuleDir(d,kind){
  const id=d.key.split(":")[1];
  const b=findBeh(id);
  const items=kind==="rdir"?splitIds(b.appliedRules).filter(r=>findRule(r)).map(r=>({id:r,label:findRule(r).name||r}))
    :behaviorObjs(b).map(o=>({id:o,label:findAgg(o).name+" "+findAgg(o).alias}));
  return card(kind==="rdir"?"规则目录":"对象目录",
    `<div class="kv">${kvd("所属行为",ref(id))}${kvd("数量",items.length)}</div>`+
    card("成员",items.map(i=>`<span class="pill" data-ref="${esc(i.id)}">${esc(i.label)}</span>`).join(" ")||"—"));
}
function renderBdir(d){
  const id=d.key.split(":")[1];
  const behs=(M2.behaviors||[]).filter(b=>b.ownerEntity===id);
  return card("行为目录",`<div class="kv">${kvd("所属对象",ref(id))}${kvd("数量",behs.length)}</div>`+
    card("行为",behs.map(b=>`<span class="pill" data-ref="${esc(b.id)}">${esc(b.name||b.id)}</span>`).join(" ")));
}
function renderSubdir(d){
  const sid=d.id.replace(":子界面","");
  const s=findScreen(sid);
  const targets=[...new Set((s.navigation||[]).map(n=>n.to).filter(t=>t!=="EXIT"&&findScreen(t)))];
  return card("子界面",`<div class="kv">${kvd("父界面",ref(sid))}</div>`+
    card("子界面",targets.map(t=>`<span class="pill" data-ref="${esc(t)}">${esc(findScreen(t).name)}（${esc(t)}）</span>`).join(" ")||"—"));
}
function renderMoredir(d){
  const sid=d.id.replace(":更多事件","");
  const s=findScreen(sid);
  const srcEls=[...new Set((s.events||[]).map(e=>((e.source||"").split(".")[0]).trim()).filter(Boolean))];
  const evs=(s.events||[]).filter(e=>{const s0=((e.source||"").split(".")[0]).trim();return !s0||!srcEls.includes(s0);});
  return card("更多事件",`<div class="kv">${kvd("所属界面",ref(sid))}</div>`+
    card("事件",evs.map(e=>`<span class="pill" data-ref="${esc(e.eventId)}">${esc(e.name||e.eventId)}</span>`).join(" ")));
}
function renderEntity(d){
  const id=d.id.split(".")[0];
  const a=findAgg(id);
  const en=(a.entities||[]).find(x=>x.name===d.label.replace("· ",""));
  return card("子对象（实体）",`<div class="kv">${kvd("所属聚合",ref(id))}${kvd("名称",esc(en?.name||"—"))}
    ${kvd("基数",esc(en?.cardinality||"—"))}${kvd("级联删除",en?.cascadeDelete?"是":"—")}
    ${kvd("说明",esc(en?.description||"—"))}</div>`+
    (en?.attributes?.length?card("属性",`<table class="tbl"><tr><th>属性</th><th>类型</th><th>必填</th></tr>`+
      en.attributes.map(at=>`<tr><td class="mono">${esc(at.name)}</td><td>${esc(at.type||"—")}</td><td>${at.required?"是":"—"}</td></tr>`).join("")+"</table>"):""));
}
function renderAttribute(d){
  const id=d.id.split(".")[0];
  const a=findAgg(id);
  const at=(a.attributes||[]).find(x=>x.name===d.id.split(".").slice(1).join("."));
  return card("属性",`<div class="kv">${kvd("所属聚合",ref(id))}${kvd("属性",esc(at?.name||d.label))}
    ${kvd("标签",esc(at?.label||"—"))}${kvd("类型",esc(at?.type||"—"))}${kvd("必填",at?.required?"是":"—")}
    ${kvd("唯一",at?.unique?"是":"—")}${kvd("约束",esc(at?.description||"—"))}</div>`);
}
function renderStep(d){
  const id=d.id.split(".")[0];
  const s=findScenario(id);
  const st=(s.steps||[]).find(x=>x.stepId===d.id.split(".").slice(1).join("."));
  return card("场景步骤",`<div class="kv">${kvd("场景",ref(id))}${kvd("步骤ID",esc(st?.stepId||"—"))}
    ${kvd("步骤类型",esc(st?.stepType||"—"))}${kvd("行为",st?.behaviorRef?ref(st.behaviorRef):"—")}
    ${kvd("事件",st?.eventRef?ref(st.eventRef):"—")}${kvd("规则",st?.ruleRef?ref(st.ruleRef):"—")}
    ${kvd("后继",esc((st?.nextSteps||[]).join(", "))||"—")}</div>`);
}
/* —— screen：右侧直接渲染界面原型 —— */
function renderScreen(d){
  const s=findScreen(d.id); if(!s)return"";
  let h=card("屏幕信息",`<div class="kv">${kvd("screenId",esc(s.screenId))}${kvd("名称",esc(s.name))}${kvd("来源",esc(s.screenRef||"—"))}</div>`);
  h+=card("界面原型",
    `<div class="uv-tools"><button class="active" id="uvBtn0" onclick="setUv(0)">现代渲染</button>
     <button id="uvBtn1" onclick="setUv(1)">原始 ASCII</button><span style="flex:1"></span>
     <button onclick="uvZoom(-1)">A-</button><button onclick="uvZoom(1)">A+</button></div><div id="uvHost"></div>`);
  h+=card("界面元素",`<table class="tbl"><tr><th>ID</th><th>类型</th><th>IO</th><th>必填</th><th>数据绑定</th><th>权限</th></tr>`+
    (s.elements||[]).map(el=>`<tr><td class="mono">${esc(el.id)}</td><td>${esc(el.type||"—")}</td><td>${esc(el.io||"—")}</td><td>${el.required?"是":"—"}</td>
      <td>${el.dataBinding?`<span class="pill" data-ref="${esc(el.dataBinding.split(".")[0])}">${esc(el.dataBinding)}</span>`:"—"}</td>
      <td>${splitIds(el.permissionRef).map(p=>ref(p)).join("")||"—"}</td></tr>`).join("")+"</table>");
  h+=card("操作事件",`<table class="tbl"><tr><th>事件</th><th>名称</th><th>触发源</th><th>调用链</th></tr>`+
    (s.events||[]).map(ev=>`<tr><td class="mono"><span class="pill" data-ref="${esc(ev.eventId)}">${esc(ev.eventId)}</span></td>
      <td>${esc(ev.name||"—")}</td><td>${esc(ev.source||"—")}</td><td>${chainBar(ev.callChain)}</td></tr>`).join("")+"</table>");
  h+=card("导航",`<table class="tbl"><tr><th>目标</th><th>触发</th></tr>`+
    (s.navigation||[]).map(nv=>`<tr><td>${nv.to==="EXIT"?"EXIT":`<span class="pill" data-ref="${esc(nv.to)}">${esc(nv.to)}</span>`}</td><td>${esc(nv.trigger||"—")}</td></tr>`).join("")+"</table>");
  return h;
}
let uvMode=0,uvFont=11.5;
function setUv(m){uvMode=m;document.getElementById("uvBtn0").classList.toggle("active",m===0);
  document.getElementById("uvBtn1").classList.toggle("active",m===1);
  const k=crumbs[crumbs.length-1]; if(k&&(k.type==="screen"||k.type==="childscreen")){const s=findScreen(k.id);
    document.getElementById("uvHost").innerHTML=uvMode===0?renderModernUI(s):rawAscii(s);}}
function uvZoom(d){uvFont=Math.max(8,Math.min(18,uvFont+d));document.querySelectorAll("#uvHost pre.ascii, #uvHost .ui-zoom").forEach(e=>e.style.fontSize=uvFont+"px");}
function isGridToken(id){return /^(grd|lst)/i.test(id);}
function extractTokens(line){
  const toks=[]; const push=(id,txt)=>{if(!toks.some(t=>t.id===id))toks.push({id,txt:(txt||"").trim()});};
  for(const m of line.matchAll(/\[([A-Za-z]\w*)(?:\s+([^\]]*))?\]/g))push(m[1],m[2]);
  for(const m of line.matchAll(/\(([A-Za-z]\w*)(?:\s+([^)]*))?\)/g))push(m[1],m[2]);
  for(const m of line.matchAll(/@([A-Za-z]\w*)/g))push(m[1],"");
  for(const m of line.matchAll(/\b(lbl[A-Za-z]\w*)\b/g))push(m[1],"");
  return toks;
}
function inferType(id,el){if(el&&el.type)return el.type;
  if(/^cbo/i.test(id))return"COMBO";if(/^dtp/i.test(id))return"DATEPICKER";if(/^chk/i.test(id))return"CHECKBOX";
  if(/^rad/i.test(id))return"RADIO";if(/^btn/i.test(id))return"BUTTON";if(/^(grd|lst)/i.test(id))return"GRID";
  if(/^lbl/i.test(id))return"LABEL";if(/^(txt|edt)/i.test(id))return"TEXTBOX";if(/^tbr/i.test(id))return"TOOLBAR";
  if(/^tmr/i.test(id))return"TIMER";if(/^tab/i.test(id))return"TAB";return"TEXTBOX";}
function parseAsciiRows(s){
  const lines=(s.layout||"").split("\n"); const rows=[];
  for(const raw of lines){
    const line=raw.replace(/[┌─┐└┘│├┤┬┴║═╔╗╚╝]/g," ").trim(); if(!line)continue;
    const region=line.match(/\[区域:\s*([^\]]+)\]/);
    if(region){rows.push({kind:"section",text:region[1]});continue;}
    if(line.includes("|")){const cb=line.match(/\[(chk\w+)\]/);
      const cols=line.replace(/\[[^\]]*\]/g," ").split("|").map(x=>x.trim()).filter(Boolean);
      rows.push({kind:"columns",cols,checkbox:cb?cb[1]:null});continue;}
    const tokens=extractTokens(line);
    if(tokens.length){rows.push({kind:"row",tokens});continue;}
    rows.push({kind:"text",text:line});
  }
  const out=[]; let lastGrid=-1;
  for(let i=0;i<rows.length;i++){const r=rows[i];
    if(r.kind==="row"&&r.tokens.some(t=>isGridToken(t.id)))lastGrid=i;
    if(r.kind==="columns"){if(lastGrid>=0){rows[lastGrid].columns=r.cols;rows[lastGrid].checkbox=r.checkbox;}continue;}
    out.push(r);}
  return out;
}
function rawAscii(s){return `<pre class="ascii" style="font-size:${uvFont}px">${esc(s.layout||"(无 ASCII 布局)")}</pre>`;}
function renderModernUI(s){
  const rows=parseAsciiRows(s);
  if(!rows.length)return `<div class="ui-win"><div class="ui-titlebar"><div class="ui-dots"><span class="ui-dot-r"></span><span class="ui-dot-y"></span><span class="ui-dot-g"></span></div><span class="t">${esc(s.name)}</span><span class="st">${esc(s.screenId)}</span></div><div class="ui-brand ui-zoom"><div class="logo">${esc(s.name)}</div><div class="tag">${esc(s.screenId)}</div><div class="ui-progress"><div class="bar"></div></div></div></div>`;
  let h=`<div class="ui-win ui-zoom">`;
  h+=`<div class="ui-titlebar"><div class="ui-dots"><span class="ui-dot-r"></span><span class="ui-dot-y"></span><span class="ui-dot-g"></span></div><span class="t">${esc(s.name)}</span><span class="st">${esc(s.screenId)}</span><span class="usr">操作员</span></div>`;
  const tb=(s.elements||[]).find(el=>el.type==="TOOLBAR");
  if(tb&&tb.label)h+=`<div class="ui-toolbar">${String(tb.label).split("|").map(x=>x.trim()).filter(Boolean).map((x,i)=>`<button class="ui-btn ${i===0?"primary":""}">${esc(x)}</button>`).join("")}</div>`;
  const elsById={};(s.elements||[]).forEach(el=>elsById[el.id]=el);
  for(const r of rows){
    if(r.kind==="section"){h+=`<div class="ui-section">${esc(r.text)}</div><div class="ui-sepline"></div>`;continue;}
    if(r.kind==="text"){h+=`<div class="ui-body" style="color:#52637a;padding:4px 14px">${esc(r.text)}</div>`;continue;}
    if(r.kind==="row"){const grid=r.tokens.find(t=>isGridToken(t.id));
      if(grid){h+=`<div class="ui-body">${renderGrid(grid.id,elsById[grid.id],r.columns,r.checkbox,grid.txt)}</div>`;continue;}
      h+=`<div class="ui-body"><div class="ui-row">${r.tokens.map(t=>renderToken(t.id,t.txt,elsById[t.id])).join("")}</div></div>`;}
  }
  return h+"</div>";
}
function renderGrid(id,el,cols,checkbox,lbl){const label=lbl||(el?el.label:"")||id;
  let header=cols&&cols.length?cols.slice():[label];if(checkbox)header=["☐ "+header[0]].concat(header.slice(1));
  const empty=3;
  return `<div class="ui-list" style="margin-top:6px"><div class="head">${header.map(c=>`<span>${esc(c)}</span>`).join("")}</div>${Array.from({length:empty},()=>`<div class="row">${header.map(()=>`<span></span>`).join("")}</div>`).join("")}<div style="padding:6px 10px;color:#9fb0c1;font-size:11px">${esc(id)}</div></div>`;}
function renderToken(id,txt,el){const type=inferType(id,el);const lbl=txt||(el?el.label:"")||id;const ph=`<span class="ui-ph">${esc(id)}</span>`;
  if(type==="BUTTON"){const t2=lbl||"按钮";return `<button class="ui-btn ${/保存|提交|新增|确定|查询/.test(t2)?"primary":/删除|作废|冲销/.test(t2)?"":"success"}">${esc(t2)}</button>`;}
  if(type==="TOOLBAR")return"";
  if(type==="COMBO")return `<div class="ui-field"><label>${esc(lbl)}</label><div class="ui-combo"><div class="ui-input">${ph}</div></div></div>`;
  if(type==="DATEPICKER")return `<div class="ui-field"><label>${esc(lbl)}</label><div class="ui-combo ui-date"><div class="ui-input">${ph}</div></div></div>`;
  if(type==="CHECKBOX"||type==="RADIO")return `<div class="ui-field"><label>${esc(lbl)}</label><span class="ui-switch"><span class="track"></span>${ph}</span></div>`;
  if(type==="GRID"||type==="LISTVIEW")return `<div class="ui-field" style="flex:1 1 100%"><label>${esc(lbl)}</label><div class="ui-list"><div class="head"><span>${ph}</span></div></div></div>`;
  if(type==="LABEL")return `<div class="ui-field"><label>${esc(lbl)}</label><div class="ui-input" style="background:#f0f4f9;color:#5b6b7d">${ph}</div></div>`;
  if(type==="TEXTAREA")return `<div class="ui-field" style="flex:1 1 100%"><label>${esc(lbl)}</label><div class="ui-input" style="min-height:54px">${ph}</div></div>`;
  if(type==="TAB")return `<div class="ui-field" style="flex:1 1 100%"><span class="ui-btn" style="color:#2f6fdb">▸ ${esc(lbl)}</span></div>`;
  return `<div class="ui-field"><label>${esc(lbl)}</label><div class="ui-input">${ph}</div></div>`;}
/* —— element / event / behavior / aggregate / table / rule / eventNode / scenario / report / permission / flow / mapping / interface / dict / cross / role / actor —— */
function renderElement(d){const sid=d.id.split(".")[0],elId=d.id.split(".").slice(1).join(".");
  const s=findScreen(sid);const el=s&&(s.elements||[]).find(x=>x.id===elId);if(!el)return"";
  return card("界面元素（触发控件）",`<div class="kv">${kvd("所属界面",ref(sid))}${kvd("ID",esc(el.id))}${kvd("标签",esc(el.label||"—"))}
    ${kvd("类型",esc(el.type||"—"))}${kvd("IO",esc(el.io||"—"))}${kvd("必填",el.required?"是":"—")}
    ${kvd("数据绑定",el.dataBinding?`<span class="pill" data-ref="${esc(el.dataBinding.split(".")[0])}">${esc(el.dataBinding)}</span>`:"—")}
    ${kvd("权限",splitIds(el.permissionRef).map(p=>ref(p)).join("")||"—")}</div>`);}
function renderEvent(d){const sid=d.id.split(".")[0];const s=findScreen(sid);const ev=s&&(s.events||[]).find(x=>x.eventId===d.id);if(!ev)return"";
  let h=card("UI 事件",`<div class="kv">${kvd("事件ID",`<span class="mono">${esc(ev.eventId)}</span>`)}${kvd("名称",esc(ev.name||"—"))}
    ${kvd("所属界面",ref(sid))}${kvd("触发源",esc(ev.source||"—"))}${kvd("权限",splitIds(ev.permissions).map(p=>ref(p)).join("")||"—")}</div>`);
  h+=card("调用链",chainBar(ev.callChain));
  h+=card("调用链明细",`<div class="kv">${(ev.callChain||[]).map((st,i)=>kvd("步骤 "+(i+1)+" "+st.step,chainStepBody(st))).join("")}</div>`);
  return h;}
function renderChainStep(d){const p=d.key.split(":");const sid=p[1];const idx=parseInt(p[p.length-1],10);
  const eventId=p.slice(2,p.length-1).join(":");const s=findScreen(sid);const ev=s&&(s.events||[]).find(x=>x.eventId===eventId);
  const st=ev&&(ev.callChain||[])[idx]; if(!st)return"";
  let h=card("调用链步骤",`<div class="kv">${kvd("步骤序号",idx+1)}${kvd("步骤类型",`<span class="mono">${esc(st.step)}</span>`)}
    ${kvd("所属事件",ref(eventId))}${kvd("所属界面",ref(sid))}</div>`);
  const body=chainStepBody(st);
  if(body!=="本地步骤")h+=card("步骤引用",`<div class="kv">${body}</div>`);
  return h;}
function chainBar(chain){return `<div class="chain">${(chain||[]).map((st,i)=>`<span class="chstep"><span class="stepno">${i+1}</span>${esc(st.step)}<span class="arrow">${chainStepBody(st)}</span></span>`+(i<(chain||[]).length-1?`<span class="charrow">→</span>`:"")).join("")}</div>`;}
function chainStepBody(st){const p=[];
  if(st.rules&&st.rules.length)p.push("规则:"+st.rules.map(r=>ref(r)).join(" "));
  if(st.behaviorRef)p.push("行为:"+ref(st.behaviorRef));
  if(st.eventRef)p.push("事件:"+ref(st.eventRef));
  if(st.scenarioRef)p.push("场景:"+ref(st.scenarioRef));
  if(st.queryRef)p.push("查询:"+ref(st.queryRef));
  if(st.reportRef)p.push("报表:"+ref(st.reportRef));
  if(st.to)p.push("跳转:"+(st.to==="EXIT"?"EXIT":ref(st.to)));
  if(st.targets)p.push("启用:"+st.targets.map(esc).join(", "));
  return p.join(" · ")||"本地步骤";}
function renderBehavior(d){const b=findBeh(d.id);if(!b)return"";
  let h=card("行为",`<div class="kv">${kvd("ID",`<span class="mono">${esc(b.id)}</span>`)}${kvd("名称",esc(b.name||"—"))}
    ${kvd("所属对象",ref(b.ownerEntity))}${kvd("行为类型",esc(b.behaviorType||"—"))}${kvd("触发类型",esc(b.triggerType||"—"))}
    ${kvd("规则",splitIds(b.appliedRules).map(r=>ref(r)).join("")||"—")}${kvd("权限",splitIds(b.requiredPermissions).map(p=>ref(p)).join("")||"—")}
    ${kvd("事件",splitIds(b.producedEvents).map(e=>ref(e)).join("")||"—")}${kvd("报表",b.queryReportRef?ref(b.queryReportRef):"—")}
    ${kvd("UI 入口",splitIds(b.uiEventRefs).map(e=>ref(e)).join("")||"—")}${b.description?kvd("说明",esc(b.description)):""}</div>`);
  h+=card("前置条件",(b.preconditions||[]).map(p=>`<li>${esc(p)}</li>`).join("")||"—");
  if(b.postconditions&&b.postconditions.length)h+=card("后置状态变更",`<div class="kv">${b.postconditions.map(p=>kvd(esc(p.field||"—"),esc(p.setValue||"—"))).join("")}</div>`);
  return h;}
function renderAggregate(d){const a=findAgg(d.id);if(!a)return"";
  const maps=(MM.mappings||[]).filter(m=>m.objectRef===a.id)||[];
  let h=card("聚合对象",`<div class="kv">${kvd("ID",`<span class="mono">${esc(a.id)}</span>`)}${kvd("名称",esc(a.name||"—"))}
    ${kvd("类型",esc(a.aggregateType||"—"))}${kvd("说明",esc(a.description||"—"))}${kvd("生命周期",esc((a.lifecycle||[]).join(" → ")))}</div>`);
  if(maps.length){h+=card("数据库表（MM 映射）",maps.map(mp=>`<div style="margin:3px 0">${ref(mp.id)} → ${(mp.tableMappings||[]).map(t=>`<span class="pill" data-ref="${esc(t.tableName)}">${esc(t.tableName)} (${esc(t.tableRole||"—")})</span>`).join(" + ")}</div>`).join(""));
    const first=maps[0].tableMappings&&maps[0].tableMappings[0];
    if(first)h+=card("表列映射",`<table class="tbl"><tr><th>字段</th><th>列</th><th>类型</th><th>主键</th><th>外键</th><th>目标表</th></tr>`+
      (first.columnMappings||[]).map(c=>`<tr><td class="mono">${esc(c.attributeRef||"—")}</td><td class="mono">${esc(c.column||"—")}</td><td>${esc(c.columnType||"—")}</td><td>${c.isPrimaryKey?"✓":""}</td><td>${c.isForeignKey?"✓":""}</td><td>${c.fkTargetTable?ref(c.fkTargetTable):"—"}</td></tr>`).join("")+"</table>");}
  h+=card("属性",`<table class="tbl"><tr><th>属性</th><th>标签</th><th>类型</th><th>必填</th><th>唯一</th><th>约束</th></tr>`+
    (a.attributes||[]).map(at=>`<tr><td class="mono">${esc(at.name)}</td><td>${esc(at.label||"—")}</td><td>${esc(at.type||"—")}</td><td>${at.required?"是":"—"}</td><td>${at.unique?"是":"—"}</td><td>${esc(at.description||"—")}</td></tr>`).join("")+"</table>");
  if(a.entities&&a.entities.length)h+=card("子对象",`<table class="tbl"><tr><th>名称</th><th>基数</th><th>说明</th></tr>`+a.entities.map(en=>`<tr><td>${esc(en.name)}</td><td>${esc(en.cardinality||"—")}</td><td>${esc(en.description||"—")}</td></tr>`).join("")+"</table>");
  if(a.invariants&&a.invariants.length)h+=card("对象不变量",(a.invariants||[]).map(iv=>`<li>${esc(iv.name||"—")} <span class="mono" style="color:var(--amber)">${esc(iv.expression||"")}</span></li>`).join(""));
  const assocs=(M1.aggregate_associations||[]).filter(x=>x.sourceAggregate===a.id||x.targetAggregate===a.id);
  if(assocs.length)h+=card("关联",`<table class="tbl"><tr><th>关联</th><th>基数</th><th>引用字段</th></tr>`+assocs.map(x=>`<tr><td>${esc(x.sourceRole)} → ${ref(x.targetAggregate)}</td><td>${esc(x.cardinality||"—")}</td><td class="mono">${esc(x.referenceField||"—")}</td></tr>`).join("")+"</table>");
  const behs=(M2.behaviors||[]).filter(b=>b.ownerEntity===a.id);
  if(behs.length)h+=card("提供的行为",behs.map(b=>`<span class="pill" data-ref="${esc(b.id)}">${esc(b.name||b.id)}</span>`).join(" "));
  return h;}
function renderTable(d){const tname=d.id;
  let h=card("数据库表",`<div class="kv">${kvd("表名",`<span class="mono">${esc(tname)}</span>`)}</div>`);
  const mp=(MM.mappings||[]).find(m=>(m.tableMappings||[]).some(t=>t.tableName===tname));
  const tb=mp&&(mp.tableMappings||[]).find(t=>t.tableName===tname);
  if(mp)h+=card("所属对象",`<div class="kv">${kvd("映射对象",ref(mp.objectRef))}${kvd("映射ID",ref(mp.id))}${kvd("表角色",esc(tb?.tableRole||"—"))}${kvd("主键",esc(tb?.primaryKey||"—"))}</div>`);
  h+=card("列映射",`<table class="tbl"><tr><th>属性路径</th><th>列</th><th>类型</th><th>主键</th><th>外键</th><th>目标表</th><th>说明</th></tr>`+
    (tb?.columnMappings||[]).map(c=>`<tr><td class="mono">${esc(c.attributeRef||"—")}</td><td class="mono">${esc(c.column||"—")}</td><td>${esc(c.columnType||"—")}</td><td>${c.isPrimaryKey?"✓":""}</td><td>${c.isForeignKey?"✓":""}</td><td>${c.fkTargetTable?ref(c.fkTargetTable):"—"}</td><td>${esc(c.mappingNote||"—")}</td></tr>`).join("")+"</table>");
  return h;}
function renderRule(d){const r=findRule(d.id);if(!r)return"";
  let h=card("规则",`<div class="kv">${kvd("ID",`<span class="mono">${esc(r.id)}</span>`)}${kvd("名称",esc(r.name||"—"))}${kvd("类型",esc(r.ruleType||"—"))}
    ${kvd("描述",esc(r.description||"—"))}${kvd("触发类型",esc(r.triggerType||"—"))}${kvd("订阅事件",splitIds(r.subscribedEvents).map(e=>ref(e)).join("")||"—")}
    ${kvd("触发行为",splitIds(r.triggeredBehaviors).map(b=>ref(b)).join("")||"—")}${kvd("被调用",splitIds(r.reusedBy).map(b=>ref(b)).join("")||"—")}
    ${kvd("执行模式",esc(r.executionMode||"—"))}${kvd("版本",esc(r.version||"—"))}</div>`);
  h+=card("表达式",`<pre class="code">${esc(r.expression||"—")}</pre>`);
  if(r.inputParams&&r.inputParams.length)h+=card("输入参数",`<table class="tbl"><tr><th>参数</th><th>类型</th><th>来源字段</th><th>必填</th></tr>`+r.inputParams.map(p=>`<tr><td class="mono">${esc(p.name)}</td><td>${esc(p.type||"—")}</td><td class="mono">${esc(p.sourceField||"—")}</td><td>${p.required?"是":"—"}</td></tr>`).join("")+"</table>");
  return h;}
function renderEventNode(d){const e=findEvent(d.id);if(!e)return"";
  let h=card("事件",`<div class="kv">${kvd("事件ID",`<span class="mono">${esc(e.eventId)}</span>`)}${kvd("事实名称",esc(e.eventName||"—"))}${kvd("说明",esc(e.description||"—"))}
    ${kvd("触发条件",esc(e.triggerCondition||"—"))}${kvd("生产者行为",splitIds(e.producerBehaviorRef).map(b=>ref(b)).join("")||"—")}${kvd("产生对象",ref(e.producerEntityRef))}${kvd("顺序语义",esc(e.ordering||"—"))}</div>`);
  h+=card("载荷",`<table class="tbl"><tr><th>字段</th><th>类型</th><th>必填</th><th>来源</th></tr>`+(e.payload||[]).map(p=>`<tr><td class="mono">${esc(p.name)}</td><td>${esc(p.type||"—")}</td><td>${p.required?"是":"—"}</td><td class="mono">${esc(p.sourceField||"—")}</td></tr>`).join("")+"</table>");
  h+=card("订阅者",(e.subscribers||[]).map(s=>`<div style="margin:3px 0">${esc(s.subscriberType||"—")} → ${splitIds(s.subscriberBehaviorRef).map(b=>ref(b)).join("")}</div>`).join("")||"—");
  return h;}
function renderScenario(d){const s=findScenario(d.id);if(!s)return"";
  let h=card("场景",`<div class="kv">${kvd("ID",`<span class="mono">${esc(s.id)}</span>`)}${kvd("名称",esc(s.name||"—"))}${kvd("说明",esc(s.description||"—"))}
    ${kvd("源对象",ref(s.sourceObjectRef))}${kvd("目标对象",splitIds(s.targetObjectRefs).map(t=>ref(t)).join("")||"—")}${kvd("触发事件",splitIds(s.triggerEventRef).map(t=>ref(t)).join("")||"—")}${kvd("终止条件",esc(s.terminationCondition||"—"))}</div>`);
  h+=card("前置条件",(s.preconditions||[]).map(p=>`<li>${esc(p)}</li>`).join("")||"—");
  h+=card("后置条件",(s.postconditions||[]).map(p=>`<li>${esc(p)}</li>`).join("")||"—");
  h+=card("步骤链",`<div class="chain">${(s.steps||[]).map((st,i)=>`<span class="chstep"><span class="stepno">${esc(st.stepId||i+1)}</span>${esc(st.stepType)}<span class="arrow">${chainStepBody(st)}</span></span>`+(i<(s.steps||[]).length-1?`<span class="charrow">→</span>`:"")).join("")}</div>`);
  return h;}
function renderReport(d){const r=findReport(d.id);if(!r)return"";
  let h=card("查询报表",`<div class="kv">${kvd("ID",`<span class="mono">${esc(r.id)}</span>`)}${kvd("名称",esc(r.name||"—"))}${kvd("类型",esc(r.objectType||"—"))}${kvd("描述",esc(r.description||"—"))}${kvd("绑定行为",ref(r.behaviorRef))}${kvd("版本",esc(r.version||"—"))}</div>`);
  h+=card("来源对象",(r.sourceObjects||[]).map(so=>`<div style="margin:3px 0">${so.primary?"◆ ":""}${ref(so.objectRef)} <span class="mono" style="color:var(--dim)">alias=${esc(so.alias||"—")}</span>${so.preAggregation?" ·预聚合":""}</div>`).join("")||"—");
  h+=card("结果列",`<table class="tbl"><tr><th>列</th><th>类型</th><th>来源表达式</th><th>聚合</th></tr>`+(r.resultColumns||[]).map(c=>`<tr><td>${esc(c.label||c.name)}</td><td>${esc(c.dataType||"—")}</td><td class="mono">${esc(c.sourceExpression||"—")}</td><td>${esc(c.aggregateFunction||"—")}</td></tr>`).join("")+"</table>");
  if(r.parameters&&r.parameters.length)h+=card("参数",`<table class="tbl"><tr><th>参数</th><th>类型</th><th>必填</th><th>操作符</th></tr>`+r.parameters.map(p=>`<tr><td>${esc(p.label||p.name)}</td><td>${esc(p.dataType||"—")}</td><td>${p.required?"是":"—"}</td><td>${esc((p.allowedOperators||[]).join(","))}</td></tr>`).join("")+"</table>");
  h+=card("参考 SQL",`<details><summary>查看/复制 SQL</summary><pre class="code">${esc(r.referenceSql?.sql||"—")}</pre></details>`);
  return h;}
function renderPermission(d){const p=(M5.permissions||[]).find(x=>x.permissionId===d.id);if(!p)return"";
  return card("权限",`<div class="kv">${kvd("ID",`<span class="mono">${esc(p.permissionId)}</span>`)}${kvd("授权目标",splitIds(p.targetRef).map(t=>ref(t)).join("")||"—")}${kvd("数据范围",esc(p.dataScope||"—"))}${kvd("ABAC",esc(p.abacCondition||"—"))}${kvd("控制元素",splitIds(p.uiControlledElements).map(e=>ref(e)).join("")||"—")}</div>`);}
function renderRole(d){const r=(M5.roles||[]).find(x=>x.roleId===d.id);if(!r)return"";
  return card("角色",`<div class="kv">${kvd("ID",`<span class="mono">${esc(r.roleId)}</span>`)}${kvd("名称",esc(r.name||"—"))}${kvd("说明",esc(r.description||"—"))}${kvd("继承",esc((r.inheritsFrom||[]).join(",")))}${kvd("权限",splitIds(r.permissions).map(p=>ref(p)).join("")||"—")}</div>`);}
function renderActor(d){const a=(M5.actors||[]).find(x=>x.actorId===d.id);if(!a)return"";const ec=a.externalContract||{};
  return card("外部实体",`<div class="kv">${kvd("ID",`<span class="mono">${esc(a.actorId)}</span>`)}${kvd("名称",esc(a.name||"—"))}${kvd("说明",esc(a.description||"—"))}${kvd("协议",esc(ec.protocol||"—"))}${kvd("数据格式",esc(ec.dataFormat||"—"))}${kvd("认证",esc(ec.authMethod||"—"))}</div>`);}
function renderFlow(d){const f=(M6.flows||[]).find(x=>x.id===d.id);if(!f)return"";
  let h=card("流程",`<div class="kv">${kvd("ID",`<span class="mono">${esc(f.id)}</span>`)}${kvd("名称",esc(f.name||"—"))}${kvd("类型",esc(f.flowType||"—"))}${kvd("描述",esc(f.description||"—"))}${kvd("业务对象",splitIds(f.businessObjectRefs).map(b=>ref(b)).join("")||"—")}${kvd("角色",splitIds(f.roleRefs).map(r=>ref(r)).join("")||"—")}${kvd("触发",esc(f.trigger?.triggerType||"—")+(f.trigger?.behaviorRef?" "+ref(f.trigger.behaviorRef):""))}</div>`);
  h+=card("活动",`<table class="tbl"><tr><th>活动</th><th>类型</th><th>角色/行为/引用</th><th>后继</th></tr>`+(f.activities||[]).map(a=>`<tr><td class="mono">${esc(a.activityId)} ${esc(a.name||"")}</td><td>${esc(a.activityType||"—")}</td><td>${splitIds(a.roleRef).map(r=>ref(r)).join(" ")}${a.behaviorRef?" "+ref(a.behaviorRef):""}${a.scenarioRef?" "+ref(a.scenarioRef):""}${a.subFlowRef?" "+ref(a.subFlowRef):""}${a.ruleRef?" "+ref(a.ruleRef):""}</td><td class="mono">${esc((a.nextActivities||[]).join(","))}${(a.branches||[]).map(b=>`<br>${esc(b.branchName)}→${esc(b.targetActivity)}`).join("")}</td></tr>`).join("")+"</table>");
  return h;}
function renderMapping(d){const mp=(MM.mappings||[]).find(x=>x.id===d.id);if(!mp)return"";
  let h=card("映射",`<div class="kv">${kvd("ID",`<span class="mono">${esc(mp.id)}</span>`)}${kvd("对象",ref(mp.objectRef))}${kvd("对象角色",esc(mp.objectRole||"—"))}${kvd("对象名",esc(mp.objectName||"—"))}</div>`);
  (mp.tableMappings||[]).forEach(tb=>{h+=card("表 "+tb.tableName,`<div class="kv">${kvd("表角色",esc(tb.tableRole||"—"))}${kvd("主键",esc(tb.primaryKey||"—"))}</div><table class="tbl"><tr><th>属性</th><th>列</th><th>类型</th><th>主键</th><th>外键</th><th>目标表</th></tr>`+(tb.columnMappings||[]).map(c=>`<tr><td class="mono">${esc(c.attributeRef||"—")}</td><td class="mono">${esc(c.column||"—")}</td><td>${esc(c.columnType||"—")}</td><td>${c.isPrimaryKey?"✓":""}</td><td>${c.isForeignKey?"✓":""}</td><td>${c.fkTargetTable?ref(c.fkTargetTable):"—"}</td></tr>`).join("")+"</table>");});
  return h;}
function renderInterface(d){const it=(MI.interfaces||[]).find(x=>x.interfaceId===d.id);if(!it)return"";
  let h=card("接口",`<div class="kv">${kvd("ID",`<span class="mono">${esc(it.interfaceId)}</span>`)}${kvd("名称",esc(it.name||"—"))}${kvd("方向",esc(it.interfaceType||"—"))}${kvd("服务提供方",esc(it.providerSystem||"—"))}${kvd("调用方",esc(it.consumerSystem||"—"))}${kvd("类别",esc(it.interfaceCategory||"—"))}${kvd("业务目的",esc(it.businessPurpose||"—"))}${kvd("协议",esc(it.protocol||"—"))}${kvd("鉴权",esc(it.authMethod||"—"))}${kvd("关联行为",splitIds(it.relatedBehaviorRef).map(b=>ref(b)).join("")||"—")}${kvd("关联对象",splitIds(it.relatedEntityRef).map(b=>ref(b)).join("")||"—")}${kvd("关联报表",splitIds(it.relatedReportRef).map(b=>ref(b)).join("")||"—")}${kvd("关联外部实体",splitIds(it.relatedExternalEntityRef).map(b=>ref(b)).join("")||"—")}</div>`);
  h+=card("输入参数",`<table class="tbl"><tr><th>字段</th><th>标签</th><th>类型</th><th>必填</th><th>说明</th></tr>`+(it.inputParameters||[]).map(p=>`<tr><td class="mono">${esc(p.name)}</td><td>${esc(p.label||"—")}</td><td>${esc(p.dataType||"—")}</td><td>${p.required?"是":"—"}</td><td>${esc(p.description||"—")}</td></tr>`).join("")+"</table>");
  h+=card("输出结果",`<table class="tbl"><tr><th>字段</th><th>标签</th><th>类型</th><th>说明</th></tr>`+(it.outputResult||[]).map(p=>`<tr><td class="mono">${esc(p.name)}</td><td>${esc(p.label||"—")}</td><td>${esc(p.dataType||"—")}</td><td>${esc(p.description||"—")}</td></tr>`).join("")+"</table>");
  h+=card("返回规则",(it.returnRule||[]).map(x=>`<li>${esc(x)}</li>`).join("")||"—");
  return h;}
function renderDictionary(d){const dd=(M1.data_dictionaries||[]).find(x=>x.id===d.id);if(!dd)return"";
  let h=card("数据字典",`<div class="kv">${kvd("ID",`<span class="mono">${esc(dd.id)}</span>`)}${kvd("名称",esc(dd.name||"—"))}</div>`);
  (dd.types||[]).forEach(t=>{h+=card(t.typeCode,`<table class="tbl"><tr><th>编码</th><th>标签</th><th>排序</th></tr>`+(t.items||[]).map(it=>`<tr><td class="mono">${esc(it.code)}</td><td>${esc(it.label||"—")}</td><td>${esc(it.sortOrder!=null?it.sortOrder:"—")}</td></tr>`).join("")+"</table>");});
  return h;}
function renderCross(d){const c=(MU.cross_cutting||[]).find(x=>x.id===d.id);if(!c)return"";
  return card("横切行为",`<div class="kv">${kvd("ID",`<span class="mono">${esc(c.id)}</span>`)}${kvd("名称",esc(c.name||"—"))}${kvd("说明",esc(c.description||"—"))}${kvd("生效屏幕",splitIds(c.appliesTo).map(s=>ref(s)).join("")||"—")}${kvd("规则",splitIds(c.rules).map(r=>ref(r)).join("")||"—")}${kvd("目标",esc(c.target||"—"))}</div>`);}

/* ═════════════ 搜索 ═════════════ */
let searchIdx=[];
function buildSearchIndex(){searchIdx=[];rootItems().forEach(r=>r.items.forEach(d=>searchIdx.push(d)));
  Object.keys(treeState).forEach(()=>{});}
function openSearch(){document.getElementById("modal").style.display="block";document.getElementById("mask").style.display="block";
  document.getElementById("q").value="";doSearch("");document.getElementById("q").focus();}
function closeSearch(){document.getElementById("modal").style.display="none";document.getElementById("mask").style.display="none";}
function doSearch(q){const res=document.getElementById("qres");q=q.trim().toLowerCase();
  if(!q){res.innerHTML='<div style="color:var(--dim);padding:10px">输入关键字搜索名称 / ID / 类型</div>';return;}
  const hits=searchIdx.filter(n=>(n.label||"").toLowerCase().includes(q)||(n.id||"").toLowerCase().includes(q)||(n.type||"").toLowerCase().includes(q)).slice(0,80);
  res.innerHTML=hits.map((x,i)=>`<div class="sres ${i===0?"sel":""}" onclick="pickSearch('${esc(x.key)}')"><span class="rt">${tag(x.type)}</span><span class="nm">${hl(x.label,q)}</span><span class="id">${esc(x.id)}</span></div>`).join("")||'<div style="color:var(--dim);padding:10px">无结果</div>';}
function hl(t,q){const i=String(t).toLowerCase().indexOf(q);if(i<0)return esc(t);return esc(t.slice(0,i))+'<span class="hl">'+esc(t.slice(i,i+q.length))+'</span>'+esc(t.slice(i+q.length));}
function pickSearch(k){closeSearch();pushCrumb(k);selectNode(k);}

/* ═════════════ 初始化 ═════════════ */
function initSplitter(){
  const sp=document.getElementById("splitter");
  const left=document.querySelector(".left");
  const KEY="wb.leftW";
  try{const w=localStorage.getItem(KEY);if(w&&parseInt(w)>100)left.style.width=w+"px";}catch(e){}
  let drag=false;
  sp.addEventListener("mousedown",e=>{drag=true;sp.classList.add("active");document.body.style.cursor="col-resize";e.preventDefault();});
  document.addEventListener("mousemove",e=>{if(!drag)return;
    const w=Math.min(Math.max(e.clientX-16,240),window.innerWidth*0.72);
    left.style.width=w+"px";});
  document.addEventListener("mouseup",()=>{if(drag){drag=false;sp.classList.remove("active");document.body.style.cursor="";
    try{localStorage.setItem(KEY,Math.round(left.getBoundingClientRect().width));}catch(e){}}});
}
function init(){
  initSplitter();
  buildTree();buildSearchIndex();
  const labels=[["屏",STATS.screen],["行为",STATS.behavior],["规则",STATS.rule],["事件",STATS.event],["场景",STATS.scenario],["对象",STATS.aggregate],["权限",STATS.permission],["报表",STATS.report],["流程",STATS.flow],["表",STATS.table],["接口",STATS.interface],["字典",STATS.dictionary]];
  document.getElementById("badges").innerHTML=labels.filter(x=>x[1]).map(x=>`<span class="badge">${x[0]}<b>${x[1]}</b></span>`).join("");
  document.getElementById("btnExpandAll").onclick=expandAll;
  document.getElementById("btnCollapseAll").onclick=collapseAll;
  document.getElementById("searchInput").addEventListener("input",e=>{openSearch();document.getElementById("q").value=e.target.value;doSearch(e.target.value);});
  document.getElementById("q").addEventListener("input",e=>doSearch(e.target.value));
  document.addEventListener("keydown",e=>{if((e.ctrlKey||e.metaKey)&&e.key.toLowerCase()==="k"){e.preventDefault();openSearch();}if(e.key==="Escape")closeSearch();});
  const first=(MU.screens||[]).length?"scr:"+(MU.screens[0].screenId):null;
  if(first)selectNode(first);
}
init();
</script>
</body>
</html>
"""


def main():
    args = parse_args(sys.argv[1:])
    models = load_models(args["dir"])
    payload = build_payload(models, args["pretty"])
    html = TEMPLATE.replace("__MODEL_JSON__", payload)
    out = args["out"]
    with open(out, "w", encoding="utf-8") as f:
        f.write(html)
    st = json.loads(payload).get("stats", {})
    print("已生成: %s" % out)
    print("读取模型文件: %d" % len(models))
    print("统计: " + ", ".join("%s=%s" % (k, v) for k, v in st.items() if v))


if __name__ == "__main__":
    main()
