# AIRA — AI Research Assistant

AIRA 是一个 AI 研究助手，作为 Obsidian + Qwen Code 的整合系统，充当主动式研究 copilot，结合文献和私人实验数据进行交叉分析。

**核心理念：** Full-Context-First（全文优先）+ AI 负责所有索引/标记/整理，人类只管往里丢知识。

## 架构

三层渐进筛选架构：

```
index.md          →  标题 + 标签，链接到 digest     （最轻，全量读入）
digest/           →  摘要 + 关键发现 + 双链，链接到 raw  （中等，精筛时读）
raw/              →  完整内容                        （最重，最终推理时读）
```

用户提问时，从 index 初筛 → digest 精筛 → raw 深度推理，用最小上下文消耗找到最相关的内容。

## 快速开始

### 前置要求

- [Qwen Code](https://github.com/QwenLM/qwen-code)（作为 AI Agent 运行时）
- [Obsidian](https://obsidian.md/)（作为前端，零开发成本使用 `[[wikilink]]` 图谱可视化）
- [Git](https://git-scm.com/)（协作同步机制，用户无需手动操作）
- [uv](https://github.com/astral-sh/uv)（Python 包管理器，用于管理项目虚拟环境）

### Python 环境管理

本项目使用 `uv` 管理 Python 虚拟环境和依赖，**不要直接使用系统全局 Python**。

```bash
# 创建虚拟环境
uv venv

# 激活环境
source .venv/bin/activate
```

### 安装

在目标项目根目录下执行：

```bash
# 克隆 AIRA 到 .qwen 目录
mkdir -p .qwen && cd .qwen
git clone https://github.com/AI-SOIL-Lab/AIRA .
cd ..

# 复制 QWEN.md 到项目根目录
cp .qwen/QWEN.md ./
```

### 安装外部 Skill

AIRA 的外部 skill 已内置于 `skills/` 目录，**无需额外安装**。但以下 skill 依赖的 Python 包需要在 uv 虚拟环境中安装：

```bash
# 激活虚拟环境
source .venv/bin/activate
```

**Skill Python 依赖：**

| Skill | Python 依赖 | 说明 |
|-------|------------|------|
| `xlsx` | `pandas`, `openpyxl` | Excel/CSV 读写、公式重算 |
| `firecrawl` | 无（CLI 工具） | 需要 `FIRECRAWL_API_KEY` 环境变量 |

**安装依赖：**

```bash
# xlsx skill 依赖
uv pip install pandas openpyxl

# firecrawl CLI（非 Python 包）
# 需配置 FIRECRAWL_API_KEY 环境变量
```

> **LibreOffice 依赖：** `xlsx` skill 的公式重算功能依赖 LibreOffice，需确保系统已安装。

### MinerU CLI 安装（可选）

MinerU CLI 用于 PDF/文档 → Markdown 转换（非 Python 包，独立安装）：

```bash
curl -fsSL https://cdn-mineru.openxlab.org.cn/open-api-cli/install.sh | sh
```

### MinerU 配置（可选）

MinerU 支持两种模式，未配置 Token 时默认使用 `flash-extract`（免登录但有限制）：

| 模式 | 适用场景 | Token 要求 | 限制 |
|------|---------|-----------|------|
| `flash-extract` | 快速提取小文件 | 不需要 | ≤10MB, ≤20页，仅 Markdown |
| `extract` | 精准提取/大文件 | 需要 | 更高配额，支持表格/公式/多格式 |

**Token 配置方式：**

```bash
# 1. 申请 Token：https://mineru.net/apiManage/token
# 2. 通过 CLI 配置
mineru-open-api auth  # 交互式设置
```

> **提示：** Token 解析优先级：`--token` 参数 > `MINERU_TOKEN` 环境变量 > `~/.mineru/config.yaml`

### 初始化知识库

在 `vault/` 目录下创建以下初始结构：

```
vault/
├── index.md
├── raw/
└── digest/
```

然后在 Obsidian 中打开 `vault/` 文件夹即可。

## 使用方式

### 添加内容（ingest）

在 Qwen Code 对话中说：
- "把这篇论文加进来"
- "我有个想法"
- "这是今天的实验数据"

AI 会自动解析内容 → 写入 raw → 生成 digest → 更新 index → git commit。

### 提问分析（research）

在 Qwen Code 对话中提问：
- "X 和 Y 的关系是什么？"
- "基于我的数据，下一步该怎么设计实验？"
- "对比这两篇论文的结论"

AI 会三层筛选（index → digest → raw），引用来源回答问题。

### 检查知识库（health）

在 Qwen Code 对话中说：
- "检查一下知识库健康度"
- "修复断链"
- "找孤立文档"

AI 会检查：链接完整性、孤立文档、index 同步、隐性双链、矛盾/质量问题。

## 项目结构

```
AIRA/
├── README.md
├── docs/
│   └── design.md          # 设计文档，已确认的设计决策
├── vault/
│   ├── index.md           # 全局索引
│   ├── raw/               # 原文归档
│   └── digest/            # 摘要
└── .qwen/
    ├── rules/
    │   └── aira-orchestration.md   # 全局编排规则（每次对话自动注入）
    └── skills/
        ├── ingest/SKILL.md         # 内容入库 skill
        ├── research/SKILL.md       # 知识库问答 skill
        └── health/SKILL.md         # 知识库健康检查 skill
```

## Git 协作机制

用户在 Obsidian 中直接编辑文件，AI 通过 git 感知变更：

- **AI 操作前：** `git status` 检查状态，处理 Obsidian 侧的未同步变更
- **AI 操作后：** `git add` + `git commit` 提交变更
- **用户不介入 git** — 用户只管在 Obsidian 里编辑

## 设计决策

详细设计文档见 [docs/design.md](docs/design.md)，包含：
- 三层架构设计原理
- Vault 目录结构
- Markdown 模板格式
- type / confidence 取值定义
- 业务流程

## 许可证

本项目为个人研究项目。
