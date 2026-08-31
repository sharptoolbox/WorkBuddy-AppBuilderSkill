---
name: {{DOMAIN_SLUG}}
description: {{DOMAIN_NAME}}领域应用技能（由 ontology-app-builder 生成）。提供：① 独立 HTML 录入表单（右侧面板打开，所有对象均支持，含数据字典/引用动态下拉框、编号自动生成）；② 对话式自然语言查询（自动建库、外键ID转名称）；③ 本体知识图谱可视化；④ 需求文档自包含。当用户提到"{{DOMAIN_NAME}}录入/查询/列表/知识图谱"等时使用。
---

# {{DOMAIN_NAME}}应用（由 ontology-app-builder 生成）

你是本领域的运行助手。底层已内置一个零依赖的运行时引擎（engine/），它读取 `ont_yaml/` 下的本体模型自动建 SQLite 库，并提供录入 API 与只读查询接口。

## 需求文档

技能包内含 `需求文档.md`（完整软件需求规格，由第 1 段需求探索产出），记录了本领域的业务背景、对象定义、功能范围、规则与报表需求。

## 对象清单
{{OBJECTS_TABLE}}

## 一、启动引擎（首次或需要录入/查询时）

用 Bash 在**后台**启动引擎（使用可用的 Python 解释器，优先 WorkBuddy managed 环境）：
```
$PYTHON engine/run.py --port 8990
```
> `$PYTHON` 指可用 Python：优先 `~/.workbuddy/binaries/python/envs/default/Scripts/python.exe`，否则系统 `python`/`python3`。
> 引擎启动时会自动建库（幂等）。数据库位于 `data/app.db`。
> 引擎提供 `http://127.0.0.1:8990` 的 REST API（录入与查询均通过此接口）；**数据录入一律使用独立 HTML 表单（右侧面板打开）**（见下）。

## 二、录入能力（独立 HTML 表单 v3 强制）

**数据录入使用独立 HTML 表单**：AI 为 M1 中每个聚合根对象自动生成 `forms/<Alias>_form.html`，调用 `present_files` 在右侧面板打开，用户直接在面板中填表提交。**禁止**在对话流内嵌表单（不使用 `show_widget` 渲染表单）。

### 独立 HTML 表单规范（严格遵循）

1. **文件位置**：所有表单位于技能包 `forms/` 目录（如 `forms/Customer_form.html`、`forms/Contract_form.html`）。
2. **容器**：表单在 HTML 内用 `width: 90%; margin: 0 auto;` 居中，适应面板宽度。
3. **布局**：`grid-template-columns: repeat(2, 1fr);`（每行严格两列，gap 16px）。
4. **样式**：卡片式（圆角 14px、双层阴影 `0 1px 3px rgba(0,0,0,.08), 0 8px 24px rgba(0,0,0,.06)`）、输入框圆角 9px、聚焦时蓝色光晕（`box-shadow: 0 0 0 3px rgba(34,102,227,.18)`）、按钮渐变背景（`linear-gradient(135deg,#2266e3,#1a56d4)`）。
5. **字段渲染规则**：
   - `DictionaryRef`（数据字典）→ 下拉框，option 文本 = `label（code）`；**页面加载时动态从 `GET /api/schema` 获取字典列表填充**
   - `AggregateRootRef`（引用类型）→ 下拉框，option 文本 = `名称（ID）`，值 = 目标 ID；**页面加载时动态从 `GET /api/objects/<目标alias>` 获取引用对象列表填充**
   - `Enum`（枚举）→ 下拉框，option 从 M1 枚举值列表生成
   - **PK/编号字段**：显示在表单中（只读模式 `readonly`），格式为"三字母缩写+四位流水号"（如 `CUS0001`），**不允许用户修改**，由引擎自动生成
   - `systemField=true`（createdBy/createdAt/updatedBy/updatedAt）→ **不显示**
6. **API 调用**：前端 JS 用**绝对 URL** `var API_BASE = 'http://127.0.0.1:<port>';` 定义前缀，所有 `fetch` 用 `API_BASE + '/api/objects/<alias>'` 直调引擎 API（引擎已配置 CORS `Access-Control-Allow-Origin: *`，独立 HTML 文件可直接跨域调用）。
   - 新增：`POST /api/objects/<alias>`，body=`{字段:值, 子实体alias:[{...}]}`
   - 修改（**必须指定 ID/编号**）：`PUT /api/objects/<alias>/<id>`，body=要改的字段
   - 获取字典/引用：`GET /api/schema`（返回 tables + dictionaries + reports）
   - 获取引用对象列表：`GET /api/objects/<alias>`
7. **提交反馈**：提交成功后弹出**模态对话框**提示"录入成功"（含新记录编号），点击"继续录入"按钮重置表单；失败显示红色错误提示。
8. **主从录入**：上部主表表单 + 下部子表明细表（明细行可增删，提交时随主表 JSON 一起发出）。

字段名用对象的 `alias` 属性名（英文，见对象清单与 `/api/schema`）。
`AggregateRootRef` 字段填目标对象的 ID；`DictionaryRef` 填字典 code。
系统字段（createdBy/createdAt/updatedBy/updatedAt）由引擎自动填充，**不要**在表单与提交数据中出现。

> **端口注入规范**：AI 在生成表单 HTML 前，必须先启动引擎并获取端口号，在 HTML 中用 `var API_BASE = 'http://127.0.0.1:<port>';` 定义绝对 URL 前缀。

## 三、对话式自然语言查询

用户用自然语言提问时，你负责"理解→生成SQL→执行→呈现"：

1. 先 `GET /api/schema` 取得表/列/外键元数据（首次或模型变更后）。
2. 把用户问题翻译成**只读 SELECT**（仅 SELECT，表名/列名来自 schema；外键列用 JOIN 关联出名称列，如 `customer.customerName`）。
3. `POST /api/sql`，body=`{"sql":"..."}`，拿到结果（引擎已把外键 ID 转为名称列 `__label`）。
4. 用表格/自然语言把结果回给用户。

示例：
- 用户："查一下所有已生效的合同，按金额排序"
  → `SELECT contractId, contractName, totalAmount, customer__label FROM Contract WHERE status='已生效' ORDER BY totalAmount DESC`
- 用户："合同 C001 的付款条款有哪些"
  → 先取主记录，再 `SELECT * FROM Contract_PaymentTerm WHERE ContractId='C001'`

> 严禁生成 INSERT/UPDATE/DELETE/DROP 等写语句；`/api/sql` 只接受 SELECT。

## 四、报表

M7 已定义固定报表（见 `ont_yaml/m7-report-model.yaml`），可基于其中 `referenceSql` 口径生成 SELECT 供 `/api/sql` 执行，例如"合同执行情况分析""部门合同统计"。

## 五、本体知识图谱

技能包内含 `知识图谱.html`（自包含离线文件，内嵌 ECharts 库，双击即用），可视化 M1~M7+ME+MU+MM+MI 十一模型本体结构：

- **节点**：聚合根、子实体、值对象、行为、规则、事件、场景、流程、角色、权限、数据字典、查询报表等，按类型颜色区分。
- **关系**：包含、引用、操作对象、产生事件、调用、触发等，边颜色按关系类型区分。
- **交互**：左侧面板过滤节点类型、搜索节点、点击节点查看详情与关联、滚轮缩放、拖拽布局。

> 若 `知识图谱.html` 不存在（如手动删除了），可重新生成（`$PYTHON` 指可用 Python：优先 `~/.workbuddy/binaries/python/envs/default/Scripts/python.exe`，否则系统 `python`/`python3`）：
```
$PYTHON ^
  ~/.workbuddy/skills/ontology-app-builder/tools/build_knowledge_graph.py ^
  ont_yaml/ ^
  knowledge-graph-data.json
$PYTHON ^
  ~/.workbuddy/skills/ontology-app-builder/tools/build_graph_html.py ^
  knowledge-graph-data.json ^
  ~/.workbuddy/skills/ontology-app-builder/tools/echarts.min.js ^
  知识图谱.html ^
  "{{DOMAIN_NAME}}·本体知识图谱"
```
