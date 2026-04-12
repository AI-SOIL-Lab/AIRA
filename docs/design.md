# AIRA — AI Research Assistant

## 三层架构

```
index.md          →  标题 + 标签，链接到 digest     （最轻，全量读入）
digest/           →  摘要 + 关键发现 + 双链，链接到 raw  （中等，精筛时读）
raw/              →  完整内容                        （最重，最终推理时读）
```

筛选链路：

```
用户提问
  → 读 index.md（全量，~30KB）→ 初筛出 30-50 条
  → 读对应 digest（30-50 个小文件，共约 50-100KB）→ 精筛出 5-10 条
  → 读对应 raw（5-10 个大文件）→ 推理回答
```

---

## Vault 目录结构

```
vault/
├── index.md                    # 全局索引
├── raw/                        # 原文，只被 digest 链接
│   ├── paper_001.md
│   ├── paper_002.md
│   ├── idea_005.md
│   └── exp_003.md
└── digest/                     # 摘要，被 index 链接，链接到 raw
    ├── paper_001_digest.md
    ├── paper_002_digest.md
    ├── idea_005_digest.md
    └── exp_003_digest.md
```

命名规则：digest 加 `_digest` 后缀，Obsidian 的 `[[]]` 对纯文件名链接支持最好。

---

## Markdown 模板

### index.md

```markdown
# Index

## Papers
- [[paper_001_digest|Deep Learning for Fatigue Life Prediction]] `#Ti-alloy` `#fatigue` `#CNN` c:4
- [[paper_002_digest|Electrochemical Corrosion of Ti Alloys]] `#Ti-alloy` `#corrosion` c:4

## Ideas
- [[idea_005_digest|用GAN反向设计热处理工艺]] `#Ti-alloy` `#GAN` `#inverse-design` c:1

## Experiments
- [[exp_003_digest|热处理优化 Round 2]] `#Ti-alloy` `#heat-treatment` c:3

## Discussions
- [[disc_001_digest|热处理优化方向讨论]] `#Ti-alloy` `#optimization-strategy` c:2
```

每行：`[[digest链接|显示名]]` + `#标签` + `c:置信度`

### digest/xxx_digest.md

```markdown
---
type: paper | idea | experiment | discussion
tags: [tag1, tag2, tag3]
created: YYYY-MM-DD
source: 来源标识
confidence: 1-5
raw: "[[文件名]]"
---

# 标题

（正文即摘要，直接写核心概括。提到其他内容时用 [[]] 自然引用。）

## Key Findings
1. ...

## Relevance
...
```

正文就是摘要，不嵌套 summary callout。正文自由组织，模型根据 type 自行决定写哪些 section。

### raw/xxx.md

```markdown
---
type: paper | idea | experiment | discussion
source: 来源标识
created: YYYY-MM-DD
---

# 标题

（完整原文 / PDF 转换后的 Markdown / 用户原始笔记）
```

raw 保留原始内容，frontmatter 极简（元数据已在 digest 中）。

---

## type 取值

| type | 说明 | source 示例 |
|------|------|------------|
| `paper` | 正式论文/预印本 | `Acta Materialia 2024` / `arXiv:2401.xxxxx` |
| `idea` | 研究想法、假设、灵感 | `self` / `discussion with Prof.X` |
| `experiment` | 实验记录/数据 | `lab notebook` / `exp_2026_04_round2.xlsx` |
| `discussion` | Agent 与用户对话中产生的结论/洞见 | `aira` |

---

## confidence 取值

| 值 | 含义 | 典型信源 |
|----|------|---------|
| 5 | 顶级期刊，严格同行评审 | Nature, Science, 顶会 |
| 4 | 领域好期刊 | Acta Materialia, PRB |
| 3 | 预印本 / 会议论文 | arXiv, conference |
| 2 | 权威博客 / 教科书 | distill.pub, 教材 |
| 1 | 个人笔记 / 未验证 | self, 知乎, Reddit |

---

## Agent 框架

单 Agent + 多 Skill，意图自动路由。

### Skills

| Skill | 动作性质 | 触发频率 | 一句话描述 |
|-------|---------|---------|-----------|
| `ingest` | 写入 | 高频，按需 | 把内容变成结构化知识，接入知识库 |
| `research` | 读取+推理 | 高频，按需 | 基于知识库回答任何问题 |
| `health` | 检查+修复 | 低频，定期 | 检查知识库健康程度并修复 |

### health Skill 职责

- **自动修复：** 链接丢失、孤立文档、index 与 digest 不同步、缺失的隐性双链 → Agent 自行处理
- **提交用户决策：** 结论矛盾、质量明显差的文档 → 提示用户，由用户决定后续

---

## 业务流程

### 流程 1：丢东西（ingest）

```
用户：把这篇论文加进来 / 我有个想法记一下 / 这是今天的实验数据
  ↓
Agent：
  1. git 检查，拉取最新状态
  2. 解析用户输入的内容
  3. 写入 raw/xxx.md
  4. AI 生成 digest（标签、摘要、关键发现、与已有内容的双链）
  5. 写入 digest/xxx_digest.md
  6. 更新 index.md（追加一条）
  7. git commit
```

用户也可能直接在 Obsidian 里新建文件写东西，Agent 下次操作时通过 git diff 发现变更，补跑 ingest。

### 流程 2：问问题（research）

```
用户：XXX和YYY的关系是什么 / 基于我的数据，下一步该怎么设计实验
  ↓
Agent：
  1. git 检查，拉取最新状态
  2. 如果有 Obsidian 侧的新文件未处理 → 先补跑 ingest
  3. 读 index.md → 推理初筛
  4. 读候选 digest → 精筛
  5. 读选中 raw → 推理回答
  6. 对话中产生新洞见 → 询问用户是否记入知识库
     - 是 → 走 ingest 流程
     - 否 → 仅在对话中保留
  7. git commit（如有文件变更）
```

### 流程 3：系统自维护（health）

```
触发条件：批量导入后 / 用户主动要求 / 定期（每次对话开始时）
  ↓
Agent：
  1. git 检查
  2. 检查：链接完整性、孤立文档、index 同步、缺失的隐性双链、矛盾/质量问题
     - 可自动修复的 → 修复（补双链、修链接、清孤立）
     - 矛盾/质量问题 → 提示用户
  3. git commit
```

### Obsidian 侧编辑的同步

| 用户操作 | Agent 应对 |
|---------|-----------|
| 新建了文件 | 补跑 ingest，生成 digest + 更新 index |
| 编辑了 digest | 尊重用户修改，不覆盖。可提示"是否需要同步更新 index？" |
| 编辑了 raw | 尊重用户修改。可提示"是否需要重新生成 digest？" |
| 删除了文件 | 清理对应的 digest / index 条目 |

Agent 在每次操作前通过 git diff 检查，统一处理这些变更。

---

## Git 协作机制

用户在 Obsidian 中直接编辑文件，Agent 无法感知哪些文件被改动。通过 git 解决：

- **Agent 操作前：** `git pull` / 检查工作区状态，获取最新文件状态
- **Agent 操作后：** `git add` + `git commit`，提交变更
- **用户不介入 git** — 用户只管在 Obsidian 里编辑，git 由 Agent 全权管理

---

## 待讨论

- **PDF 导入链路** — Marker / 多模态 LLM 直读 / 其他（工程细节，后续确定）
- **实验数据接入深度** — CSV/Excel 图片各做到什么程度，MVP 边界（后续确定）
- **质量门控** — AI 打标签是否需要人工审核（后续确定）
