---
name: ontology-app-builder
description: 本体驱动构建应用的通用技能。当用户希望把一段业务需求（或上传的需求文档）转换为一套可运行的领域应用技能时使用——自动完成需求探索（按《AI需求探索与确认提示词V4.0》人工确认，九阶段）、生成本体YAML（M1~M7+ME+MU+MM+MI 十一模型）、并产出一个自包含的领域技能（自动建SQLite库、独立HTML录入界面、对话式自然语言查询、知识图谱）。触发词：构建本体应用、生成领域技能、需求转本体、ontology app builder、本体驱动建模。
---

# 本体驱动应用构建器（ontology-app-builder）

你是一个"技能生成器"：你的产出不是业务数据，而是**另一个可安装的 WorkBuddy 技能**（领域技能）。
整个流程分三段，必须按顺序推进，且**所有需要业务判断的点都必须停下让用户确认**。

## 全局约定

- 本体建模规范：严格遵循 `specs/ontology_modeling_framework_v6.md`（最新版）的十一模型元规范与 YAML 模板（M1 对象/M2 行为/M3 规则/ME 事件/M4 场景/M5 主体/M6 流程/M7 报表/**MU UI 模型/MM 对象-表映射/MI 接口模型**）。
- 需求探索规范：严格遵循 `specs/AI需求探索与确认提示词V4.0.md`（最新版）的九阶段交互（阶段零~阶段九，含阶段八接口需求、阶段九 UI 原型），其中**必须人工确认的点**要分批提问并附 AI 建议答案。
- 参考范例：项目下的 `本体YAML范例/` 仅作**格式对标**，不得机械套用其业务内容（尤其注意范例含审批流，若用户原始需求明确"无审批流"，则以用户需求为准，不生成 M6 审批流与事件驱动关闭规则）。
- 运行引擎（engine）路径：`~/.workbuddy/skills/ontology-app-builder/engine/`，生成领域技能时整体拷贝。
- 图谱工具（tools）路径：`~/.workbuddy/skills/ontology-app-builder/tools/`（`build_knowledge_graph.py` + `build_graph_html.py` + `knowledge-graph-template.html`），第 2 段完成后自动运行生成知识图谱。
- Python 运行时：优先使用 `~/.workbuddy/binaries/python/envs/default/Scripts/python.exe`（WorkBuddy managed 环境，已装 pyyaml）；若不存在则回退系统 `python`/`python3`（需确保已安装 pyyaml，可用 `pip install pyyaml` 安装）。构建期 YAML→JSON 依赖 Python。

## 关键工程口径（务必遵守）

1. **以 M1 的 `name` 为准推导数据库表/列**；M7 的 `referenceSql` 仅作业务参考，不作为建表与查询的唯一来源。
2. **生成管线以第 1 段用户确认后的需求为准**，不机械套用任何范例。
3. v1 范围（默认 MVP）：自动建库 + 按对象 CRUD（含主从录入）+ refRules/invariants 校验 + 状态机 + 按 ID 修改 + **独立 HTML 录入表单（所有对象）** + 自然语言查询（外键 ID→名称）。**不含** M3 事件总线 / M6 审批流（除非用户在第 1 段明确需要）。**MU/MM/MI 三模型（UI/表映射/接口）仅供建模参考，不参与运行引擎建库与查询，也不再生成 UI 调用链工作台 HTML（工作台已停用）。**
4. 删除语义：提供两种——物理删除（有下游引用则拒绝，返回引用详情）+ 逻辑作废（若聚合生命周期含"作废/已作废"状态，delete 默认置为作废）。录入 UI 的删除按钮走逻辑作废。
5. 主从录入深度：仅一层子实体（如 合同↔付款条款）。值对象平铺进表单。
6. 本体 YAML 落盘：第 2 段产出存放 `工作区/.workbuddy/ontology/<项目名>/yaml/`；第 3 段将其**内嵌复制**进领域技能包的 `ont_yaml/`。
7. **系统字段自动处理（v1 强制）**：引擎自动为每张表添加并维护 `createdBy`（默认 admin）、`createdAt`（默认当前时间）、`updatedBy`（默认 admin）、`updatedAt`（默认当前时间）；`flag` 类标记字段默认有效。这些字段**不显示在录入表单**，引擎在 CRUD 时自动填充。
8. **录入表单字段处理（v1 强制）**：
   - `DictionaryRef`（数据字典）→ 渲染为下拉框（option = label + code）
   - `AggregateRootRef`（引用类型）→ 渲染为下拉框（option = 名称 + ID）
   - `Enum`（枚举）→ 渲染为下拉框
   - `systemField=true` 或 PK（unique+required）→ **不显示在录入表单**
   - 单表布局：`grid-2-columns`（2 列网格）；主从表布局：`form-top-table-bottom`（上部主表表单，下部子表明细表）
9. **独立 HTML 表单规范（v3 强制）**：
   - 录入表单生成为**独立 HTML 文件**，通过 `present_files` 在右侧面板打开，**不在对话流内嵌**
   - **所有对象必须生成表单**：AI 在第 3 段生成领域技能时，为 M1 中每个聚合根对象（主数据/核心对象）自动生成对应的 `forms/<Alias>_form.html` 录入表单
   - 表单文件生成到技能包的 `forms/` 目录（如 `forms/Customer_form.html`）
   - 表单宽度：`width: 90%; margin: 0 auto;`（占面板宽度 90%，居中）
   - 布局：`grid-template-columns: repeat(2, 1fr);`（每行严格两列，gap 16px）
   - 样式：卡片圆角 14px、双层阴影 `0 1px 3px rgba(0,0,0,.08), 0 8px 24px rgba(0,0,0,.06)`、输入框圆角 9px、聚焦蓝色光晕 `box-shadow: 0 0 0 3px rgba(34,102,227,.18)`、按钮渐变背景 `linear-gradient(135deg,#2266e3,#1a56d4)`
   - **字段渲染规则**：
     - `DictionaryRef`（数据字典）→ 下拉框，option 文本 = `label（code）`，**页面加载时动态从 `GET /api/schema` 获取字典列表填充**
     - `AggregateRootRef`（引用类型）→ 下拉框，option 文本 = `名称（ID）`，**页面加载时动态从 `GET /api/objects/<alias>` 获取引用对象列表填充**
     - `Enum`（枚举）→ 下拉框，option 从 M1 枚举值列表生成
     - **PK/编号字段**：显示在表单中（只读模式 `readonly`），格式为"三字母缩写+四位流水号"（如 `CUS0001`），**不允许用户修改**，由引擎自动生成
     - `systemField=true`（createdBy/createdAt/updatedBy/updatedAt）→ **不显示**
   - **提交**：前端 JS 用**绝对 URL** `fetch(API_BASE + '/api/objects/<alias>',...)` 直调引擎 API 录入；`API_BASE` 变量在 HTML 头部由 AI 注入（值为 `http://127.0.0.1:<port>`）
   - 表单提交成功后弹出**模态对话框**提示"录入成功"（含新记录编号），点击"继续录入"重置表单
   - **打开方式**：AI 生成表单 HTML 文件后，立即调用 `present_files` 传入该文件路径，系统在右侧面板打开预览，用户直接在面板中填表提交
   - **端口注入规范**：AI 在生成表单 HTML 前，必须先启动引擎并获取端口号，在 HTML 中用 `var API_BASE = 'http://127.0.0.1:<port>';` 定义绝对 URL 前缀

---

## 启动前必读（不可跳过）

1. **先读取 `specs/AI需求探索与确认提示词V4.0.md` 全文**——这是需求探索阶段的唯一依据，严格按其"阶段零~阶段九"执行，不得凭记忆或简化。
2. **再读取 `specs/ontology_modeling_framework_v6.md` 全文**——这是本体建模的唯一依据，十一模型（M1~M7+ME+MU+MM+MI）的元规范、YAML 模板、字段含义均以此为准。
3. **读取 `specs/UI布局规范.txt` 全文**——录入表单布局严格遵循此规范（单表 grid-2-columns、主从表 form-top-table-bottom）。

> 以上三个文件已内嵌在技能包的 `specs/` 目录下，必须读完再开始任何工作。

---

## 第 1 段 · 需求探索（必须人工确认）

> 开始前必须已完成"启动前必读"的两个文件读取。

按 `specs/AI需求探索与确认提示词V4.0.md` 九阶段推进：阶段零（原始需求接收与总体理解确认）→ 阶段一（业务对象）→ 阶段二（业务功能与规则）→ 阶段三（事件识别与跨对象影响分析）→ 阶段四（跨对象事件协同场景，可无）→ 阶段五（端到端协同流与审批流，无审批流则标注不适用）→ 阶段六（查询统计与固定报表，至少主动建议 2 个）→ 阶段七（岗位角色与功能权限，v1 默认单用户本地模式、不做登录拦截）→ 阶段八（接口需求，v1 本地模式可简化为"无外部接口"）→ 阶段九（UI 原型探索，可选、以用户确认为前提）。

要求：
- 每批提问 3~6 个，**每个问题必须附带 AI 建议答案 + 理由 + 备选**，用户可回"按AI建议"。
- 所有结论写入需求文档草稿，标注 `[AI自动补全]` / `[已确认]` / `[待确认]`。
- 阶段五若用户需求为"无审批流"，明确登记"核心单据不需要人工审批"结论，不虚构审批流。
- 完成后产出完整需求文档（Markdown），存放到 `工作区/.workbuddy/ontology/<项目名>/需求文档.md`，并汇总待确认项；待确认项清零后才进入第 2 段。该文档将在第 3 段被打包进领域技能包（`<domain-slug>/需求文档.md`），确保技能自包含完整需求背景。

> 不要自己凭空写完整十一模型就跳过确认。探索阶段未确认的需求不可进入建模。

**段间确认（不可跳过）**：第 1 段全部完成后，必须停下来**对话询问用户**，例如：
> "需求探索已完成，全部待确认项已清零。是否进入下一阶段——本体建模（生成十一模型 YAML）？"

**得到用户明确同意后**才进入第 2 段；用户未确认前不得生成任何 YAML。

---

## 第 2 段 · 生成十一模型本体 YAML

> 开始前必须已完成"启动前必读"的两个文件读取，且第 1 段待确认项已清零，且用户已明确同意进入本体建模阶段。

**建模规范（严格遵守）**：本段所有 YAML 必须严格遵循 `specs/ontology_modeling_framework_v6.md` 的本体建模规范——包括其 **十一模型元规范（M1~M7+ME+MU+MM+MI）、每个模型的 YAML 模板、属性字段语义、聚合/子实体/值对象/关联/数据字典/UI模型/表映射/接口契约的定义方式**。生成时逐条对照该文件的模板与字段说明，不得自行发明结构或字段名。

**UI 布局规范**：录入表单布局严格遵循 `specs/UI布局规范.txt`：
- 单表维护 → `grid-2-columns`（2 列网格）
- 主从表维护 → `form-top-table-bottom`（上部主表表单，下部子表明细表）

**系统字段**：M1 建模时无需手动定义 `createdBy`/`createdAt`/`updatedBy`/`updatedAt`/`flag`，引擎自动添加并维护；若显式定义，需标记 `systemField: true`。

基于已确认需求，生成以下文件到 `工作区/.workbuddy/ontology/<项目名>/yaml/`：

| 文件 | 模型 | 说明 |
|---|---|---|
| `m1-object-model.yaml` | 对象 | 聚合根/子实体/值对象/属性/refRules/invariants/数据字典/聚合间关联/`uiBindings`。**建库唯一来源** |
| `m2-behavior-model.yaml` | 行为 | 对象原子行为（含 QUERY 行为，与 M7 一对一）；含 `uiEventRefs` 反向追溯 |
| `m3-rule-model.yaml` | 规则 | 仅跨对象/事件驱动/独立复用规则（v1 若无事件总线，可只保留 VALIDATION 类跨对象规则） |
| `me-event-model.yaml` | 事件 | v1 无审批流时可仅保留最小事件定义或标注"无" |
| `m4-scenario-model.yaml` | 场景 | 无跨对象事件协同则标注"无" |
| `m5-actor-model.yaml` | 主体 | v1 单用户模式可只定义"系统管理员"全权角色 |
| `m6-flow-model.yaml` | 流程 | 无审批流则标注"无" |
| `m7-report-model.yaml` | 查询报表 | 每个报表与唯一 M2 QUERY 行为一对一；含 sourceObjects/joins/conditions/resultColumns/groupBy/referenceSql |
| `mu-ui-model.yaml` | UI 界面 | 屏幕/元素/导航/事件/调用链（建模参考；录入表单渲染参考） |
| `m-mapping-model.yaml` | 对象-表映射 | 对象到数据库表的列映射（isPrimaryKey/isForeignKey/fkTargetTable）——"穿透到数据库表"的权威来源 |
| `mi-interface-model.yaml` | 接口 | 外部接口契约（v1 本地模式可标注"无"） |
| `manifest.json` | 清单 | 见下方格式 |

生成后运行（构建期，把 YAML 转 JSON 供引擎消费）：
```
$PYTHON \
  ~/.workbuddy/skills/ontology-app-builder/engine/yaml2json.py \
  工作区/.workbuddy/ontology/<项目名>/yaml/
```
> 命令中的 `$PYTHON` 指代可用 Python 解释器：优先 `~/.workbuddy/binaries/python/envs/default/Scripts/python.exe`（managed 环境），否则用系统 `python`/`python3`（需已安装 pyyaml）。

**第 2 段完成后自动产出（见 2.5 步）**：
- `工作区/.workbuddy/ontology/<项目名>/knowledge-graph-data.json` — 知识图谱结构化数据
- `工作区/.workbuddy/ontology/<项目名>/知识图谱.html` — 自包含离线 HTML（内嵌 ECharts，双击打开）

**段间确认（不可跳过）**：第 2 段全部 YAML 生成并转换成功后，先**生成知识图谱 HTML**，再**列出全部输出文件清单**（见下方模板），最后停下来**对话询问用户**。

### 2.5 步 · 生成本体知识图谱（自动执行）

YAML 生成完毕后，**自动执行**以下步骤，无需用户确认：

**Step 1：生成图谱数据 JSON**
```
$PYTHON \
  ~/.workbuddy/skills/ontology-app-builder/tools/build_knowledge_graph.py \
  <第2段yaml输出目录> \
  <第2段yaml输出目录>/../knowledge-graph-data.json
```

**Step 2：生成知识图谱自包含 HTML（内嵌 ECharts）**
```
$PYTHON \
  ~/.workbuddy/skills/ontology-app-builder/tools/build_graph_html.py \
  <第2段yaml输出目录>/../knowledge-graph-data.json \
  ~/.workbuddy/skills/ontology-app-builder/tools/echarts.min.js \
  <第2段yaml输出目录>/../知识图谱.html \
  "<领域名>·本体知识图谱"
```

> 输出文件位于本体 YAML 目录的同级目录（`工作区/.workbuddy/ontology/<项目名>/`）：
> - `knowledge-graph-data.json` — 图谱结构化数据
> - `知识图谱.html` — 自包含离线 HTML（内嵌 ECharts，双击即用）

**完成后列出文件清单**（**必须完整列出以下全部文件**）：
```
📁 本体模型文件：
  - m1-object-model.yaml / .json
  - m2-behavior-model.yaml / .json
  - m3-rule-model.yaml / .json
  - me-event-model.yaml / .json
  - m4-scenario-model.yaml / .json
  - m5-actor-model.yaml / .json
  - m6-flow-model.yaml / .json
  - m7-report-model.yaml / .json
  - mu-ui-model.yaml / .json
  - m-mapping-model.yaml / .json
  - mi-interface-model.yaml / .json
  - manifest.json

📊 知识图谱：
  - knowledge-graph-data.json（节点 N 个，关系 M 条）
  - 知识图谱.html（自包含离线文件，双击打开）
```

> 按 v6 建模规范，`mu-ui-model.yaml`（UI 界面）、`m-mapping-model.yaml`（对象-表映射）、`mi-interface-model.yaml`（接口）为标准输出模型（v1 本地模式可标注"无"）。
> **运行期消费边界**：v1 运行引擎（建库 / CRUD / 自然语言查询）仅消费 M1~M7+ME 八模型；`mu` / `m-mapping` / `mi` 三模型不参与引擎建库与查询，仅供建模参考（不再生成 UI 调用链工作台）。

随后**段间确认**询问用户：
> "本体建模与知识图谱已完成。是否进入下一阶段——自包含技能生成（第 3 段）？"

**得到用户明确同意后**才进入第 3 段；用户未确认前不得拷贝引擎或写领域技能 SKILL.md。

---

## 第 3 段 · 生成自包含领域技能

1. 确定技能目录：`~/.workbuddy/skills/<domain-slug>/`（slug 取项目英文短名，如 `contract-management-skill`）。
2. 拷贝引擎：把 `~/.workbuddy/skills/ontology-app-builder/engine/` 整个目录复制到 `<domain-slug>/engine/`。
3. 内嵌本体：把第 2 段目录里的 **全部 YAML 及其同名 JSON** + `manifest.json` 复制到 `<domain-slug>/ont_yaml/`。
4. 拷贝知识图谱：把第 2 段生成的 `knowledge-graph-data.json` + `知识图谱.html` 复制到 `<domain-slug>/`（技能包根目录）。
5. **打包需求文档**：把第 1 段需求探索产出的**完整软件需求文档（Markdown）**复制到 `<domain-slug>/需求文档.md`（技能包根目录）。这是必须步骤，确保领域技能自包含完整需求背景。
6. **生成所有对象录入表单**：为 M1 中每个聚合根对象自动生成 `forms/<Alias>_form.html` 独立 HTML 录入表单（样式与规范见第 9 条关键工程口径）：
   - 数据字典字段（DictionaryRef）→ 页面加载时动态拉取 `GET /api/schema` 填充下拉框
   - 引用字段（AggregateRootRef）→ 页面加载时动态拉取 `GET /api/objects/<目标alias>` 填充下拉框（option = 名称（ID））
   - PK/编号字段 → 显示为只读（readonly）输入框，格式"三字母缩写+四位流水号"，**不允许修改**，由引擎自动生成
   - 枚举字段 → 静态下拉框
   - 系统字段 → 不显示
   - 提交成功 → 弹出模态对话框提示（含新记录编号）+ "继续录入"按钮重置表单
   - 主从对象 → 上部主表表单 + 下部子表明细表（明细行可增删）
7. 写领域技能 `SKILL.md`：用 `scaffold/SKILL.md.template.md` 填充（领域名、对象清单、运行命令、录入/查询指引、对话式 NL 查询示例），**必须补充独立 HTML 表单规范**（见第 9 条关键工程口径）。
8. 创建 `<domain-slug>/data/` 目录（SQLite 运行时生成）。
9. 自测（见模板末说明）：启动引擎 → 建库 → 录入 1 条主数据 + 1 条含子实体的核心对象 → 跑 1 条自然语言查询验证外键转名称。

完成后告诉用户：技能已安装到 `~/.workbuddy/skills/<domain-slug>/`，在对话中输入"打开<领域>录入界面"或"<领域>查询…"即可使用；也可在 WorkBuddy 技能列表中启用。

---

## 注意

- 不要在第 1 段未完成确认前生成 YAML。
- 生成的领域技能完全自包含、零运行时第三方依赖（引擎只用标准库 + SQLite）。
- 若用户后续要扩展 v2（事件总线/审批流/M5 权限/导出），在第 1 段补充对应需求即可，引擎层再迭代。
