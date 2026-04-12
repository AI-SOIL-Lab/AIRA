---
name: health
description: Use this skill when checking or maintaining the AIRA knowledge base health. This includes checking for broken links, orphaned documents, missing backlinks, contradictions, or quality issues. Triggers: "check health", "fix broken links", "find orphans", "review knowledge base quality".
---

# Health Skill

检查 AIRA 知识库的健康程度，并修复发现的问题。能自动修复的直接处理，需要用户判断的提交给用户。

## ⚠️ 执行纪律

**必须使用 `todo_write` 工具将流程步骤写入 todo list，逐步标记 `in_progress` 和 `completed`。** 禁止跳步、遗漏、或凭印象执行。每完成一步立即标记完成，再开始下一步。

## 前置：Git 检查

每次操作前，执行：
1. `git status` 检查工作区状态
2. 如果有 Obsidian 侧未处理的新文件 → 先调用 `ingest` skill 补跑入库

## 检查项

### 1. 链接完整性

**检查**：所有 `[[]]` 链接是否指向实际存在的文件。

| 位置 | 检查内容 |
|------|---------|
| index.md | 每个 `[[xxx_digest|...]]` 中的 `xxx_digest.md` 是否存在于 `vault/digest/` |
| digest | 每个 `[[xxx]]` 引用是否指向实际文件（可以是 digest 或 raw） |

**修复**：
- 链接目标文件不存在 → 搜索是否有重命名/移动后的对应文件
  - 找到 → 更新链接指向
  - 找不到 → 标记为**断链**，列入报告

### 2. 孤立文档

**检查**：是否存在没有被任何 `[[]]` 链接引用的文件。

| 位置 | 检查内容 |
|------|---------|
| digest/ | 是否被 index.md 引用 |
| raw/ | 是否被对应 digest 的 `raw:` frontmatter 引用 |

**修复**：
- digest 未被 index 引用 → 追加到 index.md 对应 type 分类下
- raw 未被 digest 引用 → 该 raw 可能缺少 digest，调用 `ingest` 补生成

### 3. index 与 digest 同步

**检查**：index.md 中的条目信息是否与对应 digest 的 frontmatter 一致。

| 检查内容 | 一致性要求 |
|---------|-----------|
| 标签 | index 中的 `#tag` 与 digest frontmatter 的 `tags` 一致 |
| confidence | index 中的 `c:N` 与 digest frontmatter 的 `confidence` 一致 |
| 显示名 | index 中的 `[[xxx_digest|显示名]]` 与 digest 的 `# 标题` 一致 |

**修复**：以 digest 为准，更新 index.md 中不一致的条目。

### 4. 缺失的隐性双链

**检查**：digest 之间是否存在内容相关但未建立 `[[]]` 引用的情况。

方法：
1. 读取 `vault/index.md` 获取全貌
2. 对每个 digest，检查其内容是否与其他 digest 存在语义关联但未引用
3. 关联判断依据：
   - 共享标签较多（3 个以上相同标签）
   - 内容中提到对方的关键概念/方法/材料
   - Key Findings 或 Relevance 中隐含关联

**修复**：在相关 digest 的正文中补充 `[[]]` 引用。修改 digest 后同步检查 index 标签是否需要更新。

### 5. 矛盾检测

**检查**：不同 digest 之间是否存在结论矛盾。

方法：
1. 对共享相同标签的 digest 进行交叉比对
2. 重点关注 Key Findings 中的结论性陈述
3. 检测模式：
   - 同一现象，不同结论（如 A 说"X 提升性能"，B 说"X 降低性能"）
   - 同一方法，不同适用条件（如 A 说"方法 M 适用于条件 C1"，B 说"方法 M 在条件 C1 下失效"）

**处理**：矛盾**不自动修复**，提交给用户决策：
- 列出矛盾双方及来源
- 提示用户判断：哪个更可信？是否需要标注条件差异？是否需要更新 confidence？

### 6. 质量检测

**检查**：是否存在质量明显差的文档。

| 问题 | 检测标准 |
|------|---------|
| digest 内容过短 | 正文少于 5 行（可能是生成失败） |
| digest 无 Key Findings | 缺少 Key Findings section |
| raw 为空 | 文件只有 frontmatter，无正文 |
| 标签缺失 | digest 无标签或标签过于笼统（如只有一个 `#research`） |
| confidence 异常 | confidence 与 source 不匹配（如 arXiv 论文标为 c:5） |

**处理**：
- 可自动修复的（如 confidence 与 source 不匹配）→ 直接修正
- 需要重新生成的（如 digest 过短、无 Key Findings）→ 重新读取 raw 生成 digest
- 无法自动修复的（如 raw 为空）→ 提交用户决策

## 执行流程

```
1. Git 检查 + Obsidian 同步
2. 依次执行检查项 1-6
3. 自动修复可修复的问题
4. 汇总需用户决策的问题
5. 输出健康报告
6. Git commit（如有文件变更）
```

## 健康报告

```markdown
## Health Report — {YYYY-MM-DD}

### 自动修复
- ✅ 补充了 3 个缺失的 index 条目
- ✅ 修复了 2 个断链（paper_003_digest → paper_004_digest）
- ✅ 补充了 5 条隐性双链
- ✅ 同步了 2 个 index/digest 不一致的标签

### 需用户决策
- ⚠️ 矛盾：[[paper_001_digest|...]] 与 [[paper_005_digest|...]] 对 X 的效果结论相反
- ⚠️ 质量差：[[exp_002_digest|...]] digest 仅 3 行，可能生成失败

### 统计
- 总文档数：42（paper: 25, idea: 8, experiment: 6, discussion: 3）
- 断链：0（修复前 2）
- 孤立文档：0（修复前 3）
- 隐性双链补充：5
- 矛盾：1
- 质量问题：1
```

## 触发时机

- 批量导入后自动触发
- 用户主动要求（"检查一下知识库健康度"）
- 定期：每次对话开始时可选执行（轻量模式，只检查 1-3 项）

## 轻量模式

定期检查时不需要全量扫描，只做快速检查：
- 检查项 1（链接完整性）— 快速，grep 即可
- 检查项 2（孤立文档）— 快速，比对文件列表即可
- 检查项 3（index 同步）— 快速，比对 frontmatter 即可

检查项 4-6 需要语义理解，只在完整模式或用户主动要求时执行。

## 约束

- 只修改 digest 和 index，**永远不修改 raw**
- 矛盾和质量问题不自动修复，必须提交用户决策
- 修复操作要幂等（重复执行不产生副作用）
- 每次修复后立即 git commit，不要批量积累
