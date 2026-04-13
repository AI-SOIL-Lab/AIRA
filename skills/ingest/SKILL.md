---
name: ingest
description: Use this skill when new files appear in vault/raw/ (via git diff or Obsidian sync) and need to be processed into the knowledge base. Triggers: "process new files", "check for new content", "run ingest on vault", or automatically when git diff shows new raw files.
---

# Ingest Skill

扫描 `vault/raw/` 中的新文件（通过 git diff 发现），生成 digest 并更新 index.md。

**职责边界：** ingest **不负责**文件转换或录入。它只处理已存在于 `vault/raw/` 中的新文件，将其转化为结构化知识（digest + index 条目）。文件录入请使用 `ingest-raw` skill。

## ⚠️ 执行纪律

**必须使用 `todo_write` 工具将流程步骤写入 todo list，逐步标记 `in_progress` 和 `completed`。** 禁止跳步、遗漏、或凭印象执行。每完成一步立即标记完成，再开始下一步。

## 前置：Git 检查 + 新文件发现

每次操作前，执行：
1. `git status` 检查工作区状态
2. `git diff HEAD -- vault/raw/` 对比 HEAD，找出 `vault/raw/` 中新增或变更的文件
3. 如果有 Obsidian 侧未处理的变更（用户直接新建/编辑了文件），先处理同步（见下方"Obsidian 侧同步"）

## 核心流程

### Step 1：识别新文件类型

对每个新文件，从文件名和 frontmatter 中提取元数据：

| 信息 | 获取方式 |
|------|---------|
| type | 从 frontmatter 读取，或从文件名推断（`paper_*`, `idea_*`, `exp_*`, `disc_*`） |
| source | 从 frontmatter 读取 |
| created | 从 frontmatter 读取，或使用当前日期 |
| 标题 | 从 frontmatter 或文件第一个 `# 标题` 提取 |

如果文件没有 frontmatter，根据内容自动补充：

```markdown
---
type: {type}
source: {来源标识}
created: {YYYY-MM-DD}
---
```

### Step 2：生成 digest

读取 `vault/index.md` 获取已有知识库的全貌，用于判断双链关联。

AI 生成 digest，写入 `vault/digest/{raw_filename}_digest.md`（其中 `{raw_filename}` 是 raw 文件的实际文件名，不含扩展名）：

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

{正文：核心概括，提到已有内容时使用 [[]] 自然引用}

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

其中 `{raw_filename}` 是 raw 文件的实际文件名（不含扩展名）。如果该 type 的分类标题不存在，则新建。

### Step 4：Git 提交

```
git add vault/raw/{raw_filename} vault/digest/{raw_filename}_digest.md vault/index.md
git commit -m "ingest: {raw_filename} {标题}"
```

## Obsidian 侧同步

用户可能直接在 Obsidian 中新建文件，通过 git diff 发现后：

| 用户操作 | 处理 |
|---------|------|
| 在 raw/ 新建了文件 | 补跑 ingest：生成 digest + 更新 index |
| 编辑了 digest | 尊重用户修改，不覆盖。提示"是否需要同步更新 index？" |
| 编辑了 raw | 尊重用户修改。提示"是否需要重新生成 digest？" |
| 删除了文件 | 清理对应的 digest / index 条目 |

## 批量处理

当 git diff 发现多个新文件时，逐个执行 Step 1-3，最后统一 git commit。批量处理完成后，提示用户可以运行 health 检查。

## 约束

- raw 文件在 ingest 流程中**只读不写**，不可修改
- 标签尽量复用已有标签，避免同义不同名（如 `#fatigue` vs `#fatigue-life`）
- index.md 的格式必须与已有条目保持一致
- 置信度取值参考 QWEN.md 中的定义
