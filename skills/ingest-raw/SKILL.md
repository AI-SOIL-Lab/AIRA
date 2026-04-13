---
name: ingest-raw
description: Use this skill when the user wants to add raw files to vault/raw/. This includes PDFs, documents, URLs, CSV/Excel files, or any content that needs to be converted to Markdown and saved. Triggers: "add this paper", "import this PDF", "save this URL", "add this experiment data".
---

# Ingest-Raw Skill

将用户提供的各种文件类型转换为 Markdown，写入 `vault/raw/` 目录。**不负责**生成 digest 或更新 index，这些由 `ingest` skill 后续处理。

## ⚠️ 执行纪律

**必须使用 `todo_write` 工具将流程步骤写入 todo list，逐步标记 `in_progress` 和 `completed`。** 禁止跳步、遗漏、或凭印象执行。每完成一步立即标记完成，再开始下一步。

## 可用外部 Skills

你有三个外部 skill 可调用，根据输入类型自动选择：

| Skill | 用途 | 调用时机 |
|-------|------|---------|
| `mineru` | PDF/文档 → Markdown 转换（基于 MinerU API） | 用户输入为 `.pdf` / `.docx` 等文档文件时 |
| `firecrawl` | 网页抓取 → Markdown | 用户输入为 URL 时 |
| `xlsx` | Excel/CSV 解析 | 用户输入为 `.xlsx` / `.csv` 文件时 |

调用方式：使用对应的 skill tool（如 `skill: "mineru"`、`skill: "firecrawl"`、`skill: "xlsx"`），将原始内容转换为 Markdown 后，进入后续流程。

## 前置：Git 检查

每次操作前，执行：
1. `git status` 检查工作区状态
2. 如果有 Obsidian 侧未处理的变更，先处理同步

## 核心流程

### Step 1：解析输入 + 确定 type + 选择转换方式

根据输入形式确定 type 和转换方式：

| 输入形式 | type | 转换方式 |
|---------|------|---------|
| 论文 PDF / 文档（.pdf, .docx 等） | `paper` | `mineru` skill → Markdown |
| 论文 URL | `paper` | `firecrawl` skill → Markdown |
| 用户口述的想法 | `idea` | 直接整理为 Markdown 文本 |
| 实验数据（CSV/Excel） | `experiment` | `xlsx` skill → Markdown |
| 对话中产生的洞见 | `discussion` | 直接整理为 Markdown 文本 |

如果用户没有明确指定 type，根据内容自动判断。

### Step 2：执行转换 / 复制

根据输入类型，选择转换或直接复制：

| 输入类型 | 处理方式 | 说明 |
|---------|---------|------|
| 已是完整 Markdown 文件（`.md`） | **直接 `cp` 复制** | 用 `cp -r` 将文件及其资源目录整体复制到 `vault/raw/` |
| PDF/文档（`.pdf`, `.docx` 等） | `mineru` skill → Markdown | 调用 mineru 转换 |
| URL | `firecrawl` skill → Markdown | 调用 firecrawl 抓取 |
| Excel/CSV（`.xlsx`, `.csv`） | `xlsx` skill → Markdown | 调用 xlsx 解析 |
| 用户口述/对话内容 | 直接整理为 Markdown 文本 | 由 Agent 整理写入 |

#### 直接复制模式（`.md` 文件）

当用户提供的是已经是 Markdown 格式的文件时，**直接用 `cp` 命令复制，不要读取内容后再写入**：

```bash
cp -r {源文件路径} vault/raw/
# 如果有配套资源目录，也一并复制
cp -r {源资源目录路径} vault/raw/
```

**注意：**
- 使用 `cp -r` 保留目录结构和所有文件
- 复制后检查文件名是否冲突，冲突时追加 `_1`, `_2` 等后缀
- **禁止**读取 `.md` 文件内容后由 Agent 重新写入，这会丢失格式、破坏相对路径引用
- 复制后添加 frontmatter（如原文件没有）：使用 `sed` 或类似工具在文件头部插入

```markdown
---
type: {type}
source: {来源标识}
created: {YYYY-MM-DD}
---

```

### Step 3：生成文件名 + 落盘 raw

#### 文件名生成规则

**原则：保留原始文件名，避免破坏内部引用（如图片相对路径）。**

| 场景 | 文件名 | 说明 |
|------|--------|------|
| 用户直接提供了文件（PDF/文档/CSV/Markdown 等） | **保留原文件名** | 转换/复制后直写到 `vault/raw/` |
| 用户提供了 URL | `{type}_{NNN}.md` | NNN 为同 type 下的递增编号 |
| 用户口述/对话产生的内容 | `{type}_{NNN}.md` | NNN 为同 type 下的递增编号 |

**判断逻辑：**
- 如果输入是一个**已有文件**（用户上传的文件），保留原文件名
- 如果输入是 **URL 或口述内容**（没有原始文件名），使用 `{type}_{NNN}.md` 编号命名
- 文件名冲突时，在文件名后追加 `_1`, `_2` 等后缀避免覆盖

**注意：** 保留原文件名很重要，因为 Markdown 中的图片等资源可能使用相对路径（如 `images/xxx.jpg`），重命名文件会导致链接失效。

#### 处理文件资源（图片等）

PDF/文档通过 `mineru` 转换后，Markdown 中的图片可能使用相对路径（如 `images/xxx.jpg`、`figures/fig1.png`）。**必须确保这些资源文件一起被复制，并保持相对路径不变。**

**处理规则：**

1. **检查转换输出**：`mineru` 等工具可能返回一个目录（含 `.md` 文件 + 资源文件夹），而非单一文件
2. **复制资源文件**：将图片等资源文件夹整体复制到 `vault/raw/` 下，与 `.md` 文件同级
3. **保持相对路径**：复制时**不修改** Markdown 中的图片路径，确保 `![img](images/xxx.jpg)` 仍能正确引用
4. **资源文件夹命名**：如果转换工具输出的资源文件夹名与 Markdown 文件名不一致，**以转换工具输出的原名为准**，不要重命名

示例结构：
```
vault/raw/
├── Zhang_2024_Fatigue.md          # 转换后的 Markdown
└── Zhang_2024_Fatigue/            # 同名资源文件夹（或转换工具输出的原名）
    ├── images/
    │   ├── fig1.png
    │   └── fig2.jpg
    └── tables/
        └── table1.csv
```

**注意：** 如果资源文件较多或较大，在 git commit 时一并加入（`git add vault/raw/{filename}.md vault/raw/{资源文件夹}/`）。

#### 写入后校验

保存 raw 后检查文件大小和行数，如果明显小于预期（如 PDF 原文 20 页但 raw 只有 50 行），告警并重试。同时检查 Markdown 中引用的图片文件是否都已存在。

### Step 4：Git 提交

```
git add vault/raw/{filename}.md vault/raw/{资源文件夹}/
git commit -m "ingest-raw: {filename} ({type})"
```

**注意：** 如果有图片等资源文件，必须一并加入 git commit。

**提交后提示：** raw 文件已录入，提示用户"raw 文件已保存，运行 ingest 生成 digest 并更新 index"。

## 批量导入

用户一次提供多篇内容时，逐篇执行 Step 1-3，最后统一 git commit。批量导入完成后，提示用户运行 ingest skill 处理新文件。

## 约束

- raw 写入后**不可变**，任何后续修改只改 digest
- 文件名中的编号 NNN 必须不与已有文件冲突
- 所有 raw 文件必须在 `vault/raw/` 目录下
- 本 skill **只负责录入**，不生成 digest 或更新 index
- PDF/文档转换产生的图片等资源文件**必须与 .md 文件一起录入**，保持相对路径不变
- 录入后校验 Markdown 中引用的图片文件是否都存在
