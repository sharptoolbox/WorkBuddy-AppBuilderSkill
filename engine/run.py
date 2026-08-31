# -*- coding: utf-8 -*-
"""
Entry point for a generated domain skill's runtime engine.

Usage:
    python engine/run.py [--port 8990] [--host 127.0.0.1]

It loads the embedded ontology (ont_yaml/*.json), auto-creates the SQLite
database (idempotent) and serves the embedded web UI + API on localhost.
Runtime has ZERO third-party dependencies (only the standard library).
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import loader
import db
import server


def main():
    base = os.path.dirname(os.path.abspath(__file__))
    root = os.path.dirname(base)  # skill root
    yaml_dir = os.path.join(root, "ont_yaml")
    data_dir = os.path.join(root, "data")
    os.makedirs(data_dir, exist_ok=True)

    if not os.path.exists(os.path.join(yaml_dir, "manifest.json")):
        print(f"[错误] 未找到本体模型目录: {yaml_dir}")
        sys.exit(1)

    model = loader.OntologyModel(yaml_dir)
    if not model.aggregates:
        print("[错误] 未解析到任何聚合根，请检查 ont_yaml 下的 JSON 模型文件。")
        sys.exit(1)

    db_path = os.path.join(data_dir, "app.db")
    db.build_database(model, db_path)  # idempotent

    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=int(os.environ.get("PORT", "8990")))
    args = ap.parse_args()

    srv = server.make_server(model, db_path, host=args.host, port=args.port)
    url = f"http://{args.host}:{args.port}"
    print("=" * 56)
    print(f"  本体驱动应用已启动: {url}")
    print(f"  领域: {model.m1.get('domain')}  对象数: {len(model.aggregates)}")
    print(f"  数据库: {db_path}")
    print("=" * 56)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\n已停止。")


if __name__ == "__main__":
    main()
