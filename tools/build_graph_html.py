# -*- coding: utf-8 -*-
"""
知识图谱 HTML 生成脚本（通用版）：
将 knowledge-graph-data.json + echarts.min.js 内嵌进 HTML 模板，输出完全离线可运行的自包含 HTML。
用法：
  python build_graph_html.py <graph_data_json> <echarts_js> <output_html> [title]
  python build_graph_html.py data.json echarts.min.js 知识图谱.html "销售合同管理·本体知识图谱"
"""
import os, json, sys

def main():
    if len(sys.argv) < 4:
        print("用法: python build_graph_html.py <graph_data_json> <echarts_js> <output_html> [title]")
        sys.exit(1)

    data_json = sys.argv[1]
    echarts_js = sys.argv[2]
    out_html   = sys.argv[3]
    title      = sys.argv[4] if len(sys.argv) > 4 else "本体知识图谱"

    # 读取图谱数据
    with open(data_json, encoding='utf-8') as f:
        graph_data = json.load(f)

    # 安全检查
    raw = json.dumps(graph_data, ensure_ascii=False)
    if '</script>' in raw or '<!--' in raw:
        print("❌ 数据含危险字符，中止生成")
        sys.exit(1)

    # 读取 echarts 库
    with open(echarts_js, encoding='utf-8') as f:
        echarts_js_content = f.read()
    if '</script' in echarts_js_content:
        print("❌ echarts 库含 </script>，不能内嵌")
        sys.exit(1)

    # 读取 HTML 模板（同目录下的 knowledge-graph-template.html）
    tpl_path = os.path.join(os.path.dirname(__file__), 'knowledge-graph-template.html')
    if not os.path.exists(tpl_path):
        print(f"❌ 模板文件不存在: {tpl_path}")
        sys.exit(1)
    with open(tpl_path, encoding='utf-8') as f:
        tpl = f.read()

    # 注入图谱数据
    html = tpl.replace('__GRAPH_DATA__', raw)
    html = html.replace('__TITLE__', title)

    # 内嵌 echarts 库（在业务脚本前插入）
    anchor = '<script>\nconst GRAPH = '
    pos = html.find(anchor)
    if pos < 0:
        print("❌ 未找到脚本锚点")
        sys.exit(1)
    echarts_block = '<script>\n' + echarts_js_content + '\n</script>\n'
    html = html[:pos] + echarts_block + html[pos:]

    # 输出
    with open(out_html, 'w', encoding='utf-8') as f:
        f.write(html)

    size_kb = os.path.getsize(out_html) / 1024
    print(f"✅ 知识图谱 HTML 已生成: {out_html}")
    print(f"   大小: {size_kb:.1f} KB")
    print(f"   内嵌 echarts: {'是' if echarts_js_content[:20] in html else '否'}")
    print(f"   脚本配对: {html.count('<script>') == html.count('</script>')}")

if __name__ == '__main__':
    main()
