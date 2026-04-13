---
name: research
description: Use this skill when the user asks a research question based on the AIRA knowledge base. This includes questions about literature, experiments, cross-analysis between papers and data, or seeking insights from the knowledge base. Triggers: "what's the relationship between X and Y", "based on my data", "compare these papers", "summarize my findings".
---

# Research Skill

基于 AIRA 知识库回答用户的研究问题。核心方法是**三层渐进筛选**：从轻量索引逐步深入到原文，用最小的上下文消耗找到最相关的内容。

## ⚠️ 执行纪律

**必须使用 `todo_write` 工具将流程步骤写入 todo list，逐步标记 `in_progress` 和 `completed`。** 禁止跳步、遗漏、或凭印象执行。每完成一步立即标记完成，再开始下一步。

## 前置：Git 检查 + Obsidian 同步

每次操作前，执行：
1. `git status` 检查工作区状态
2. 如果有 Obsidian 侧未处理的新文件 → 先调用 `ingest` skill 补跑入库
3. 如果有 Obsidian 侧编辑了 raw → 提示用户"原文已修改，是否需要重新生成 digest？"
4. 如果有 Obsidian 侧编辑了 digest → 尊重用户修改，不覆盖

## 核心流程：三层渐进筛选

### Step 1：读 index.md，初筛

读取 `vault/index.md`（全量，~30KB，可一次性读入）。

根据用户问题，从 index 中筛选出**可能相关**的条目（30-50 条）。筛选依据：
- 标签匹配
- 显示名/标题关键词
- type 过滤（如用户问实验相关，优先 experiment 类型）
- confidence 权重（同等相关时，高置信度优先）

**输出**：候选 digest 文件名列表。

### Step 2：读候选 digest，精筛

读取 Step 1 筛出的 digest 文件（30-50 个小文件，共约 50-100KB）。

根据用户问题，从 digest 中筛选出**高度相关**的条目（5-10 条）。筛选依据：
- Key Findings 与问题的相关性
- Relevance section 的匹配度
- digest 正文中 `[[]]` 引用的关联内容

**输出**：需要深入阅读的 raw 文件名列表。

### Step 3：读选中 raw，推理回答

读取 Step 2 筛出的 raw 文件（5-10 个大文件）。

基于 raw 原文进行深度推理，回答用户问题。回答要求：
- **引用来源**：每个关键论点标注来源，格式为 `[[xxx_digest|显示名]]`
- **区分事实与推断**：明确标注哪些是原文结论，哪些是你的推理
- **标注置信度**：对不确定的结论标注置信度

### Step 4：回答格式

```markdown
## 回答

{基于 raw 原文的深度回答，引用标注 [[xxx_digest|显示名]]}

## 引用

- [[paper_001_digest|Deep Learning for Fatigue Life Prediction]] — 支撑了 XXX 结论
- [[exp_003_digest|热处理优化 Round 2]] — 提供了 YYY 实验数据

## 进一步问题

- {基于当前回答，自然延伸的 1-2 个研究问题}
```

## 对话中产生洞见

如果在回答过程中产生了新的研究洞见（如发现了两个实验之间的矛盾、提出了新的假设），主动询问用户：

> "在分析过程中我发现 [洞见描述]，是否记入知识库？"

- **用户同意** → 调用 `ingest` skill，type 为 `discussion`，source 为 `aira`
- **用户拒绝** → 仅在当前对话中保留，不写入知识库

## 追问与迭代

用户可能基于回答继续追问。后续追问复用同一流程，但可以优化：
- 如果追问在同一主题范围内，**复用 Step 2 的精筛结果**，不需要重新从 index 开始
- 如果追问转向新主题，**重新从 Step 1 开始**
- 追问时如果需要读取更多 raw，直接补充读取

## 跨库关联

如果用户的问题涉及多个 type 的交叉分析（如"基于我的实验数据，哪些论文的结论支持/矛盾？"）：
1. 在 Step 1 中**不限定 type**，同时筛选 paper 和 experiment
2. 在 Step 3 中**显式对比**不同 type 的内容，标注一致/矛盾
3. 矛盾结论 → 在回答中标注，并在 Step 4 的"进一步问题"中建议用户决策

## 约束

- 严格遵循三层筛选顺序，不要跳层（如直接读 raw 而不经过 index/digest 筛选）
- index.md 全量读入，不做子集采样
- digest 按需读取，只读 Step 1 筛出的候选
- raw 按需读取，只读 Step 2 筛出的选中项
- 回答必须标注引用来源，不允许无来源的断言
- 不确定时明确说"基于当前知识库无法确定"，不要编造
