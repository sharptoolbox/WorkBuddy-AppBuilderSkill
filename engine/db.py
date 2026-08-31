# -*- coding: utf-8 -*-
"""
SQLite builder driven by the ontology M1 object model.

Mapping rules (aligned with ontology_modeling_framework.md section 2.6):
  Aggregate Root            -> main table (PK = first unique+required attr, else surrogate)
  Collection sub-entity     -> child table with FK to master PK
  Single sub-entity         -> flattened columns into the main table
  ValueObject attribute     -> TEXT column storing JSON
  AggregateRootRef attr     -> TEXT column storing the target aggregate's ID
  DictionaryRef attr        -> TEXT column storing the dictionary item code
  Enum / Date / DateTime    -> TEXT
  Boolean                   -> INTEGER (0/1)
  Integer / Decimal / Money -> INTEGER / REAL
"""
import json
import os
import sqlite3

from loader import SQL_TYPE_MAP


def build_database(model, db_path, reset=False):
    """Create all tables for the domain model. Idempotent unless reset=True."""
    if reset and os.path.exists(db_path):
        os.remove(db_path)
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = OFF")  # logic-level FK protection handled in crud
    cur = conn.cursor()

    # Dictionary lookup table
    cur.execute(
        """CREATE TABLE IF NOT EXISTS __dict(
            dict_id TEXT, type_code TEXT, code TEXT, label TEXT,
            enabled INTEGER, sort_order INTEGER)"""
    )
    cur.execute("DELETE FROM __dict")
    for it in model.dict_items():
        cur.execute(
            "INSERT INTO __dict(dict_id,type_code,code,label,enabled,sort_order) VALUES (?,?,?,?,?,?)",
            (it["dict_id"], it["type_code"], it["code"], it["label"],
             1 if it["enabled"] else 0, it["sort_order"]),
        )

    for agg in model.aggregates:
        _create_main(cur, model, agg)
        _create_children(cur, model, agg)

    conn.commit()
    conn.close()


def _create_main(cur, model, agg):
    table = model.table_name(agg)
    pk = model.pk_column(agg)
    cols = model.columns(agg)
    seen = set()
    parts = []
    for c in cols:
        if c["name"] in seen:
            continue
        seen.add(c["name"])
        if c["name"] == pk:
            parts.append(f'"{pk}" {c["sql_type"]} PRIMARY KEY')
        else:
            parts.append(f'"{c["name"]}" {c["sql_type"]}')
    # flatten single (non-collection) sub-entities
    for kind, e, spec in model.child_tables(agg):
        if kind == "flat" and spec["name"] not in seen:
            seen.add(spec["name"])
            parts.append(f'"{spec["name"]}" {spec["sql_type"]}')
    if pk not in seen:
        parts.insert(0, f'"{pk}" TEXT PRIMARY KEY')
    cur.execute(f'CREATE TABLE IF NOT EXISTS "{table}" ({", ".join(parts)})')


def _create_children(cur, model, agg):
    for kind, e, spec in model.child_tables(agg):
        if kind != "child":
            continue
        cols = spec["cols"]
        parts = ['"__rowid" INTEGER PRIMARY KEY AUTOINCREMENT']
        for c in cols:
            parts.append(f'"{c["name"]}" {c["sql_type"]}')
        cur.execute(f'CREATE TABLE IF NOT EXISTS "{spec["table"]}" ({", ".join(parts)})')
        idx = f'ix_{spec["table"]}_{spec["pk"]}'
        cur.execute(f'CREATE INDEX IF NOT EXISTS "{idx}" ON "{spec["table"]}" ("{spec["pk"]}")')


def dict_label(conn, dict_id, type_code, code):
    row = conn.execute(
        "SELECT label FROM __dict WHERE dict_id=? AND type_code=? AND code=?",
        (dict_id, type_code, code),
    ).fetchone()
    return row[0] if row else code


def connect(db_path):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn
