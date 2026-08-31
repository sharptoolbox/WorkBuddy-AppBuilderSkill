# -*- coding: utf-8 -*-
"""
Ontology model loader.

Reads the manifest.json + 8 model JSON files produced by the ontology-app-builder
pipeline and exposes a unified, query-friendly view of the domain model.

Runtime has ZERO third-party dependencies: it only reads the *.json companion files
(the *.yaml files are kept for human readability / maintenance).
"""
import json
import os


class OntologyModel:
    def __init__(self, yaml_dir):
        self.dir = yaml_dir
        self.manifest = self._load_json("manifest.json") or {}
        # Load every model file declared in the manifest (json companion).
        self.m1 = self._load_model("object") or {}
        self.m2 = self._load_model("behavior") or {}
        self.m3 = self._load_model("rule") or {}
        self.me = self._load_model("event") or {}
        self.m4 = self._load_model("scenario") or {}
        self.m5 = self._load_model("actor") or {}
        self.m6 = self._load_model("flow") or {}
        self.m7 = self._load_model("report") or {}

        # Indexes
        self.aggregates = self.m1.get("aggregates", [])
        self.associations = self.m1.get("aggregate_associations", [])
        self.dictionaries = self.m1.get("data_dictionaries", [])
        self._agg_by_id = {a["id"]: a for a in self.aggregates}
        self._agg_by_alias = {a.get("alias"): a for a in self.aggregates if a.get("alias")}
        self._agg_by_name = {a.get("name"): a for a in self.aggregates if a.get("name")}

    # ---------------------------------------------------------------- loaders
    def _load_json(self, name):
        p = os.path.join(self.dir, name)
        if os.path.exists(p):
            with open(p, encoding="utf-8") as f:
                return json.load(f)
        return None

    def _load_model(self, model_type):
        for f in self.manifest.get("files", []):
            if f.get("model_type") == model_type:
                return self._load_json(f["file_name"].rsplit(".", 1)[0] + ".json")
        # Fallback: try conventional names
        cand = {
            "object": "m1-object-model.json",
            "behavior": "m2-behavior-model.json",
            "rule": "m3-rule-model.json",
            "event": "me-event-model.json",
            "scenario": "m4-scenario-model.json",
            "actor": "m5-actor-model.json",
            "flow": "m6-flow-model.json",
            "report": "m7-report-model.json",
        }.get(model_type)
        return self._load_json(cand) if cand else None

    # ---------------------------------------------------------------- helpers
    def get_aggregate(self, key):
        """Resolve an aggregate by id / alias / name."""
        if key in self._agg_by_id:
            return self._agg_by_id[key]
        if key in self._agg_by_alias:
            return self._agg_by_alias[key]
        if key in self._agg_by_name:
            return self._agg_by_name[key]
        # case-insensitive alias/name
        for a in self.aggregates:
            if a.get("alias", "").lower() == str(key).lower():
                return a
            if a.get("name", "").lower() == str(key).lower():
                return a
        return None

    def table_name(self, agg):
        """SQL table name for an aggregate root (uses alias, English)."""
        return agg.get("alias") or _safe(self._agg_id_short(agg))

    def _agg_id_short(self, agg):
        return agg.get("id", "agg").split("-")[-1]

    def pk_attr(self, agg):
        """Find the primary-key attribute (first unique+required, else first *Id)."""
        attrs = agg.get("attributes", [])
        for a in attrs:
            if a.get("unique") and a.get("required"):
                return a
        for a in attrs:
            if a.get("name", "").lower().endswith("id"):
                return a
        # default surrogate
        return None

    def pk_column(self, agg):
        pk = self.pk_attr(agg)
        if pk:
            return pk["name"]
        return self.table_name(agg) + "_id"

    # ---------------------------------------------------------------- system fields
    # System fields automatically appended to every aggregate root table.
    # These are managed by the engine and never shown in entry forms.
    SYSTEM_FIELDS = [
        {"name": "createdBy",   "label": "创建人",   "type": "String",   "systemField": True, "defaultValue": "admin"},
        {"name": "createdAt",   "label": "创建时间",  "type": "DateTime", "systemField": True},
        {"name": "updatedBy",   "label": "最后更新人","type": "String",   "systemField": True, "defaultValue": "admin"},
        {"name": "updatedAt",   "label": "最后更新时间","type": "DateTime", "systemField": True},
    ]

    def columns(self, agg):
        """Return the flat column list for the main table of an aggregate root.

        Each entry: {name, label, sql_type, ref=None, dict_ref=None, vo=None,
                     enum=None, required, unique, default, systemField=False}
        System fields are always appended at the end (auto-managed by engine).
        """
        cols = []
        seen = set()
        for a in agg.get("attributes", []):
            col = self._attr_column(a)
            cols.append(col)
            seen.add(col["name"])
        # Append system fields not already explicitly defined in M1
        for sf in self.SYSTEM_FIELDS:
            if sf["name"] not in seen:
                col = self._attr_column(sf)
                cols.append(col)
        return cols

    def _attr_column(self, a):
        t = a.get("type")
        col = {
            "name": a["name"],
            "label": a.get("label", a["name"]),
            "sql_type": SQL_TYPE_MAP.get(t, "TEXT"),
            "ref": a.get("targetAggregate") if t == "AggregateRootRef" else None,
            "dict_ref": a.get("dictionaryRef") if t == "DictionaryRef" else None,
            "vo": a.get("valueObjectRef") if t == "ValueObject" else None,
            "enum": a.get("enumValues") if t == "Enum" else None,
            "required": a.get("required", False),
            "unique": a.get("unique", False),
            "default": a.get("defaultValue"),
            "systemField": a.get("systemField", False),
        }
        return col

    def child_tables(self, agg):
        """Build child-table specs for collection-valued sub-entities."""
        specs = []
        for e in agg.get("entities", []):
            card = e.get("cardinality")
            collect = card in (None, "ONE_OR_MORE", "ZERO_OR_MORE", "MANY", "ONE_TO_MANY", "MANY_TO_MANY")
            if not collect:
                # single embedded entity -> flatten into main table
                for a in e.get("attributes", []):
                    col = self._attr_column(a)
                    col["name"] = e["alias"] + "_" + col["name"] if e.get("alias") else col["name"]
                    specs.append(("flat", e, col))
                continue
            table = self.table_name(agg) + (("_" + e["alias"]) if e.get("alias") else "")
            cols = [{"name": self.pk_column(agg), "label": "主表ID", "sql_type": "TEXT",
                     "ref": agg["id"], "dict_ref": None, "vo": None, "enum": None,
                     "required": True, "unique": False, "default": None}]
            for a in e.get("attributes", []):
                cols.append(self._attr_column(a))
            specs.append(("child", e, {"table": table, "pk": self.pk_column(agg), "cols": cols}))
        return specs

    def dict_items(self, dict_id=None, type_code=None):
        out = []
        for d in self.dictionaries:
            if dict_id and d.get("id") != dict_id:
                continue
            for t in d.get("types", []):
                if type_code and t.get("typeCode") != type_code:
                    continue
                for it in t.get("items", []):
                    out.append({
                        "dict_id": d.get("id"),
                        "type_code": t.get("typeCode"),
                        "code": it.get("code"),
                        "label": it.get("label"),
                        "enabled": it.get("enabled", True),
                        "sort_order": it.get("sortOrder", 0),
                    })
        return out

    def reports(self):
        return self.m7.get("query_reports", [])


# Map ontology attribute types -> SQLite column types
SQL_TYPE_MAP = {
    "String": "TEXT",
    "Integer": "INTEGER",
    "Decimal": "REAL",
    "Money": "REAL",
    "Date": "TEXT",
    "DateTime": "TEXT",
    "Boolean": "INTEGER",
    "Enum": "TEXT",
    "DictionaryRef": "TEXT",
    "AggregateRootRef": "TEXT",
    "ValueObject": "TEXT",
}


def _safe(s):
    return "".join(ch for ch in str(s) if ch.isalnum())
