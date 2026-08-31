# -*- coding: utf-8 -*-
"""
Build-time helper: convert ontology YAML files into JSON companions.

The runtime engine reads JSON (zero runtime third-party deps). The YAML files
are kept for human readability / maintenance. Run this after (re)generating YAML.

Usage:
    python engine/yaml2json.py <ont_yaml_dir>
"""
import json
import os
import sys

try:
    import yaml
except ImportError:
    print("[错误] 需要 PyYAML：请先 pip install pyyaml")
    sys.exit(1)


def convert(yaml_dir):
    count = 0
    for fn in os.listdir(yaml_dir):
        if not fn.endswith(".yaml"):
            continue
        src = os.path.join(yaml_dir, fn)
        with open(src, encoding="utf-8") as f:
            data = yaml.safe_load(f)
        dst = os.path.join(yaml_dir, fn[:-5] + ".json")
        with open(dst, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        count += 1
        print(f"  {fn} -> {os.path.basename(dst)}")
    print(f"已转换 {count} 个 YAML 文件。")


if __name__ == "__main__":
    d = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "..", "ont_yaml")
    convert(d)
