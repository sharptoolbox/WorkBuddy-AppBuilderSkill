#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""初始化一次需求探索的交付物骨架。

用法：
    python scaffold_deliverables.py "销售合同执行管理"
    python scaffold_deliverables.py "销售合同执行管理" --out D:/work/output
    python scaffold_deliverables.py "销售合同执行管理" --out ./output --date 2026-09-15

产出（默认 <out>/需求探索-<系统名>/）：
    需求规格说明书-<系统名>.md   九部分 + 附录 A 固定结构骨架
    编制说明-<系统名>.md         A~E 五区骨架

仅使用标准库，无需安装依赖。
"""
import argparse
import datetime as _dt
import sys
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
TEMPLATE_DIR = SKILL_DIR / "assets" / "templates"

TEMPLATES = [
    ("需求规格说明书-骨架.md", "需求规格说明书-{name}.md"),
    ("编制说明-骨架.md", "编制说明-{name}.md"),
]


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

    ap = argparse.ArgumentParser(description="初始化需求探索交付物骨架")
    ap.add_argument("name", help="系统 / 项目名称，如「销售合同执行管理」")
    ap.add_argument("--out", default="./output", help="输出根目录（默认 ./output）")
    ap.add_argument("--date", default=None, help="编制日期 YYYY-MM-DD（默认今天）")
    ap.add_argument("--force", action="store_true", help="已存在时覆盖")
    args = ap.parse_args()

    name = args.name.strip()
    if not name:
        print("✗ 系统名称不能为空")
        return 1
    date = args.date or _dt.date.today().isoformat()
    date_compact = date.replace("-", "")

    if not TEMPLATE_DIR.is_dir():
        print(f"✗ 找不到模板目录：{TEMPLATE_DIR}")
        return 1

    target = Path(args.out).expanduser().resolve() / f"需求探索-{name}"
    target.mkdir(parents=True, exist_ok=True)

    created = []
    for src_name, dst_pattern in TEMPLATES:
        src = TEMPLATE_DIR / src_name
        if not src.exists():
            print(f"✗ 缺少模板：{src}")
            return 1
        dst = target / dst_pattern.format(name=name)
        if dst.exists() and not args.force:
            print(f"· 已存在，跳过（用 --force 覆盖）：{dst.name}")
            created.append(dst)
            continue
        text = src.read_text(encoding="utf-8")
        text = (
            text.replace("{{SYSTEM_NAME}}", name)
            .replace("{{DATE_COMPACT}}", date_compact)
            .replace("{{DATE}}", date)
        )
        dst.write_text(text, encoding="utf-8", newline="\n")
        created.append(dst)

    print("✅ 交付物骨架已创建")
    print(f"   目录：{target}")
    for p in created:
        print(f"   - {p.name}")
    print("\n下一步：")
    print("   1) 按 knowledge/01 的八阶段流程推进，每轮确认后写入对应章节（只更新相关章节）")
    print("   2) 定稿后转换单文件 HTML（--mermaid inline：把库内联，交付件离线也能把图渲染出来）：")
    for p in created:
        if p.name.startswith("需求规格说明书"):
            print(f'      python scripts/md_to_requirement_html.py "{p}" --theme light --mermaid inline --version v1.0')
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
