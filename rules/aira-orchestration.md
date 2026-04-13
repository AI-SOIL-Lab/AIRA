---
description: AIRA 知识库编排规则 — 定义 skill 路由、git 协作、文件操作约束
alwaysApply: true
---

# AIRA 编排规则

## Skill 路由

根据用户意图自动选择 skill：

| 用户意图 | Skill | 示例 |
|---------|-------|------|
| 添加/导入/记录内容 | `ingest` | "把这篇论文加进来"、"我有个想法"、"这是实验数据" |
| 提问/分析/对比 | `research` | "X 和 Y 的关系"、"基于我的数据"、"对比这两篇论文" |
| 检查/修复知识库 | `health` | "检查健康度"、"修复断链"、"找孤立文档" |

多个意图同时出现时，按 ingest → research → health 顺序执行。

### ingest 统一处理逻辑

`ingest` skill 统一处理所有知识库录入场景：

1. **判断是否需要 raw 录入**（用户指定了文件/URL → 是）
2. **如果需要**：调用 `aira-ingest` CLI tool 录入 raw 文件
3. **git diff** 发现所有新文件（`git diff HEAD -- vault/raw/`，含用户手动录入的）
4. **对每个新文件**：生成 digest → 写入 `vault/digest/` → 更新 `vault/index.md`
5. **Git commit**

**aira-ingest（CLI tool）：** 位于 `skills/ingest/ingest_raw/` 包中，提供确定性的文件转换录入功能。

## Git 协作协议

**每次操作必须遵循 git 前置/后置协议，三个 skill 共用：**

### 前置（操作前）

1. `git status` — 检查工作区状态
2. 如果有 Obsidian 侧未跟踪的新文件 → 调用 `ingest` skill 补跑入库
3. 如果用户编辑了 digest → 尊重修改，不覆盖
4. 如果用户编辑了 raw → 提示"原文已修改，是否需要重新生成 digest？"

### 后置（操作后）

1. `git add` 涉及变更的文件
2. `git commit -m "<skill>: <简要描述>"` — commit message 以 skill 名开头

**用户不介入 git** — 用户只在 Obsidian 中编辑，git 由 AI 全权管理。

## 文件操作约束

- **raw 不可变** — 写入后任何 skill 都不修改 raw 文件
- **digest 可写** — ingest 生成、health 修复、用户编辑均可
- **index.md 可写** — ingest 追加条目、health 修复同步
- **写入后校验** — 保存文件后检查大小/行数，异常时告警重试

## Vault 路径

```
vault/
├── index.md
├── raw/{type}_{NNN}.md
└── digest/{type}_{NNN}_digest.md
```

所有文件操作必须基于 `vault/` 目录，不在此目录外的任何位置创建知识库文件。
