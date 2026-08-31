# -*- coding: utf-8 -*-
"""
CRUD + validation layer driven by the ontology M1 model.

Supports (v1 scope):
  - create / update(by id) / delete (physical with FK protection OR logical void)
  - refRules (single-attribute) validation
  - invariants (aggregate-level) validation for common patterns
  - status lifecycle membership check
  - one level of master-detail (collection sub-entities)
"""
import json
import re
import sqlite3
import uuid
from datetime import datetime

from loader import SQL_TYPE_MAP  # noqa


# ---------------------------------------------------------------- validation
def _norm_value(col, val):
    """Normalize a Python value for storage according to column sql_type."""
    if val is None:
        return None
    if col["sql_type"] == "INTEGER" and col.get("enum") is None and col["name"] not in ():
        if isinstance(val, bool):
            return 1 if val else 0
        if col.get("vo") or col.get("dict_ref") or col.get("ref"):
            return str(val)
        try:
            return int(val)
        except (TypeError, ValueError):
            return val
    if col["sql_type"] == "REAL":
        try:
            return float(val)
        except (TypeError, ValueError):
            return val
    if col.get("vo"):
        return json.dumps(val, ensure_ascii=False) if not isinstance(val, str) else val
    return val


def _eval_refrule(expr, value):
    if value is None:
        return True
    env = {"value": value, "LENGTH": len, "LEN": len, "ABS": abs, "NOW": ""}
    expr = expr.replace(" AND ", " and ").replace(" OR ", " or ")
    try:
        return bool(eval(expr, {"__builtins__": {}}, env))
    except Exception:
        return True  # cannot evaluate -> do not block


def _sum(lst, attr):
    return sum((d.get(attr) or 0) for d in lst)


def _eval_invariant(expr, children_map):
    env = {"_sum": _sum, "len": len, "LENGTH": len, "ABS": abs,
           "SUM": lambda *a, **k: 0}
    env.update(children_map)
    e = expr
    e = re.sub(r"(\w+)\.size\(\)", r"len(\1)", e)
    e = re.sub(r"SUM\(\s*([\w]+)\.([\w]+)\s*\)", r'_sum(\1,"\2")', e)
    e = e.replace(" AND ", " and ").replace(" OR ", " or ")
    try:
        return bool(eval(e, {"__builtins__": {}}, env))
    except Exception:
        # unsupported expression pattern -> record but do not block v1 flow
        return "SKIP"


def validate_refrules(agg, data):
    errors = []
    for a in agg.get("attributes", []):
        for r in a.get("refRules", []) or []:
            val = data.get(a["name"])
            if val is None:
                continue
            if not _eval_refrule(r.get("expression", "True"), val):
                errors.append(r.get("violationMessage") or f"规则不满足: {r.get('name')}")
    # sub-entity attribute refRules
    for e in agg.get("entities", []):
        rows = data.get(e.get("alias")) or data.get(e.get("name")) or []
        for row in (rows if isinstance(rows, list) else []):
            for a in e.get("attributes", []):
                for r in a.get("refRules", []) or []:
                    val = row.get(a["name"]) if isinstance(row, dict) else None
                    if val is None:
                        continue
                    if not _eval_refrule(r.get("expression", "True"), val):
                        errors.append(f"[{e.get('name')}] {r.get('violationMessage') or r.get('name')}")
    return errors


def validate_invariants(agg, data, children_map):
    warnings = []
    errors = []
    for inv in agg.get("invariants", []) or []:
        res = _eval_invariant(inv.get("expression", "True"), children_map)
        if res is False:
            errors.append(inv.get("violationMessage") or inv.get("name"))
        elif res == "SKIP":
            warnings.append(f"不变量未自动校验(表达式暂不支持): {inv.get('name')}")
    return errors, warnings


# ---------------------------------------------------------------- helpers
def _child_payloads(model, agg, data):
    payloads = {}
    for kind, e, spec in model.child_tables(agg):
        if kind != "child":
            continue
        key = None
        for cand in [e.get("alias"), e.get("name"),
                     (model.table_name(agg) + "_" + (e.get("alias") or ""))]:
            if cand and cand in data:
                key = cand
                break
        if key and data[key]:
            spec["_var"] = e.get("alias") or e.get("name")
            payloads[spec["table"]] = (spec, data[key])
    return payloads


def _lifecycle_has_void(agg):
    for st in agg.get("lifecycle", []) or []:
        if st in ("已作废", "作废", "VOID", "作废关闭"):
            return True
    return False


def _find_references(model, conn, table, pk_val):
    """Return list of (table, column) that reference pk_val."""
    found = []
    tables = [model.table_name(a) for a in model.aggregates]
    for a in model.aggregates:
        for kind, e, spec in model.child_tables(a):
            if kind == "child":
                tables.append(spec["table"])
    for t in set(tables):
        if t == table:
            continue
        cur = conn.execute(f'PRAGMA table_info("{t}")')
        for col in cur.fetchall():
            cname = col[1]
            try:
                row = conn.execute(f'SELECT COUNT(*) FROM "{t}" WHERE "{cname}"=?',
                                    (str(pk_val),)).fetchone()
                if row and row[0] > 0:
                    found.append((t, cname, row[0]))
            except sqlite3.Error:
                continue
    return found


# ---------------------------------------------------------------- ops
def create(model, conn, agg, data):
    table = model.table_name(agg)
    pk = model.pk_column(agg)
    cols = model.columns(agg)

    # validate refRules
    errs = validate_refrules(agg, data)
    if errs:
        return {"ok": False, "error": "校验失败: " + "; ".join(errs)}

    # build main row (skip system fields — auto-filled below)
    main = {}
    for c in cols:
        if c.get("systemField"):
            continue
        if c["name"] == pk and pk not in data:
            # surrogate handled below
            continue
        main[c["name"]] = _norm_value(c, data.get(c["name"]))

    # PK：优先用传入值；否则按"三字母缩写+四位流水号"自动生成；兜底用 UUID
    if pk in data and data[pk] not in (None, ""):
        main[pk] = data[pk]
    elif pk not in main:
        # 自动编号：取对象 alias 前3位大写 + 四位流水号（从数据库当前最大编号+1）
        auto_id = None
        try:
            alias = agg.get("alias") or agg.get("name", "OBJ")
            prefix = alias[:3].upper() if len(alias) >= 3 else alias.upper()
            # 查询当前最大编号
            cur2 = conn.execute(f'SELECT "{pk}" FROM "{table}" WHERE "{pk}" LIKE ? ORDER BY "{pk}" DESC LIMIT 1', (prefix + '%',))
            row = cur2.fetchone()
            if row:
                last = row[0]
                num_part = ''.join(c for c in last if c.isdigit())
                next_num = int(num_part) + 1 if num_part else 1
            else:
                next_num = 1
            auto_id = f"{prefix}{next_num:04d}"
        except Exception:
            pass
        if not auto_id:
            auto_id = str(uuid.uuid4())
        main[pk] = auto_id

    # Auto-fill system fields (createdBy/createdAt/updatedBy/updatedAt)
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    for c in cols:
        if c.get("systemField") and c["name"] not in main:
            if c["name"] in ("createdBy", "updatedBy"):
                main[c["name"]] = c.get("default") or "admin"
            elif c["name"] in ("createdAt", "updatedAt"):
                main[c["name"]] = now
            elif c["name"] == "flag" and c["name"] not in data:
                # flag defaults to effective/valid
                if c.get("enum"):
                    main[c["name"]] = c["enum"][0]  # first enum value as default valid
                else:
                    main[c["name"]] = _norm_value(c, c.get("default") or True)

    # invariants (build children map from payload)
    payloads = _child_payloads(model, agg, data)
    children_map = {}
    for t, (spec, rows) in payloads.items():
        cname = spec["cols"][0]["name"]  # master fk col name (== pk)
        children_map.setdefault(spec["_var"], [])
        child_attr_names = [c["name"] for c in spec["cols"][1:]]
        for r in (rows if isinstance(rows, list) else []):
            children_map[spec["_var"]].append({k: r.get(k) for k in child_attr_names})
    ierrs, iwarns = validate_invariants(agg, data, children_map)
    if ierrs:
        return {"ok": False, "error": "不变式校验失败: " + "; ".join(ierrs)}

    cur = conn.cursor()
    keys = list(main.keys())
    ph = ",".join("?" for _ in keys)
    cur.execute(f'INSERT INTO "{table}" ({",".join(keys)}) VALUES ({ph})',
                [main[k] for k in keys])
    pk_val = main[pk]
    for t, (spec, rows) in payloads.items():
        for r in (rows if isinstance(rows, list) else []):
            ckeys = [spec["cols"][0]["name"]] + [c["name"] for c in spec["cols"][1:]]
            cvals = [pk_val]
            for c in spec["cols"][1:]:
                cvals.append(_norm_value(c, r.get(c["name"])))
            cur.execute(
                f'INSERT INTO "{t}" ({",".join(ckeys)}) VALUES ({",".join("?"*len(ckeys))})',
                cvals,
            )
    conn.commit()
    return {"ok": True, "id": pk_val, "warnings": iwarns}


def _child_var(agg, spec):
    return spec.get("_var") or "children"


def update(model, conn, agg, pk_val, data):
    table = model.table_name(agg)
    pk = model.pk_column(agg)
    cols = model.columns(agg)

    exists = conn.execute(f'SELECT 1 FROM "{table}" WHERE "{pk}"=?', (str(pk_val),)).fetchone()
    if not exists:
        return {"ok": False, "error": f"未找到 {table} 中 ID={pk_val} 的记录"}

    errs = validate_refrules(agg, data)
    if errs:
        return {"ok": False, "error": "校验失败: " + "; ".join(errs)}

    sets, vals = [], []
    for c in cols:
        if c["name"] == pk:
            continue
        if c.get("systemField"):
            continue  # system fields not user-updatable
        if c["name"] in data:
            sets.append(f'"{c["name"]}"=?')
            vals.append(_norm_value(c, data[c["name"]]))
    # Auto-update system fields
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    for c in cols:
        if c.get("systemField") and c["name"] in ("updatedBy", "updatedAt"):
            sets.append(f'"{c["name"]}"=?')
            vals.append("admin" if c["name"] == "updatedBy" else now)
    if sets:
        vals.append(str(pk_val))
        conn.execute(f'UPDATE "{table}" SET {",".join(sets)} WHERE "{pk}"=?', vals)

    payloads = _child_payloads(model, agg, data)
    if payloads:
        children_map = {}
        for t, (spec, rows) in payloads.items():
            conn.execute(f'DELETE FROM "{t}" WHERE "{spec["cols"][0]["name"]}"=?', (str(pk_val),))
            child_attr_names = [c["name"] for c in spec["cols"][1:]]
            for r in (rows if isinstance(rows, list) else []):
                ckeys = [spec["cols"][0]["name"]] + child_attr_names
                cvals = [str(pk_val)] + [_norm_value(c, r.get(c["name"])) for c in spec["cols"][1:]]
                conn.execute(
                    f'INSERT INTO "{t}" ({",".join(ckeys)}) VALUES ({",".join("?"*len(ckeys))})',
                    cvals,
                )
            children_map.setdefault(spec["_var"], [])
            for r in (rows if isinstance(rows, list) else []):
                children_map[spec["_var"]].append({k: r.get(k) for k in child_attr_names})
        ierrs, _ = validate_invariants(agg, data, children_map)
        if ierrs:
            conn.rollback()
            return {"ok": False, "error": "不变式校验失败: " + "; ".join(ierrs)}
    conn.commit()
    return {"ok": True, "id": pk_val}


def delete(model, conn, agg, pk_val, force=False):
    table = model.table_name(agg)
    pk = model.pk_column(agg)
    exists = conn.execute(f'SELECT 1 FROM "{table}" WHERE "{pk}"=?', (str(pk_val),)).fetchone()
    if not exists:
        return {"ok": False, "error": f"未找到 {table} 中 ID={pk_val} 的记录"}

    # Logical void takes priority: it is a soft status change and MUST be allowed
    # even when child/external references exist (the row is NOT removed, so FK
    # references stay valid). Only the PHYSICAL delete path is reference-guarded.
    if _lifecycle_has_void(agg) and not force:
        conn.execute(f'UPDATE "{table}" SET status=? WHERE "{pk}"=?', ("已作废", str(pk_val)))
        conn.commit()
        return {"ok": True, "id": pk_val, "mode": "logical_void"}

    refs = _find_references(model, conn, table, pk_val)
    if refs and not force:
        detail = "; ".join(f"{t}.{c}({n}条)" for t, c, n in refs)
        return {"ok": False, "error": f"存在下游引用，禁止物理删除。引用: {detail}。可改逻辑作废或 force=true",
                "references": refs}

    # physical delete (children first)
    for kind, e, spec in model.child_tables(agg):
        if kind == "child":
            conn.execute(f'DELETE FROM "{spec["table"]}" WHERE "{spec["cols"][0]["name"]}"=?',
                         (str(pk_val),))
    conn.execute(f'DELETE FROM "{table}" WHERE "{pk}"=?', (str(pk_val),))
    conn.commit()
    return {"ok": True, "id": pk_val, "mode": "physical"}


def get(model, conn, agg, pk_val):
    table = model.table_name(agg)
    pk = model.pk_column(agg)
    row = conn.execute(f'SELECT * FROM "{table}" WHERE "{pk}"=?', (str(pk_val),)).fetchone()
    if not row:
        return None
    rec = dict(row)
    # children
    for kind, e, spec in model.child_tables(agg):
        if kind == "child":
            rows = conn.execute(
                f'SELECT * FROM "{spec["table"]}" WHERE "{spec["cols"][0]["name"]}"=?',
                (str(pk_val),)).fetchall()
            rec[e.get("alias") or e.get("name")] = [dict(r) for r in rows]
    return rec


def list_rows(model, conn, agg, limit=200, offset=0, filters=None):
    table = model.table_name(agg)
    pk = model.pk_column(agg)
    where, vals = [], []
    if filters:
        for k, v in filters.items():
            where.append(f'"{k}" LIKE ?')
            vals.append(f"%{v}%")
    wsql = (" WHERE " + " AND ".join(where)) if where else ""
    sql = f'SELECT * FROM "{table}"{wsql} ORDER BY "{pk}" LIMIT ? OFFSET ?'
    rows = conn.execute(sql, vals + [limit, offset]).fetchall()
    return [dict(r) for r in rows]
