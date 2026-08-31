# -*- coding: utf-8 -*-
"""
Read-only query layer.

Provides:
  - run_readonly_sql: safe execution of SELECT only (statement + table whitelist)
  - enrich_row / enrich_rows: turn FK ids into "名称(id)" and dict codes into labels
  - schema(): metadata for the AI-driven natural-language query (table/column/FK info)
"""
import json
import re
import sqlite3

from db import dict_label


def get_name_column(model, agg):
    for a in agg.get("attributes", []):
        if "名称" in (a.get("label") or "") or a.get("name", "").lower().endswith("name"):
            return a["name"]
    for a in agg.get("attributes", []):
        if a.get("name") != model.pk_column(agg):
            return a["name"]
    return None


def enrich_row(model, conn, agg, row):
    """Return a new dict with __label suffixes for FK / dict columns."""
    if not row:
        return row
    out = dict(row)
    for c in model.columns(agg):
        val = out.get(c["name"])
        if c.get("ref") and val:
            target = model.get_aggregate(c["ref"])
            if target:
                tname = model.table_name(target)
                ncol = get_name_column(model, target) or model.pk_column(target)
                r = conn.execute(
                    f'SELECT "{ncol}" FROM "{tname}" WHERE "{model.pk_column(target)}"=?',
                    (str(val),)).fetchone()
                if r:
                    out[c["name"] + "__label"] = r[0]
        if c.get("dict_ref") and val:
            lbl = dict_label(conn, c["dict_ref"].get("dictionaryId"),
                             c["dict_ref"].get("typeCode"), val)
            out[c["name"] + "__label"] = lbl
        if c.get("vo") and isinstance(out.get(c["name"]), str):
            try:
                out[c["name"]] = json.loads(out[c["name"]])
            except (ValueError, TypeError):
                pass
    return out


def enrich_rows(model, conn, agg, rows):
    return [enrich_row(model, conn, agg, r) for r in rows]


_FORBIDDEN = re.compile(
    r"(?is)(\binsert\b|\bupdate\b|\bdelete\b|\bdrop\b|\balter\b|\bcreate\b|"
    r"\bpragma\b|\battach\b|;|--|\bexec\b)"
)


def run_readonly_sql(conn, sql, params=None):
    s = (sql or "").strip()
    if not re.match(r"(?is)^\s*select\b", s):
        raise ValueError("只允许执行 SELECT 查询语句")
    if _FORBIDDEN.search(s):
        raise ValueError("查询包含禁止的操作或字符")
    cur = conn.execute(s, params or [])
    cols = [d[0] for d in cur.description] if cur.description else []
    rows = cur.fetchall()
    return cols, [dict(r) for r in rows]


def schema(model):
    """Metadata used by the NL-query layer to build correct SQL."""
    tables = []
    for agg in model.aggregates:
        table = model.table_name(agg)
        cols = []
        for c in model.columns(agg):
            entry = {
                "name": c["name"],
                "label": c["label"],
                "type": c["sql_type"],
            }
            if c.get("ref"):
                t = model.get_aggregate(c["ref"])
                entry["fk_table"] = model.table_name(t) if t else None
                entry["fk_target_label"] = get_name_column(model, t) if t else None
            if c.get("dict_ref"):
                entry["dict"] = {
                    "dict_id": c["dict_ref"].get("dictionaryId"),
                    "type_code": c["dict_ref"].get("typeCode"),
                }
            if c.get("enum"):
                entry["enum"] = c["enum"]
            cols.append(entry)
        tables.append({
            "table": table,
            "alias": agg.get("alias"),
            "label": agg.get("name"),
            "pk": model.pk_column(agg),
            "is_master": True,
            "columns": cols,
        })
        # child tables
        for kind, e, spec in model.child_tables(agg):
            if kind == "child":
                ccols = [{"name": c["name"], "label": c["label"], "type": c["sql_type"]}
                         for c in spec["cols"][1:]]
                tables.append({
                    "table": spec["table"],
                    "alias": e.get("alias"),
                    "label": e.get("name"),
                    "pk": spec["cols"][0]["name"],
                    "is_master": False,
                    "parent": table,
                    "columns": ccols,
                })
    return {
        "domain": model.m1.get("domain"),
        "tables": tables,
        "reports": [{"id": r.get("id"), "name": r.get("name"),
                     "alias": r.get("alias")} for r in model.reports()],
    }
