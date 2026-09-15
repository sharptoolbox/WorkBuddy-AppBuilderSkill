# UI/UE 界面设计规范

> 版本 1.0 · 基于 `ai-prototype` 源代码逆向 + `mu-ui-model.yaml` 界面建模

---

## 1. 文档说明

### 1.1 目的

本规范用于指导 AI 在开发新系统时，**复用当前 `ai-prototype` 原型系统的完整视觉风格与交互模式**，使新开发出来的系统界面与现有原型高度一致。

### 1.2 信息来源与分工

| 来源 | 提供内容 |
|---|---|
| `mu-ui-model.yaml`（本体模型 MU） | 界面清单、菜单树、界面类型、字段/控件、操作功能点与行为映射 |
| `ai-prototype` 源代码（逆向） | **具体样式风格**：配色、字体、CSS、组件写法、布局细节 |

**原则**：MU 模型决定"有哪些界面、每个界面有哪些字段和按钮"；本规范决定"这些界面长什么样、如何排布、用什么样式"。

### 1.3 使用方式

AI 生成新系统时，按以下顺序执行：

1. 读 `mu-ui-model.yaml` 得到菜单树、界面列表、字段、操作点；
2. 按本规范第 4～12 章的布局规则与样式 token 装配界面；
3. 直接复用本规范第 13 章 CSS 样式库与第 14 章组件伪代码。

---

## 2. 整体设计原则

1. **Hybrid 布局**：固定功能界面（左侧菜单 + 中间多标签工作区）与 AI 动态界面（右侧对话区）共存；
2. **紧凑专业**：全局 9pt 字体，信息密度高，接近传统企业级桌面系统；
3. **表格化表单**：表单标签右对齐、控件左对齐，整体呈规整的两列网格；
4. **扁平化**：卡片圆角归零、无阴影，靠边框和底色分层；
5. **品牌色统一**：深色导航栏 + 品牌蓝贯穿。

---

## 3. 整体布局架构（三栏结构）

```
┌──────────────────────────────────────────────────────────────────────┐
│  Header 顶栏（深色 #111827，高 60px）                                 │
├───────────────┬────────────────────────────────┬─────────────────────┤
│               │                                │                     │
│  Sidebar      │  MainArea 多标签工作区          │  AIChat             │
│  左侧菜单      │  （中间弹性区域）               │  右侧 AI 对话        │
│  (250px)      │                                │  (400px)            │
│               │                                │                     │
└───────────────┴────────────────────────────────┴─────────────────────┘
```

- 左侧菜单与右侧对话区支持拖拽调整宽度，可显隐；
- 中间工作区为弹性自适应区域。

### 3.1 顶栏 Header

- 背景 `#111827`，文字白色，高度 60px；
- 左：侧栏折叠按钮（`PanelLeftClose`）+ 系统标题（加粗）；
- 右：当前用户名（`User` 图标）+ 分割线 + AI 对话折叠按钮（`PanelRightClose`）+ 退出按钮（`LogOut`）。

### 3.2 左侧菜单 Sidebar（两级布局）

- 白底，宽 250px，可折叠；
- 菜单层级固定 **两级**：一级菜单（分组）+ 二级菜单（叶子，触发打开标签页）；
- 一级菜单：图标 + 标题 + 展开/收起箭头（`ChevronDown/ChevronRight`），加粗；
- 二级菜单：缩进 20px，图标 + 标题；
- 选中态：文字品牌蓝 + 浅蓝底 `#eff6ff` + 右侧 3px 品牌蓝竖条；
- hover：浅灰底 `#f8fafc`。

> 即使某一级菜单下只有一个二级菜单，也必须保留两级结构（二级菜单不可省略）。

### 3.3 中间工作区 MainArea（多标签）

- 顶部标签栏：高 48px，白底，横向滚动；
- 标签：圆角 10px，选中态浅蓝底 `#eff6ff` + 品牌蓝字 + 浅蓝边框 `#dbeafe`；每标签含关闭按钮（`X`）；
- 内容区：`padding: 15px`，背景 `#f0f2f6`，纵向滚动。

### 3.4 右侧 AI 对话 AIChat

- 白底，宽 400px，左边界 1px 分割线；
- 头部：品牌蓝圆角方块内 `Sparkles` 图标 + 「AI 智能助理」标题；
- 消息区：浅灰底 `#fcfdfe`，气泡样式（用户右对齐品牌蓝底白字，AI 左对齐白底）；
- 输入区：圆角 textarea + 右下角品牌蓝发送按钮；
- 底部灰字提示。

### 3.5 登录界面 Login

详见第 10 章。

---

## 4. 设计 Token

### 4.1 配色

| 变量 | 值 | 用途 |
|---|---|---|
| `--primary-color` | `#2266e3` | 品牌蓝（主按钮、链接、选中态） |
| `--primary-hover` | `#1a56c0` | 品牌蓝 hover |
| `--bg-color` | `#f0f2f6` | 页面背景 |
| `--card-bg` | `#ffffff` | 卡片背景 |
| `--text-primary` | `#1e293b` | 主文字 |
| `--text-secondary` | `#5b6e8c` | 次文字/标签 |
| `--border-color` | `#e2edf2` | 输入边框 |
| `--divider-color` | `#e4e7ec` | 分割线 |
| `--nav-bg` | `#111827` | 顶栏深色 |
| `--nav-text` | `#ffffff` | 顶栏文字 |
| `--nav-item-hover` | `rgba(255,255,255,0.1)` | 顶栏 hover |
| `--nav-item-active` | `#2563eb` | 导航选中 |

**浅蓝交互色**（选中/激活背景）：`#eff6ff`、`#dbeafe`

**状态色**（badge 用「底 / 字」配对）：

| 状态 | 底色 | 文字色 |
|---|---|---|
| 正常/成功 | `#dcfce7` | `#166534` |
| 考察中/待审核/警告 | `#fef9c3` | `#854d0e` |
| 异常/危险 | `#fee2e2` | `#991b1b` |
| 已提交/信息 | `#dbeafe` | `#1e40af` |
| 已关闭/中性 | `#f1f5f9` | `#475569` |

删除/危险操作：`#ef4444`

### 4.2 圆角

| 变量 | 值 | 用途 |
|---|---|---|
| `--radius-lg` | `28px` | 大圆角 |
| `--radius-md` | `12px` | 输入框、卡片 |
| `--radius-sm` | `8px` | 小圆角 |

> 注意：卡片 `.card` 实际圆角归零（`border-radius: 0`）、无阴影，靠 1px 边框分隔。

### 4.3 阴影

- `--shadow-sm`: `0 8px 20px rgba(0,0,0,0.03), 0 2px 6px rgba(0,0,0,0.05)`
- `--shadow-md`: `0 20px 35px -10px rgba(0,0,0,0.15)`

### 4.4 尺寸

| 变量 | 值 |
|---|---|
| `--header-height` | `60px` |
| `--sidebar-width` | `250px` |
| `--chat-width` | `400px` |

---

## 5. 字体规范

- 全局基准字体：**9pt**（约 12px）；
- 字体族：`'Inter', system-ui, -apple-system, 'Segoe UI', Roboto, 'Helvetica Neue', sans-serif`；
- 层次区分靠 `font-weight`（400 正文 / 500 按钮标签 / 600 表头与强调 / 700 标题），不靠字号放大；
- 标签列固定宽度 **96px**，右对齐。

---

## 6. 通用组件规范

### 6.1 按钮

- 圆角胶囊 `40px`；
- 主按钮：品牌蓝底白字；次按钮：白底 + `#cbd5e1` 边框；
- 尺寸：`padding: 6px 18px`，内含图标（14px）+ 文字，`gap: 6px`。

### 6.2 输入控件

- `input/select/textarea`：`padding: 6px 10px`、圆角 `8px`、1px `#e2edf2` 边框；
- 聚焦：品牌蓝边框 + `0 0 0 3px rgba(37,99,235,0.1)` 光晕。

### 6.3 表格

- 表头：浅灰底 `#f9fafb`，次文字色，加粗，`padding: 8px 12px`；
- 单元格：`padding: 8px 12px`，下边框 `#f0f2f5`；
- 行 hover：`#fafcff`；
- 从表内联编辑：无边框透明输入框（`.table-input`），hover/focus 显示边框。

### 6.4 分页

- 右对齐，`共 N 条 / X 页` + `上一页 / 页码 / 下一页` 按钮；
- 当前页按钮品牌蓝，其余白底描边。

### 6.5 状态标签（badge）

- `padding: 2px 8px`、圆角 `12px`、字重 500；
- 按第 4.1 节状态色配对着色。

### 6.6 表单布局（表格化）

**核心规则：标签右对齐、控件左对齐，形成规整的「标签列 + 控件列」网格。**

```css
.form-item {
  display: flex;
  align-items: center;
  gap: 8px;
}
.form-item .field-label {
  flex-shrink: 0;
  white-space: nowrap;
  text-align: right;        /* 标签右对齐 */
  width: 96px;              /* 固定列宽，表格化对齐 */
  color: var(--text-secondary);
}
.form-item .field-control {
  flex: 1;
  min-width: 0;
}
```

- 必填标记：标签左侧红色 `*`（`.field-label.required::before { content: '* '; }`）。

---

## 7. 三类界面布局规范

### 7.1 单表维护界面

- 一行布置 **2 个**属性控件；
- 标签右对齐、控件左对齐；
- 备注/长文本字段一行只布置 1 个控件（占满整行）。

```
┌──────────────────────────────────────────────────────────────┐
│ 界面标题                                        [重置] [保存] │
├──────────────────────────────────────────────────────────────┤
│     字段A：[input_______]      字段B：[input_______]          │
│     字段C：[select▾_____]      字段D：[select▾_____]          │
│     备注  ：[textarea___________________________]            │
└──────────────────────────────────────────────────────────────┘
```

### 7.2 主从表维护界面

- 主表一行布置 **3 个**属性控件，标签右对齐、控件左对齐；
- 从表在下方，**表格化**布置，数据新增/维护/删除**直接在表格内动态完成**（内联编辑 + 行内删除按钮 + 添加行按钮）。

```
┌──────────────────────────────────────────────────────────────┐
│ 界面标题                                        [重置] [保存] │
├──────────────────────────────────────────────────────────────┤
│  字段A：[____]  字段B：[____]  字段C：[____]                  │
│  字段D：[____]  字段E：[____]  字段F：[____]                  │
│  备注  ：[________________________________]                   │
├──────────────────────────────────────────────────────────────┤
│ 明细（从表）                                    [+ 添加行]    │
│ ┌────┬──────┬──────┬──────┬──────┬──────┬──────┬────┐        │
│ │No. │字段1 │字段2 │字段3 │数量  │单价  │总金额 │操作│        │
│ ├────┼──────┼──────┼──────┼──────┼──────┼──────┼────┤        │
│ │ 1  │[___] │[___] │[___] │[___] │[___] │ xxx  │ 🗑 │        │
│ └────┴──────┴──────┴──────┴──────┴──────┴──────┴────┘        │
│                                    总计项数:N  总额:¥xxx     │
└──────────────────────────────────────────────────────────────┘
```

### 7.3 查询列表界面

- 查询条件区在**上**，一行布置 **3 个**属性控件，标签右对齐、控件左对齐，独立「查询/重置」按钮行；
- 查询结果表格在**下**，表格化布局，**支持分页**。

```
┌──────────────────────────────────────────────────────────────┐
│ 查询条件区                                                    │
│  条件A：[____]  条件B：[____]  条件C：[____]                  │
│                          [查询] [重置]                        │
├──────────────────────────────────────────────────────────────┤
│ 查询结果                                   共 N 条记录          │
│ ┌──────┬──────┬──────┬──────┬──────┬──────┬────┐             │
│ │列1   │列2   │列3   │列4   │列5   │状态  │操作│             │
│ └──────┴──────┴──────┴──────┴──────┴──────┴────┘             │
│                          共 N 条 / X 页  [上一页][1][下一页]  │
└──────────────────────────────────────────────────────────────┘
```

---

## 8. 控件类型映射

由 M1 属性类型（或 MU 元素 `type`）决定界面控件：

| 属性类型 / 元素 type | 界面控件 | 说明 |
|---|---|---|
| Date / DateTime | 日期控件（`DATEPICKER`） | 原生 `type="date"` |
| Enum / DictionaryRef | 下拉列表框（`COMBO`） | `select` |
| AggregateRootRef | 跳选框（`POPUP_SELECT`） | 文本框 + 右侧按钮弹窗选择 |
| Boolean | 复选框（`CHECKBOX`） | `type="checkbox"` |
| String（长文本/备注） | 多行文本域（`TEXTAREA`） | `textarea` |
| Integer / Decimal / Money | 数字框（`NUMBER`） | `type="number"` |
| 其它 String | 文本框（`TEXTBOX`） | `type="text"` |
| 明细/结果 | 表格（`GRID`） | `table` |

---

## 9. 菜单导航规范（两级）

- 菜单树固定 **两级**：一级菜单（分组）→ 二级菜单（叶子，关联界面）；
- 一级菜单必须至少包含一个二级菜单；
- 只有二级菜单触发打开标签页；
- 结构示例：

```
├── 一级菜单A
│   ├── 二级菜单A-1  → 界面A-1
│   └── 二级菜单A-2  → 界面A-2
├── 一级菜单B
│   └── 二级菜单B-1  → 界面B-1
```

对应 MU 模型 `application.menus[].children[].screenRef`。

---

## 10. 登录界面布局

- 全屏居中，浅灰背景 `#f0f2f6`；
- 居中卡片宽约 400px、`padding: 40px`、白底、1px 分割线边框；
- 结构：品牌蓝圆角方块 Logo 图标 → 系统标题（加粗）→ 副标题（次文字色）→ 用户名输入（左侧 `User` 图标内嵌）→ 密码输入（左侧 `Lock` 图标内嵌）→ 登录按钮（品牌蓝，全宽，高 44px）→ 底部灰字提示。

```
┌─────────────────────────────────────────┐
│           [🔒 品牌蓝 Logo]               │
│              系统标题                    │
│         请登录您的账号以继续              │
│  👤 [用户名________________]             │
│  🔒 [密码__________________]             │
│  [          立即登录 →        ]          │
│        模拟登录账号: admin               │
└─────────────────────────────────────────┘
```

---

## 11. 审批功能双按钮

带审批流程的录入界面，必须提供两个**独立**按钮功能点：

- **保存草稿**（`DRAFT`）：仅保存，对象置为"草稿"态；
- **提交**（`SUBMIT`）：保存并进入审批流。

对应 MU 模型 `actions[]` 的 `actionType: DRAFT / SUBMIT`，分别映射到两个 M2 行为。

---

## 12. AI 动态渲染规范

AI 对话区支持四类渲染（详见架构文档第 9 章）：

1. `text`：业务说明 / 状态反馈；
2. `table`：列表 / 统计 / 结构化结果；
3. `chart`：趋势 / 分布图，用 `ECharts`；
4. `action`：引导打开页面 / 执行行为。

AI 对话区渲染的表格、状态标签必须与固定页面**共用同一套样式**（同 CSS 类）。

---

## 13. CSS 样式库（完整 variables.css）

> 以下是可直接复用的完整样式库，AI 生成系统时原样使用。

```css
:root {
    --primary-color: #2266e3;
    --primary-hover: #1a56c0;
    --bg-color: #f0f2f6;
    --card-bg: #ffffff;
    --text-primary: #1e293b;
    --text-secondary: #5b6e8c;
    --border-color: #e2edf2;
    --divider-color: #e4e7ec;
    --radius-lg: 28px;
    --radius-md: 12px;
    --radius-sm: 8px;
    --shadow-sm: 0 8px 20px rgba(0,0,0,0.03), 0 2px 6px rgba(0,0,0,0.05);
    --shadow-md: 0 20px 35px -10px rgba(0,0,0,0.15);
    --font-family: 'Inter', system-ui, -apple-system, 'Segoe UI', Roboto, 'Helvetica Neue', sans-serif;

    /* 统一字体 9pt */
    --font-size-base: 9pt;
    /* 表单标签列宽 */
    --field-label-width: 96px;

    /* 深色导航 */
    --nav-bg: #111827;
    --nav-text: #ffffff;
    --nav-item-hover: rgba(255, 255, 255, 0.1);
    --nav-item-active: #2563eb;

    --sidebar-width: 250px;
    --chat-width: 400px;
    --header-height: 60px;
}

* { margin: 0; padding: 0; box-sizing: border-box; }

body {
    background-color: var(--bg-color);
    font-family: var(--font-family);
    color: var(--text-primary);
    font-size: var(--font-size-base);
    line-height: 1.5;
    overflow: hidden;
}

/* 卡片：扁平化（圆角归零、无阴影） */
.card {
    background: var(--card-bg);
    border-radius: 0;
    box-shadow: none;
    padding: 24px;
    border: 1px solid var(--divider-color);
    margin-bottom: 20px;
}

/* 按钮 */
.btn {
    padding: 6px 18px;
    border-radius: 40px;
    font-weight: 500;
    cursor: pointer;
    transition: 0.2s;
    font-size: var(--font-size-base);
    border: none;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    gap: 6px;
}
.btn-primary { background-color: var(--primary-color); color: white; }
.btn-primary:hover { background-color: var(--primary-hover); }
.btn-secondary { background-color: white; border: 1px solid #cbd5e1; color: var(--text-primary); }
.btn-secondary:hover { background-color: #f8fafc; }

/* 输入控件 */
input, select, textarea {
    padding: 6px 10px;
    border-radius: var(--radius-sm);
    border: 1px solid var(--border-color);
    font-size: var(--font-size-base);
    font-family: var(--font-family);
    transition: all 0.2s;
    outline: none;
    width: 100%;
}
input:focus, select:focus, textarea:focus {
    border-color: var(--primary-color);
    box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.1);
}

/* 表单布局：标签右对齐、控件左对齐（表格化） */
.form-grid-2 { display: grid; grid-template-columns: repeat(2, 1fr); gap: 14px 28px; }
.form-grid-3 { display: grid; grid-template-columns: repeat(3, 1fr); gap: 14px 24px; }

.form-item { display: flex; align-items: center; gap: 8px; min-width: 0; }
.form-item .field-label {
    flex-shrink: 0;
    white-space: nowrap;
    color: var(--text-secondary);
    font-size: var(--font-size-base);
    text-align: right;
    width: var(--field-label-width);
}
.form-item .field-label.required::before { content: '* '; color: #ef4444; }
.form-item .field-control { flex: 1; min-width: 0; }
.form-item.span-2 { grid-column: span 2; }
.form-item.span-3 { grid-column: span 3; }

/* 表格 */
.table-container {
    background: white;
    border-radius: var(--radius-md);
    overflow: hidden;
    border: 1px solid var(--divider-color);
}
table { width: 100%; border-collapse: collapse; font-size: var(--font-size-base); }
th {
    text-align: left;
    padding: 8px 12px;
    font-weight: 600;
    background-color: #f9fafb;
    border-bottom: 1px solid var(--divider-color);
    color: var(--text-secondary);
}
td { padding: 8px 12px; border-bottom: 1px solid #f0f2f5; font-size: var(--font-size-base); }
tr:hover { background-color: #fafcff; }

/* 从表内联编辑 */
.table-input {
    width: 100%;
    padding: 4px 6px;
    border: 1px solid transparent;
    background: transparent;
    border-radius: 4px;
    font-size: var(--font-size-base);
    font-family: var(--font-family);
    transition: all 0.15s;
}
.table-input:hover { border-color: var(--border-color); background: #fff; }
.table-input:focus { border-color: var(--primary-color); background: #fff; outline: none; }

/* 分页 */
.pagination { display: flex; align-items: center; gap: 6px; font-size: var(--font-size-base); }
.pagination .page-btn { padding: 4px 10px; font-size: var(--font-size-base); min-width: 28px; text-align: center; }

/* 滚动条 */
::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-thumb { background: #cbd5e1; border-radius: 10px; }
::-webkit-scrollbar-track { background: transparent; }
```

---

## 14. 组件伪代码片段

### 14.1 单表维护界面（TSX）

```tsx
<div className="card">
  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
    <h2 style={{ fontWeight: 700 }}>界面标题</h2>
    <div style={{ display: 'flex', gap: '12px' }}>
      <button className="btn btn-secondary"><RotateCcw size={14} /> 重置</button>
      <button className="btn btn-primary"><Save size={14} /> 保存</button>
    </div>
  </div>
  <div className="form-grid-2">
    <div className="form-item">
      <label className="field-label required">字段A</label>
      <div className="field-control"><input type="text" /></div>
    </div>
    <div className="form-item">
      <label className="field-label">字段B</label>
      <div className="field-control"><select>...</select></div>
    </div>
    <div className="form-item span-2">
      <label className="field-label">备注</label>
      <div className="field-control"><textarea rows={3} /></div>
    </div>
  </div>
</div>
```

### 14.2 主从表维护界面（TSX）

```tsx
<div className="form-grid-3" style={{ marginBottom: '24px' }}>
  {/* 主表：一行 3 个 form-item，标签右对齐、控件左对齐 */}
  <div className="form-item"><label className="field-label required">订单编号</label><div className="field-control"><input /></div></div>
  {/* ... */}
</div>
{/* 从表：表格化，内联编辑 + 行内删除 */}
<div className="table-container">
  <table>
    <thead><tr><th>No.</th><th>字段1</th><th>字段2</th><th>操作</th></tr></thead>
    <tbody>
      {items.map((item, i) => (
        <tr key={item.id}>
          <td>{i + 1}</td>
          <td><input className="table-input" value={item.f1} onChange={...} /></td>
          <td><input className="table-input" value={item.f2} onChange={...} /></td>
          <td><button onClick={() => removeItem(item.id)} style={{ color: '#ef4444' }}><Trash2 size={14} /></button></td>
        </tr>
      ))}
    </tbody>
  </table>
</div>
<button className="btn btn-secondary" onClick={addItem}><Plus size={14} /> 添加行</button>
```

### 14.3 查询列表界面（TSX）

```tsx
{/* 条件区 */}
<div className="card" style={{ padding: '20px' }}>
  <div className="form-grid-3">
    <div className="form-item"><label className="field-label">条件A</label><div className="field-control"><input /></div></div>
    {/* ... */}
  </div>
  <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '12px', marginTop: '16px' }}>
    <button className="btn btn-primary"><Search size={14} /> 查询</button>
    <button className="btn btn-secondary"><RotateCcw size={14} /> 重置</button>
  </div>
</div>
{/* 结果区 */}
<div className="card" style={{ padding: 0, overflow: 'hidden' }}>
  <div style={{ padding: '14px 20px', borderBottom: '1px solid var(--divider-color)' }}>
    <h3 style={{ fontWeight: 700 }}>查询结果</h3>
  </div>
  <div className="table-container"><table>...</table></div>
  <div style={{ padding: '14px 20px', display: 'flex', justifyContent: 'flex-end' }}>
    <div className="pagination">
      <button className="btn btn-secondary page-btn">上一页</button>
      <button className="btn btn-primary page-btn">1</button>
      <button className="btn btn-secondary page-btn">下一页</button>
    </div>
  </div>
</div>
```

### 14.4 左侧两级菜单（TSX）

```tsx
const menuData = [
  { id: 'a', title: '一级菜单A', icon: <Database size={18} />, children: [
      { id: 'a-1', title: '二级菜单A-1', icon: <PlusCircle size={16} />, type: 'xxx' },
      { id: 'a-2', title: '二级菜单A-2', icon: <Search size={16} />, type: 'yyy' },
  ]},
  // 每个一级菜单下至少一个二级菜单
];
// 一级菜单渲染：图标 + 标题 + ChevronDown/Right
// 二级菜单：缩进 20px，点击 onMenuClick 打开标签页
// 选中态：color 品牌蓝 + background #eff6ff + borderRight 3px 品牌蓝
```

### 14.5 登录界面（TSX）

```tsx
<div style={{ height: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', background: 'var(--bg-color)' }}>
  <div className="card" style={{ width: '400px', padding: '40px', display: 'flex', flexDirection: 'column', gap: '24px' }}>
    <div style={{ textAlign: 'center' }}>
      <div style={{ width: '64px', height: '64px', background: 'var(--primary-color)', borderRadius: '16px', margin: '0 auto 16px', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'white' }}>
        <Lock size={32} />
      </div>
      <h1 style={{ fontWeight: 800, color: 'var(--nav-bg)' }}>系统标题</h1>
      <p style={{ color: 'var(--text-secondary)', marginTop: '8px' }}>请登录您的账号以继续</p>
    </div>
    {/* 用户名/密码：左侧内嵌图标 + input paddingLeft 40px */}
    <button type="submit" className="btn btn-primary" style={{ width: '100%', height: '44px' }}>立即登录</button>
  </div>
</div>
```

---

## 15. 与本体模型 MU 的对应关系

| MU 模型元素 | 本规范对应 |
|---|---|
| `application.menus`（两级） | 第 9 章 菜单导航 |
| `screen.screenType`（SINGLE_FORM / MASTER_DETAIL_FORM / QUERY_LIST） | 第 7 章 三类界面布局 |
| `element.type`（TEXTBOX / COMBO / DATEPICKER / POPUP_SELECT / ...） | 第 8 章 控件类型映射 |
| `element.dataBinding`（M1 属性） | 决定控件类型 |
| `actions[].actionType`（DRAFT / SUBMIT / APPROVE / ...） | 第 11 章 审批双按钮 |
| `layout`（ASCII 布局图） | 第 7 章 ASCII 布局基准 |

---

## 16. 静态界面原型装配规范（需求文档「第九部分 子条 1」专用）

> 本章是《软件需求编写规范 V10.0》第九部分子条 1「UI 界面说明」的**装配基准**。需求文档里的界面说明**必须是这一章装配出来的真实界面原型**，不得用「区域 / 行 / 单元格 1-4」的表格描述控件位置，也不得使用 ASCII 字符框图。

### 16.1 载体形式（强制）

在 Markdown 中以 ` ```html ` 围栏代码块书写原型片段：

````text
（1）UI 界面说明

<一句话说明该界面的形态与关键动作>

```html
<div class="mock"> … </div>
```

<p class="fig-cap">图 9-x　某某界面原型（说明关键规则）</p>
````

- 转换器 `scripts/md_to_requirement_html.py` 对 ` ```html ` 代码块**原样透传**（不转义），并已内置本章全部样式（`.mock / .mock-head / .toolbar / .zone / .form-grid-3 / .form-item / .ctl / .mbtn / .badge / .tbl-mini / .mock-foot / .pager / .mock-modal / .mock-dialog`），**无需额外引入 CSS**；
- `lang` 用 ` ```mermaid ` 仍渲染流程图、用 ` ```html ` 渲染原型，两者互不干扰；
- 原型片段中**不写 `<style>`、不引用外部资源、不写 JS**；确需微调宽度时只允许用 `style="width:xxx"` 之类的极小内联样式。

### 16.2 类名清单（唯一可用集合）

| 层级 | 类名 / 结构 | 用途 |
|---|---|---|
| 外壳 | `.mock` > `.mock-head` + （`.toolbar` / `.mock-body` / 表格）+ `.mock-foot` | 一个界面原型的容器。`.mock-head` 内含 `.mtitle`（界面标题，建议写「界面名（屏幕类型）」）与 `.mock-actions`（右上按钮组） |
| 安全区 | `.zone` > `.zone-title` | 界面的分区（查询条件区、明细区、历史记录区、意见区）。虚线边框，仅用于原型分区示意 |
| 工具栏 | `.toolbar` > `.filters` | 查询条件区：`.filters` 内并排若干条件控件 + 「查询」「重置」按钮 |
| 表单 | `.form-grid-3` / `.form-grid-2` > `.form-item`(可加 `.span-2` / `.span-3`) > `.field-label`(可加 `.required`) + `.field-control` | 表格化表单。**单表 2 列、主从表主表 3 列、查询条件 3 列**（与第 7 章一致）；必填字段加 `required`（自动前置红色 `*`） |
| 控件形态 | `.ctl`（文本框）｜`.ctl.ro`（只读，灰底）｜`.ctl.gr`（下拉，文案以 ` ▾` 结尾）｜`.ctl.psi` + `<span class="bt">…</span>`（跳选框，右侧「…」按钮）｜`.ctl.ta`（多行文本域）｜`.ck` + `<i class="on"></i>`（复选框） | **必须按属性类型选对形态**，见第 8 章控件映射 |
| 按钮 | `.mbtn.p`（主按钮）｜`.mbtn.s`（次按钮）｜`.mbtn.d`（危险，删除 / 驳回）｜加 `.sm` 变小（列表行内按钮） | 按钮文案直接写上功能点编号，如 `💾 保存草稿（DRAFT · FUNC-22）` |
| 状态 | `.badge` + `.b-succ`（已审核 / 已生效 / 已提交 / 在职）｜`.b-warn`（待审核 / 需注意 / 未提交）｜`.b-danger`（已驳回 / 超期）｜`.b-info`（进行中 / 已提交信息）｜`.b-neutral`（草稿 / 已取消 / 已关闭 / 停用） | 状态色**必须**按本表取用，与第 4.1 节状态色一致 |
| 数据表 | `.mock .tbl-mini`（普通表格）｜`tr.sum`（汇总行）｜`td.ra` 或 `style="text-align:right"`（金额 / 数量右对齐）｜`<input value="...">`（从表内联编辑） | 列表列顺序按第九部分子条 2 的字段顺序写，金额右对齐 |
| 分页 | `.mock-foot` > `.pagination`（左：条数） + `.pagination`（右：上一页 / 页码 / 下一页） | 列表类与查询类界面必须有 |
| 弹窗 | `.mock-modal` > `.mock-dialog` > `.dlg-head`（`<b>标题</b>` + `<span class="x">✕</span>`） + `.dlg-body` + `.dlg-foot`（取消 + 主按钮） | 列表维护类界面的新增 / 编辑必须用弹窗示意；`.mock-dialog` 可用 `style="max-width:680px"` 收窄 |
| 提示块 | `.note.info` / `.note.warn` / `.note.ok` / `.note.err` | 用于在原型内提示关键规则（如「驳回时必须填写审核意见」） |
| 说明文字 | `<p class="fig-cap">图 9-x …</p>` | 原型下方一句话说明该界面的关键规则 |

### 16.3 四类屏幕的装配骨架

**（1）列表维护（`LIST_MAINTENANCE`）**：`.mock-head`（标题 + 新增 / 导出）+ `.toolbar`（查询条件 + 查询 / 重置）+ `.tbl-mini`（列表，行内 [编辑][停用][删除]）+ `.mock-foot`（分页）；随后另起 `.mock-modal` 呈现「新增 / 编辑弹窗」，弹窗内 `.dlg-foot` 放 [取消] + 主按钮（带审批的界面必须是 `保存草稿` + `提交` 两个主按钮）。

**（2）主从表（`MASTER_DETAIL_FORM`）**：`.mock-modal` 内 `.form-grid-3` 主表 + `.zone`「从表：明细对象名」+ `.tbl-mini`（从表，单元格内 `<input>` 内联编辑、末列 🗑）+ `tr.sum` 汇总行 + `.dlg-foot` 双按钮。

**（3）审核界面（`SINGLE_FORM`）**：`.mock-body` 内三个 `.zone`：① 单据信息（全部 `.ctl.ro` 只读）；② 从表明细（只读 `.tbl-mini`）；③ 历史审批记录（只读 `.tbl-mini`，取审批记录对象）；再加一个 `.zone` 放审核意见 `.ctl.ta`。`.mock-foot` 左侧写职责分离提示，右侧放 `✕ 驳回`（`.mbtn.d`）与 `✓ 通过`（`.mbtn.p`）。

**（4）查询列表 / 统计报表（`QUERY_LIST`）**：`.mock-head`（标题 + 视角切换 / 导出）+ `.toolbar`（多行条件）+ `.tbl-mini`（结果，统计报表用 `tr.sum` 合计行）+ `.mock-foot`（分页 + 统计口径说明）。纯查询界面不出现弹窗与操作按钮（行内「查看」除外）。

### 16.4 与子条 2 的一致性约束

1. 原型中出现的**每一个字段**都必须能在子条 2「界面元素表」中找到同名行；子条 2 有而原型未展示的字段，应在同域内补充说明「字段同上，见子条 2」；
2. 原型中的**按钮文案**必须与子条 2 按钮区一致，并标注 `FUNC-xx` / `B-APP-xx` / `Q-xx` 编号；「不占编号」的交互（添加行 / 删除行 / 取消 / 重置 / 导出 / 翻页 / 视角切换）在原型中可呈现但须在子条 2 标注为不占编号；
3. 原型中的**状态标签文案**必须取自第七部分数据字典的字典值；
4. 原型中展示的编号示例必须符合第 3.5 节统一编号规则（如 `CUS-20260915-0001`）；
5. 原型**只表达形态**，字段语义（默认值、可编辑性、必填、数据源）一律以子条 2 为唯一权威——两者冲突时以子条 2 为准并修正原型。

---

*本规范由 ai-prototype 源代码逆向整理，配合本体模型 MU 使用，用于指导 AI 生成风格一致的新系统界面。*

