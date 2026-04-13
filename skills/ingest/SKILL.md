---
name: ingest
description: Unified knowledge base ingestion skill. Handles file conversion, raw file录入, digest generation, and index updates. Triggers: "add this paper", "import this PDF", "process new files", "check for new content", "run ingest".
---

# Ingest Skill

统一的知识库录入入口。根据用户意图自动判断是否需要 raw 录入，然后执行文件转换、digest 生成和 index 更新。

## ⚠️ 执行纪律

**必须使用 `todo_write` 工具将流程步骤写入 todo list，逐步标记 `in_progress` 和 `completed`。** 禁止跳步、遗漏、或凭印象执行。每完成一步立即标记完成，再开始下一步。

## 核心流程

### Step 1：意图判断

根据用户输入，判断是否需要 raw 文件录入：

| 用户意图 | 需要 raw 录入 | 后续流程 |
|---------|-------------|---------|
| "把这篇论文加进来" / "导入这个 PDF" / 指定了文件路径 | ✅ 是 | Step 1a → Step 2 → Step 3 → Step 4 |
| "处理新文件" / "检查是否有新内容" | ❌ 否 | Step 1b → Step 2 → Step 3 → Step 4 |

**如果需要 raw 录入：** 调用 ingest CLI tool：

```bash
aira-ingest ingest {文件路径或URL} -v {vault_dir}
```

如果有多个文件，使用 batch 模式：

```bash
aira-ingest batch {文件1} {文件2} {文件3} -v {vault_dir}
```

### Step 2：文件录入（raw 录入）

将用户提供的文件转换为 Markdown，写入 `vault/raw/`。

**支持的输入类型：**
| 输入类型 | 转换工具 | 自动 type | 说明 |
|---------|---------|----------|------|
| `.pdf` | mineru | `paper` | 默认 extract 模式，失败自动降级 flash-extract |
| `.docx`, `.doc` | mineru | `paper` | Word 文档 |
| `.pptx`, `.ppt` | mineru | `paper` | PowerPoint |
| URL (http/https) | mineru crawl | `paper` | 需要 Token |
| `.md`, `.txt` | 直接复制 | `paper` | 保留原文件名和资源 |

**文件名规则：**
- **文件输入**：保留原始文件名，避免破坏内部引用（如图片相对路径）
- **URL/口述内容**：使用 `{type}_{NNN}.md` 编号命名
- **冲突处理**：追加 `_1`, `_2` 等后缀

**资源文件处理：**
PDF/文档转换可能产生图片等资源文件。工具会自动复制资源目录，保持相对路径引用不变。

### Step 3：Git 检查 + 新文件发现

执行 `git diff HEAD -- vault/raw/` 对比 HEAD，找出 `vault/raw/` 中新增或变更的文件。

**注意：** 不管是否使用了 raw 录入，都必须执行此步骤，因为用户可能直接在 Obsidian 中新建了文件。

对每个新文件，从文件名和 frontmatter 中提取元数据：

| 信息 | 获取方式 |
|------|---------|
| type | 从 frontmatter 读取，或从文件名推断（`paper_*`, `idea_*`, `exp_*`, `disc_*`） |
| source | 从 frontmatter 读取 |
| created | 从 frontmatter 读取，或使用当前日期 |
| 标题 | 从 frontmatter 或文件第一个 `# 标题` 提取 |

如果文件没有 frontmatter，根据内容自动补充。

### Step 4：生成 digest

读取 `vault/index.md` 获取已有知识库全貌，用于判断双链关联。

AI 生成 digest，写入 `vault/digest/{raw_filename}_digest.md`：

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

**生成规则：**
- **标签**：从内容中提取领域标签，复用 index.md 中已有的标签以保持一致性
- **置信度**：根据 source 自动判断（顶级期刊=5，好期刊=4，预印本=3，权威博客=2，个人=1）
- **双链**：在正文中用 `[[]]` 引用相关的已有 digest，建立知识关联
- **正文即摘要**：不嵌套 summary callout，直接写核心概括

### Step 5：更新 index.md

在 `vault/index.md` 的对应 type 分类下追加一行：

```markdown
- [[{raw_filename}_digest|{显示名}]] `#tag1` `#tag2` c:{confidence}
```

### Step 6：Git 提交

```bash
git add vault/raw/ vault/digest/ vault/index.md
git commit -m "ingest: {描述}"
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

当 git diff 发现多个新文件时，逐个执行 Step 2-4，最后统一 git commit。

## 约束

- **raw 不可变** — 写入后任何流程都不修改 raw 文件
- 标签尽量复用已有标签，避免同义不同名
- index.md 的格式必须与已有条目保持一致
- 置信度取值参考 QWEN.md 中的定义

## CLI Tool 使用说明

### 安装

```bash
cd skills/ingest
source ../../.venv/bin/activate
uv pip install -e .
```

### 依赖要求

| 依赖 | 用途 | 安装方式 |
|------|------|---------|
| `mineru-open-api` | PDF/文档/URL → Markdown 转换 | CLI 工具 |

#### MinerU 安装

```bash
curl -fsSL https://cdn-mineru.openxlab.org.cn/open-api-cli/install.sh | sh
```

可选：配置 Token 以使用 extract 模式（支持表格/公式识别）：
```bash
mineru-open-api auth
```

### 使用方式

```bash
# 录入单个文件
aira-ingest ingest paper.pdf
aira-ingest ingest https://arxiv.org/abs/2401.xxxxx
aira-ingest ingest notes.md -t idea

# 批量录入
aira-ingest batch paper1.pdf paper2.pdf paper3.pdf

# 指定 vault 目录
aira-ingest ingest paper.pdf -v /path/to/vault

# 指定 MinerU 模型
aira-ingest ingest large_paper.pdf --mineru-model vlm
```
