---
name: ingest
description: Use this skill when the user wants to add content to the AIRA knowledge base. This includes ingesting papers (PDFs), ideas, experimental data (CSV/Excel), URLs, or any research notes. Triggers: "add this paper", "import this PDF", "save this idea", "record this experiment".
---

# Ingest Skill

将用户提供的任何内容转化为结构化知识，写入 AIRA 的三层知识库（raw → digest → index）。

## ⚠️ 执行纪律

**必须使用 `todo_write` 工具将流程步骤写入 todo list，逐步标记 `in_progress` 和 `completed`。** 禁止跳步、遗漏、或凭印象执行。每完成一步立即标记完成，再开始下一步。

## 可用 Skills

你有三个外部 skill 可调用，根据输入类型自动选择：

| Skill | 用途 | 调用时机 |
|-------|------|---------|
| `mineru` | PDF/文档 → Markdown 转换（基于 MinerU API） | 用户输入为 `.pdf` 等文档文件时 |
| `firecrawl` | 网页抓取 → Markdown | 用户输入为 URL 时 |
| `xlsx` | Excel/CSV 解析 | 用户输入为 `.xlsx` / `.csv` 文件时 |

调用方式：使用对应的 skill tool（如 `skill: "mineru"`、`skill: "firecrawl"`、`skill: "xlsx"`），将原始内容转换为 Markdown 后，进入后续流程。

## 前置：Git 检查

每次操作前，执行：
1. `git status` 检查工作区状态
2. 如果有 Obsidian 侧未处理的变更（用户直接新建/编辑了文件），先处理同步（见下方"Obsidian 侧同步"）

## 核心流程

### Step 1：解析输入 + 落盘 raw（save 与 process 分离）

同时确定 type、选择转换方式、直接落盘。**不做内容中转** — skill 输出直写 `vault/raw/`，不让 AI 复述内容。

#### 文件名生成规则

**原则：保留原始文件名，避免破坏内部引用（如图片相对路径）。**

| 场景 | 文件名 | 说明 |
|------|--------|------|
| 用户直接提供了文件（PDF/文档/CSV 等） | **保留原文件名**（如 `Zhang_2024_ENSO_Transformer.md`） | 转换后直写到 `vault/raw/`，不重命名 |
| 用户提供了 URL | `{type}_{NNN}.md` | NNN 为同 type 下的递增编号 |
| 用户口述/对话产生的内容 | `{type}_{NNN}.md` | NNN 为同 type 下的递增编号 |

**判断逻辑：**
- 如果输入是一个**已有文件**（用户上传的 PDF/文档/CSV 等），保留原文件名（去掉扩展名，加 `.md`）
- 如果输入是 **URL 或口述内容**（没有原始文件名），使用 `{type}_{NNN}.md` 编号命名
- 文件名冲突时，在文件名后追加 `_1`, `_2` 等后缀避免覆盖

**注意：** 保留原文件名很重要，因为 Markdown 中的图片等资源可能使用相对路径（如 `images/xxx.jpg`），重命名文件会导致链接失效。

| 输入形式 | type | 转换 + 落盘 |
|---------|------|------------|
| 论文 PDF | `paper` | `mineru` skill → Markdown，保留原文件名，`write_file` 直写到 `vault/raw/` |
| 论文 URL | `paper` | `firecrawl` skill → Markdown，写入 `{type}_{NNN}.md` |
| 用户口述的想法 | `idea` | 直接 `write_file` 落盘，写入 `{type}_{NNN}.md`，source 为 `self` |
| 实验数据（CSV/Excel） | `experiment` | `xlsx` skill → Markdown，保留原文件名，`write_file` 直写到 `vault/raw/` |
| 对话中产生的洞见 | `discussion` | 直接 `write_file` 落盘，写入 `{type}_{NNN}.md`，source 为 `aira` |

如果用户没有明确指定 type，根据内容自动判断。

落盘后追加 frontmatter（如果文件没有的话）：

```markdown
---
type: {type}
source: {来源标识}
created: {YYYY-MM-DD}
---

# {标题}

{完整原文}
```

**写入后校验**：保存 raw 后检查文件大小和行数，如果明显小于预期（如 PDF 原文 20 页但 raw 只有 50 行），告警并重试。

raw 是不可变归档，写入后不再修改。

### Step 2：生成 digest

读取 `vault/index.md` 获取已有知识库的全貌，用于判断双链关联。

AI 生成 digest，写入 `vault/digest/{raw_filename}_digest.md`（其中 `{raw_filename}` 是 raw 文件的实际文件名，不含 `.md` 扩展名）：

```markdown
---
type: {type}
tags: [{tag1}, {tag2}, {tag3}]
created: {YYYY-MM-DD}
source: {来源标识}
confidence: {1-5}
raw: "[[{raw_filename}]]"
---

# {标题}

{正文：核心概括，提到已有内容时用 [[]] 自然引用}

## Key Findings
1. ...

## Relevance
...
```

生成规则：
- **标签**：从内容中提取领域标签，复用 index.md 中已有的标签以保持一致性
- **置信度**：根据 source 自动判断（顶级期刊=5，好期刊=4，预印本=3，权威博客=2，个人=1）
- **双链**：在正文中用 `[[]]` 引用相关的已有 digest，建立知识关联
- **正文即摘要**：不嵌套 summary callout，直接写核心概括
- **section 自由组织**：模型根据 type 自行决定写哪些 section，但必须包含 Key Findings 和 Relevance

### Step 3：更新 index.md

在 `vault/index.md` 的对应 type 分类下追加一行：

```markdown
- [[{raw_filename}_digest|{显示名}]] `#tag1` `#tag2` c:{confidence}
```

其中 `{raw_filename}` 是 raw 文件的实际文件名（不含 `.md` 扩展名）。如果该 type 的分类标题不存在，则新建。

### Step 4：Git 提交

```
git add vault/raw/{raw_filename}.md vault/digest/{raw_filename}_digest.md vault/index.md
git commit -m "ingest: {raw_filename} {标题}"
```

## Obsidian 侧同步

用户可能直接在 Obsidian 中新建文件，通过 git diff 发现后：

| 用户操作 | 处理 |
|---------|------|
| 新建了文件 | 补跑 ingest：生成 digest + 更新 index |
| 编辑了 digest | 尊重用户修改，不覆盖。提示"是否需要同步更新 index？" |
| 编辑了 raw | 尊重用户修改。提示"是否需要重新生成 digest？" |
| 删除了文件 | 清理对应的 digest / index 条目 |

## 批量导入

用户一次提供多篇内容时，逐篇执行 Step 1-3，最后统一 git commit。批量导入完成后，提示用户可以运行 health 检查。

## 约束

- raw 写入后不可变，任何后续修改只改 digest
- 文件名中的编号 NNN 必须不与已有文件冲突
- index.md 的格式必须与已有条目保持一致
- 标签尽量复用已有标签，避免同义不同名（如 `#fatigue` vs `#fatigue-life`）
