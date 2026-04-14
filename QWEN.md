# AIRA — AI Research Assistant

## 项目概述

AIRA 是一个 AI 研究助手，作为 **Obsidian + Qwen Code** 的整合系统，充当主动式研究 copilot，结合文献和私人实验数据进行交叉分析。

**核心理念：** Full-Context-First（全文优先）+ AI 负责所有索引/标记/整理，人类只管往里丢知识。

### 三层渐进筛选架构

```
index.md          →  标题 + 标签，链接到 digest     （最轻，全量读入）
digest/           →  摘要 + 关键发现 + 双链，链接到 raw  （中等，精筛时读）
raw/              →  完整内容                        （最重，最终推理时读）
```

用户提问时，从 index 初筛 → digest 精筛 → raw 深度推理，用最小上下文消耗找到最相关的内容。

## 项目结构

```
AIRA/
├── README.md                      # 项目说明
├── docs/
│   └── design.md                  # 详细设计文档
├── vault/                         # 知识库根目录（Obsidian 打开此目录）
│   ├── index.md                   # 全局索引
│   ├── raw/                       # 原文归档（不可变）
│   └── digest/                    # 摘要（可写）
└── .qwen/
    ├── rules/
    │   └── aira-orchestration.md  # 全局编排规则（每次对话自动注入）
    └── skills/
        ├── ingest/SKILL.md        # 内容入库 skill
        ├── aminer-*/SKILL.md      # 学术搜索 skill
        ├── research/SKILL.md      # 知识库问答 skill
        └── health/SKILL.md        # 知识库健康检查 skill
```

## 核心 Skills

### 1. Ingest（知识库录入 — 统一入口）

**触发：** "把这篇论文加进来"、"处理新文件"、"检查是否有新内容"、"运行 ingest"

**实现方式：** `ingest` 是一个 skill（位于 `skills/ingest/`），统一处理所有知识库录入场景。内部包含 CLI tool（`aira-ingest`）用于确定性的文件转换录入。

**使用方式：** 用户只需告诉 AI 要录入或处理文件，AI 自动判断流程：

| 用户意图 | AI 处理流程 |
|---------|-----------|
| "把这篇论文加进来"（指定了文件/URL） | 文件转换录入 → git diff 发现新文件 → 生成 digest → 更新 index |
| "处理新文件"（没有指定文件） | git diff 发现新文件（含用户手动录入的） → 生成 digest → 更新 index |

**流程：**
1. 判断是否需要 raw 录入（用户指定了文件/URL → 是）
2. 如果需要：调用 `aira-ingest` CLI tool 录入 raw 文件
3. `git diff HEAD -- vault/raw/` 发现所有新文件（含用户手动录入的）
4. 对每个新文件：生成 digest → 写入 `vault/digest/` → 更新 `vault/index.md`
5. Git commit

**支持的输入类型：**
| 输入 | 转换工具 | 说明 |
|------|---------|------|
| PDF/DOCX/PPTX | `mineru` | 默认 extract 模式，失败自动降级 flash-extract |
| URL | `mineru crawl` | 需要 Token |
| MD/TXT | 直接复制 | 保留原文件名 |

### 2. Ingest（知识库接入）

**触发：** "处理新文件"、"检查是否有新内容"、"运行 ingest"

**流程：**
1. Git 检查，`git diff` 扫描 `vault/raw/` 中的新文件
2. 对每个新文件：AI 生成 digest → 写入 `vault/digest/{filename}_digest.md`
3. 更新 `vault/index.md`
4. Git commit

### 3. Research（知识库问答）

**触发：** "X 和 Y 的关系"、"基于我的数据"、"对比这两篇论文"

**流程（三层渐进筛选）：**
1. Git 检查 + Obsidian 同步
2. 如果有 raw/ 中的新文件未处理 → 先补跑 ingest
3. 读 `index.md` → 初筛（30-50 条）
4. 读候选 digest → 精筛（5-10 条）
5. 读选中 raw → 推理回答
6. 对话中产生新洞见 → 询问用户是否记入知识库
7. Git commit（如有文件变更）

### 4. Health（知识库健康检查）

**触发：** "检查健康度"、"修复断链"、"找孤立文档"

**检查项：**
1. 链接完整性（断链检测）
2. 孤立文档（未被引用的文件）
3. index 与 digest 同步（标签/置信度/显示名一致性）
4. 缺失的隐性双链（语义关联但未建立链接）
5. 矛盾检测（不同文档结论冲突）
6. 质量检测（内容过短、缺少 Key Findings 等）

**修复策略：** 能自动修复的直接处理，需要用户判断的提交给用户。

### 5. AMiner（学术搜索）

**触发：** 学术相关查询，如"查某位学者"、"找某篇论文"、"Transformer 最新进展"、"查某个机构/期刊"

**实现方式：** `aminer-open-skill` 提供 AMiner 开放平台的学术数据查询能力，包含两个 skill：

| Skill | 定位 | 说明 |
|-------|------|------|
| `aminer-free-search` | 轻量初筛 | 免费接口，适合论文/学者/机构/期刊的发现与初筛、实体标准化 |
| `aminer-data-search` | 深度分析 | 全量版，覆盖 27 个接口和 6 个分析工作流（scholar_profile、paper_deep_dive 等） |
| `aminer-daily-paper` | 论文跟踪 | 适合追踪最新的研究进展 |

**典型使用场景：**
- 查学者：简介、研究方向、论文、专利、项目
- 查论文：详情、引用关系、关键词扩展
- 查机构/期刊：学者规模、论文产出、专利分布
- 自然语言问答：如"Transformer 最新进展"
- 专利查询：技术方向专利、学者/机构专利关系

**路由策略：** 学术查询优先路由到 AMiner skill。先用 `aminer-free-search` 轻量初筛，需要深度分析时再升级到 `aminer-data-search`。追踪最新研究进展时使用 `aminer-daily-paper`。

**Token 配置：** 需要在 AMiner 控制台生成 Token：https://open.aminer.cn/open/board?tab=control

## 文件操作约束

- **raw 不可变** — 写入后任何 skill 都不修改 raw 文件
- **digest 可写** — ingest 生成、health 修复、用户编辑均可
- **index.md 可写** — ingest 追加条目、health 修复同步
- **写入后校验** — 保存文件后检查大小/行数，异常时告警重试
- **所有知识库文件必须在 `vault/` 目录下**

## Git 协作协议

用户在 Obsidian 中直接编辑文件，AI 通过 git 感知变更：

- **操作前：** `git status` 检查状态，处理 Obsidian 侧的未同步变更
- **操作后：** `git add` + `git commit -m "<skill>: <描述>"`
- **用户不介入 git** — 用户只管在 Obsidian 里编辑

### Obsidian 侧编辑的同步

| 用户操作 | Agent 应对 |
|---------|-----------|
| 新建了文件 | 补跑 ingest，生成 digest + 更新 index |
| 编辑了 digest | 尊重用户修改，不覆盖。可提示"是否需要同步更新 index？" |
| 编辑了 raw | 尊重用户修改。可提示"是否需要重新生成 digest？" |
| 删除了文件 | 清理对应的 digest / index 条目 |

## 内容类型（type）

| type | 说明 | source 示例 |
|------|------|------------|
| `paper` | 正式论文/预印本 | `Acta Materialia 2024` / `arXiv:2401.xxxxx` |
| `idea` | 研究想法、假设、灵感 | `self` / `discussion with Prof.X` |
| `experiment` | 实验记录/数据 | `lab notebook` / `exp_2026_04_round2.xlsx` |
| `discussion` | Agent 与用户对话中产生的结论/洞见 | `aira` |

## 置信度（confidence）取值

| 值 | 含义 | 典型信源 |
|----|------|---------|
| 5 | 顶级期刊，严格同行评审 | Nature, Science, 顶会 |
| 4 | 领域好期刊 | Acta Materialia, PRB |
| 3 | 预印本 / 会议论文 | arXiv, conference |
| 2 | 权威博客 / 教科书 | distill.pub, 教材 |
| 1 | 个人笔记 / 未验证 | self, 知乎, Reddit |

## 构建与运行

本项目无需构建步骤。使用方式：

1. 在 Obsidian 中打开 `vault/` 目录
2. 通过 Qwen Code 对话进行内容添加和查询
3. 外部 skill 已内置于 `skills/` 目录，无需额外安装。但需在 uv 虚拟环境中安装 Python 依赖：

```bash
source .venv/bin/activate

# xlsx skill（Excel/CSV 处理）
uv pip install pandas openpyxl

# MinerU CLI（PDF/文档转换，非 Python 包）
curl -fsSL https://cdn-mineru.openxlab.org.cn/open-api-cli/install.sh | sh
```

| Skill | Python 依赖 | 说明 |
|-------|------------|------|
| `mineru` | 无（CLI 工具） | 需配置 Token 以使用 extract 模式 |
| `xlsx` | `pandas`, `openpyxl` | Excel/CSV 读写 |
| `firecrawl` | 无（CLI 工具） | 需 `FIRECRAWL_API_KEY` 环境变量 |

> **注意：** `xlsx` skill 的公式重算功能依赖 LibreOffice。

## Python 环境管理

本项目使用 `uv` 管理 Python 虚拟环境和依赖，**不要直接使用系统全局 Python**。

```bash
# 创建虚拟环境
uv venv

# 激活环境
source .venv/bin/activate

# 安装依赖（如有 requirements.txt）
uv pip install -r requirements.txt
```

## 开发约定

- **Skill 执行纪律：** 所有 skill 必须使用 `todo_write` 工具将流程步骤写入 todo list，逐步标记 `in_progress` 和 `completed`，禁止跳步
- **标签一致性：** 复用已有标签，避免同义不同名（如 `#fatigue` vs `#fatigue-life`）
- **编号规则：** 文件名中的编号 NNN 必须不与已有文件冲突
- **幂等性：** 修复操作要幂等（重复执行不产生副作用）
- **引用标注：** research 回答中每个关键论点必须标注来源，格式为 `[[xxx_digest|显示名]]`

## 前置要求

- [Qwen Code](https://github.com/QwenLM/qwen-code)（作为 AI Agent 运行时）
- [Obsidian](https://obsidian.md/)（作为前端，零开发成本使用 `[[wikilink]]` 图谱可视化）
- [Git](https://git-scm.com/)（协作同步机制，用户无需手动操作）
- [uv](https://github.com/astral-sh/uv)（Python 包管理器，用于管理项目虚拟环境）

## MinerU 配置（可选）

MinerU 用于 PDF/文档 → Markdown 转换，支持两种模式：

| 模式 | 适用场景 | Token 要求 | 限制 |
|------|---------|-----------|------|
| `flash-extract` | 快速提取小文件 | 不需要 | ≤10MB, ≤20页，仅 Markdown |
| `extract` | 精准提取/大文件 | 需要 | 更高配额，支持表格/公式/多格式 |

### Token 配置方式

1. **申请 Token：** 前往 https://mineru.net/apiManage/token 创建 API Token

2. **通过 CLI 配置：**

```bash
mineru-open-api auth  # 交互式设置
```

**Token 解析优先级：** `--token` 参数 > `MINERU_TOKEN` 环境变量 > `~/.mineru/config.yaml`

> **提示：** 未配置 Token 时，系统自动使用 `flash-extract` 模式（免登录但有限制）。如需表格识别、公式识别或处理大文件，请配置 Token 使用 `extract` 模式。
