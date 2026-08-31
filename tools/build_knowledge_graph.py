# -*- coding: utf-8 -*-
"""
本体知识图谱生成脚本（通用版）：
解析 ont_yaml/ 下的 M1~M7+ME 八模型 YAML，生成 ECharts 力导向图数据 JSON。
用法：
  python build_knowledge_graph.py <ont_yaml_dir> [output_json]
  python build_knowledge_graph.py E:/some-project/ont_yaml E:/some-project/knowledge-graph-data.json
"""
import yaml, os, json, sys, re
from collections import Counter

def load_yaml(path):
    with open(path, encoding='utf-8') as f:
        return yaml.safe_load(f) or {}

def load_all_models(yaml_dir):
    """加载所有模型 YAML，返回 {model_id: data}"""
    files = {
        'm1': 'm1-object-model.yaml',
        'm2': 'm2-behavior-model.yaml',
        'm3': 'm3-rule-model.yaml',
        'me': 'me-event-model.yaml',
        'm4': 'm4-scenario-model.yaml',
        'm5': 'm5-actor-model.yaml',
        'm6': 'm6-flow-model.yaml',
        'm7': 'm7-report-model.yaml',
    }
    models = {}
    for key, fname in files.items():
        path = os.path.join(yaml_dir, fname)
        if os.path.exists(path):
            models[key] = load_yaml(path)
        else:
            models[key] = {}
    return models

# ═══════════════════════════════════════════════════════
# 节点/边收集
# ═══════════════════════════════════════════════════════
nodes = {}   # id -> node dict
edges = []   # [{source, target, type, label, model}]

def add_node(nid, name, ntype, model, desc=''):
    if not nid: return
    if nid not in nodes:
        nodes[nid] = {'id': nid, 'name': name, 'type': ntype, 'model': model, 'desc': desc}

def add_edge(s, t, etype, label, model):
    if not s or not t or s == t: return
    edges.append({'source': s, 'target': t, 'type': etype, 'label': label, 'model': model})

def strip_id_prefix(agg):
    """从 aggregate 中提取短 ID（alias 或 name）用于节点 ID"""
    return agg.get('alias') or agg.get('name', '')

# ═══════════════════════════════════════════════════════
# M1 对象模型
# ═══════════════════════════════════════════════════════
def process_m1(m1):
    # 聚合根
    for agg in m1.get('aggregates', []):
        aid = agg.get('id') or agg.get('alias')
        add_node(aid, agg.get('name', aid), 'aggregate', 'M1', agg.get('description', ''))
        # 子实体
        for ent in agg.get('entities', []):
            eid = aid + '.' + (ent.get('alias') or ent.get('name', ''))
            add_node(eid, ent.get('name', eid), 'entity', 'M1', ent.get('description', ''))
            add_edge(aid, eid, 'contains', '包含子实体', 'M1')
            for a in ent.get('attributes', []):
                if a.get('type') == 'AggregateRootRef' and a.get('targetAggregate'):
                    add_edge(eid, a['targetAggregate'], 'refers', '引用', 'M1')
        # 值对象
        for vo in agg.get('valueObjects', []):
            vid = aid + '.VO.' + (vo.get('alias') or vo.get('name', ''))
            add_node(vid, vo.get('name', vid), 'value_object', 'M1', vo.get('description', ''))
            add_edge(aid, vid, 'contains', '包含值对象', 'M1')
        # 聚合根属性引用
        for a in agg.get('attributes', []):
            if a.get('type') == 'AggregateRootRef' and a.get('targetAggregate'):
                add_edge(aid, a['targetAggregate'], 'refers', '引用', 'M1')
        # 不变量规则
        for inv in agg.get('invariants', []):
            rid = 'INV-' + (inv.get('name') or aid)
            add_node(rid, inv.get('name', rid), 'rule', 'M1',
                     '对象级不变量: ' + inv.get('expression', ''))
            add_edge(aid, rid, 'owned', '约束', 'M1')
        # refRules（引用规则也作为规则节点）
        for a in agg.get('attributes', []):
            for rr in a.get('refRules', []):
                rid = 'REFRULE-' + (rr.get('name') or a.get('name', ''))
                add_node(rid, rr.get('name', rid), 'rule', 'M1',
                         rr.get('description', '') or rr.get('expression', ''))
                add_edge(aid, rid, 'owned', '约束', 'M1')

    # 数据字典
    for dd in m1.get('data_dictionaries', []):
        did = dd.get('id') or dd.get('name', 'DICT')
        add_node(did, dd.get('name', did), 'dictionary', 'M1', dd.get('description', ''))
        for t in dd.get('types', []):
            tname = t.get('typeCode', '')
            add_node(did + '.' + tname, t.get('typeName', tname), 'dictionary', 'M1', '字典类型')

    # 聚合间关联
    for assoc in m1.get('aggregate_associations', []):
        s = assoc.get('sourceAggregate'); t = assoc.get('targetAggregate')
        if s and t:
            label = assoc.get('sourceRole') or (assoc.get('cardinality') or '关联')
            add_edge(s, t, 'assoc', label, 'M1')

# ═══════════════════════════════════════════════════════
# M2 行为模型
# ═══════════════════════════════════════════════════════
def process_m2(m2):
    for b in m2.get('behaviors', []):
        bid = b.get('id') or b.get('alias')
        if not bid: continue
        btype = b.get('behaviorType', '')
        add_node(bid, b.get('name', bid), 'behavior', 'M2',
                 '触发:' + b.get('triggerType', '') + ';类型:' + btype)
        owner = b.get('ownerEntity')
        if owner: add_edge(bid, owner, 'operates', '操作对象', 'M2')
        for r in b.get('appliedRules', []):
            add_edge(bid, r, 'applies', '引用规则', 'M2')
        for ev in b.get('producedEvents', []):
            add_edge(bid, ev, 'produces', '产生事件', 'M2')
        qr = b.get('queryReportRef')
        if qr: add_edge(bid, qr, 'binds', '查询绑定', 'M2')
        for p in b.get('requiredPermissions', []):
            add_edge(bid, p, 'requires', '需要权限', 'M2')

# ═══════════════════════════════════════════════════════
# M3 规则模型
# ═══════════════════════════════════════════════════════
def process_m3(m3):
    for r in m3.get('rules', []):
        rid = r.get('id') or r.get('alias')
        if not rid: continue
        add_node(rid, r.get('name', rid), 'rule', 'M3',
                 '类型:' + r.get('ruleType', '') + ';' + r.get('description', ''))
        for sub in r.get('subscribedEvents', []):
            add_edge(sub, rid, 'consumed_by', '规则订阅', 'M3')
        for tb in r.get('triggeredBehaviors', []):
            add_edge(rid, tb, 'triggers', '触发行为', 'M3')

# ═══════════════════════════════════════════════════════
# ME 事件模型
# ═══════════════════════════════════════════════════════
def process_me(me):
    for ev in me.get('events', []):
        eid = ev.get('eventId') or ev.get('id')
        if not eid: continue
        add_node(eid, ev.get('eventName', eid), 'event', 'ME', ev.get('description', ''))
        p = ev.get('producerBehaviorRef')
        if p: add_edge(p, eid, 'produces', '产生事件', 'ME')
        pe = ev.get('producerEntityRef')
        if pe: add_edge(pe, eid, 'event_entity', '事件所属', 'ME')
        for sub in ev.get('subscribers', []):
            st = sub.get('subscriberType')
            ref = sub.get('subscriberBehaviorRef') or sub.get('subscriberRuleRef')
            if ref:
                add_edge(eid, ref, 'consumed_by', '事件消费', 'ME')

# ═══════════════════════════════════════════════════════
# M4 场景模型
# ═══════════════════════════════════════════════════════
def process_m4(m4):
    for sc in m4.get('event_scenarios', []) or m4.get('scenarios', []):
        sid = sc.get('id') or sc.get('alias')
        if not sid: continue
        add_node(sid, sc.get('name', sid), 'scenario', 'M4', sc.get('description', ''))
        src = sc.get('sourceObjectRef')
        if src: add_edge(sid, src, 'source', '源对象', 'M4')
        for t in sc.get('targetObjectRefs', []):
            add_edge(sid, t, 'target', '目标对象', 'M4')
        tr = sc.get('triggerEventRef')
        if tr: add_edge(sid, tr, 'trigger', '触发事件', 'M4')
        for step in sc.get('steps', []):
            br = step.get('behaviorRef'); er = step.get('eventRef'); rr = step.get('ruleRef')
            if br: add_edge(sid, br, 'calls', '调用行为', 'M4')
            if er: add_edge(sid, er, 'calls', '发布事件', 'M4')
            if rr: add_edge(sid, rr, 'calls', '评估规则', 'M4')

# ═══════════════════════════════════════════════════════
# M5 主体模型
# ═══════════════════════════════════════════════════════
def process_m5(m5):
    for actor in m5.get('actors', []):
        aid = actor.get('actorId') or actor.get('id')
        if not aid: continue
        add_node(aid, actor.get('name', aid), 'external', 'M5',
                 actor.get('description', '') + ';类型:' + actor.get('actorType', ''))
        for r in actor.get('roles', []):
            add_edge(aid, r, 'role_of', '拥有角色', 'M5')
    for role in m5.get('roles', []):
        rid = role.get('roleId') or role.get('id')
        if not rid: continue
        add_node(rid, role.get('name', rid), 'role', 'M5', role.get('description', ''))
        for p in role.get('permissions', []):
            add_edge(rid, p, 'role_perm', '拥有权限', 'M5')
    for perm in m5.get('permissions', []):
        pid = perm.get('permissionId') or perm.get('id')
        if not pid: continue
        add_node(pid, pid, 'permission', 'M5', '授权目标:' + str(perm.get('targetRef', '')))
        tr = perm.get('targetRef')
        if tr: add_edge(pid, tr, 'perm_behavior', '授权行为', 'M5')

# ═══════════════════════════════════════════════════════
# M6 流程模型
# ═══════════════════════════════════════════════════════
def process_m6(m6):
    for flow in m6.get('flows', []):
        fid = flow.get('id') or flow.get('alias')
        if not fid: continue
        add_node(fid, flow.get('name', fid), 'flow', 'M6', '类型:' + flow.get('flowType', ''))
        for obj in flow.get('businessObjectRefs', []):
            add_edge(fid, obj, 'flow_object', '业务对象', 'M6')
        for r in flow.get('roleRefs', []):
            add_edge(fid, r, 'flow_role', '执行角色', 'M6')
        trig = flow.get('trigger', {})
        if trig.get('behaviorRef'): add_edge(fid, trig['behaviorRef'], 'calls', '启动行为', 'M6')
        if trig.get('eventRef'): add_edge(fid, trig['eventRef'], 'calls', '启动事件', 'M6')
        for act in flow.get('activities', []):
            if act.get('behaviorRef'): add_edge(fid, act['behaviorRef'], 'calls', '调用行为', 'M6')
            if act.get('scenarioRef'): add_edge(fid, act['scenarioRef'], 'calls', '调用场景', 'M6')

# ═══════════════════════════════════════════════════════
# M7 查询报表模型
# ═══════════════════════════════════════════════════════
def process_m7(m7):
    for qr in m7.get('query_reports', []):
        qid = qr.get('id') or qr.get('alias')
        if not qid: continue
        add_node(qid, qr.get('name', qid), 'report', 'M7',
                 '类型:' + qr.get('objectType', '') + ';' + qr.get('description', ''))
        br = qr.get('behaviorRef')
        if br: add_edge(qid, br, 'binds', '查询行为', 'M7')
        for src in qr.get('sourceObjects', []):
            obj = src.get('objectRef')
            if obj: add_edge(qid, obj, 'sources', '数据来源', 'M7')

# ═══════════════════════════════════════════════════════
# 分类 / 边颜色 / 边标签 元信息
# ═══════════════════════════════════════════════════════
CATEGORIES = [
    {'type': 'aggregate',   'name': '聚合根',   'color': '#5470c6'},
    {'type': 'entity',      'name': '子实体',   'color': '#91cc75'},
    {'type': 'value_object','name': '值对象',   'color': '#fac858'},
    {'type': 'dictionary',  'name': '数据字典', 'color': '#a0a0a0'},
    {'type': 'behavior',    'name': '行为',     'color': '#ee6666'},
    {'type': 'rule',        'name': '规则',     'color': '#ff8c00'},
    {'type': 'event',       'name': '事件',     'color': '#9a60b4'},
    {'type': 'scenario',    'name': '场景',     'color': '#3ba272'},
    {'type': 'flow',        'name': '流程',     'color': '#fc8452'},
    {'type': 'role',        'name': '角色',     'color': '#36a3f7'},
    {'type': 'permission',  'name': '权限',     'color': '#e06343'},
    {'type': 'external',    'name': '外部参与方','color': '#b8b8d8'},
    {'type': 'report',      'name': '查询报表', 'color': '#2f9688'},
]

EDGE_COLORS = {
    'contains': '#ccc', 'operates': '#ee6666', 'applies': '#ff8c00',
    'produces': '#9a60b4', 'consumed_by': '#9a60b4', 'triggers': '#ff8c00',
    'calls': '#3ba272', 'emits': '#9a60b4', 'source': '#91cc75', 'target': '#fc8452',
    'trigger': '#9a60b4', 'flow_role': '#36a3f7', 'role_perm': '#36a3f7',
    'perm_behavior': '#e06343', 'perm_ui': '#e06343', 'binds': '#2f9688',
    'sources': '#2f9688', 'assoc': '#5470c6', 'navigates': '#5d6b7a',
    'owned': '#ff8c00', 'refers': '#5470c6', 'requires': '#e06343',
    'role_of': '#36a3f7', 'event_entity': '#9a60b4', 'flow_object': '#5470c6',
}
EDGE_LABELS = {
    'contains': '包含', 'operates': '操作对象', 'applies': '引用规则', 'produces': '产生事件',
    'consumed_by': '消费', 'triggers': '触发行为', 'calls': '调用', 'emits': '发布事件',
    'source': '源对象', 'target': '目标对象', 'trigger': '触发事件', 'flow_role': '执行角色',
    'role_perm': '拥有权限', 'perm_behavior': '授权行为', 'perm_ui': '控制界面', 'binds': '查询绑定',
    'sources': '数据来源', 'assoc': '关联', 'navigates': '跳转', 'owned': '约束',
    'refers': '引用', 'requires': '需要权限', 'role_of': '拥有角色', 'event_entity': '事件所属',
    'flow_object': '业务对象',
}

# ═══════════════════════════════════════════════════════
# 主流程
# ═══════════════════════════════════════════════════════
def main():
    if len(sys.argv) < 2:
        print("用法: python build_knowledge_graph.py <ont_yaml_dir> [output_json]")
        sys.exit(1)

    yaml_dir = sys.argv[1]
    out_json = sys.argv[2] if len(sys.argv) > 2 else os.path.join(yaml_dir, '..', 'knowledge-graph-data.json')

    if not os.path.isdir(yaml_dir):
        print(f"错误: 目录不存在 {yaml_dir}")
        sys.exit(1)

    models = load_all_models(yaml_dir)

    # 逐模型解析
    if models.get('m1'): process_m1(models['m1'])
    if models.get('m2'): process_m2(models['m2'])
    if models.get('m3'): process_m3(models['m3'])
    if models.get('me'): process_me(models['me'])
    if models.get('m4'): process_m4(models['m4'])
    if models.get('m5'): process_m5(models['m5'])
    if models.get('m6'): process_m6(models['m6'])
    if models.get('m7'): process_m7(models['m7'])

    # 去重边
    seen = set()
    dedup_edges = []
    for e in edges:
        key = (e['source'], e['target'], e['type'])
        if key in seen: continue
        seen.add(key)
        dedup_edges.append(e)

    data = {
        'nodes': list(nodes.values()),
        'edges': dedup_edges,
        'categories': CATEGORIES,
        'edgeColors': EDGE_COLORS,
        'edgeLabels': EDGE_LABELS,
    }

    os.makedirs(os.path.dirname(os.path.abspath(out_json)), exist_ok=True)
    with open(out_json, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=1)

    print(f"✅ 知识图谱数据已生成: {out_json}")
    print(f"   节点数: {len(nodes)}")
    print(f"   边数:   {len(dedup_edges)}")
    print(f"   节点分类: {dict(Counter(n['type'] for n in nodes.values()))}")

if __name__ == '__main__':
    main()
