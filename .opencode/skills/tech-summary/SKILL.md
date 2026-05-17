---
name: tech-summary
description: 当需要对采集的技术内容进行深度分析总结时使用此技能
allowed-tools: Read, Grep, Glob, WebFetch
---

# 技术深度分析总结技能

## 使用场景

当需要对采集 Agent 产出的原始技术内容（`knowledge/raw/` 目录下的采集数据）进行深度分析、提炼亮点、质量评分和趋势发现时，使用本技能。

## 执行步骤

### 步骤 1：读取最新采集数据

- 使用 Glob 扫描 `knowledge/raw/` 目录，按文件名时间戳排序，读取最新的采集文件
- 确认数据中包含 `items` 数组，每条记录含 `url`、`title`/`name`、`summary`、`source`、`popularity` 等字段

### 步骤 2：逐条深度分析

对每条记录依次执行以下分析，要求基于原文实际内容，**严禁编造**：

| 分析项 | 要求 |
|--------|------|
| **摘要重写** | 中文，不超 50 字，精准提炼项目核心价值，避免套话 |
| **技术亮点** | 2-3 个亮点，每个用事实说话（不超 30 字），如"LongMemEval-S R@5 达 95.2%"而非"检索效果好" |
| **质量评分** | 1-10 分，必须附评分理由（不超 50 字） |
| **标签建议** | 2-5 个标签，优先从已有标签体系选择 |

必要时对 Top 项目通过 WebFetch 访问原文链接获取更详细上下文。

### 步骤 3：趋势发现

综合所有分析结果，识别并输出：

- **共同主题**：本轮采集内容的共同关注点（如"Agent 工程方法论成熟""多模态 Agent 落地加速"）
- **新概念/术语**：首次出现或热度骤升的技术概念
- **值得关注的信号**：虽当前热度不高但成长迅速的方向

### 步骤 4：输出分析结果 JSON

按热度从高到低排列，输出结构化 JSON，格式见下方「输出格式」章节。

## 评分标准

| 分数 | 含义 | 说明 |
|------|------|------|
| 9-10 | 改变格局 | 重大突破性成果、范式级创新、行业里程碑事件 |
| 7-8 | 直接有帮助 | 实用工具/库、优质教程、深度分析、可落地的方法论 |
| 5-6 | 值得了解 | 有趣但不紧迫，了解即可，如概念验证、早期项目 |
| 1-4 | 可略过 | 信息量低、重复内容、营销稿、与 AI 关联度弱 |

### 评分约束

- 每 15 个项目中，**9-10 分不超过 2 个**，确保高分稀缺性
- 应有合理区分度，不可全部集中在 7-8 分区间
- 评分理由必须与分数一致，不可出现高分低理或低分高理

## 注意事项

- **基于原文**：所有摘要、亮点、评分必须基于原文实际内容，严禁凭空编造项目功能或技术细节
- **长度控制**：摘要 ≤50 字，亮点每条 ≤30 字，评分理由 ≤50 字
- **标签规范**：优先使用已有标签体系（LLM、Agent、RAG、Tool、Framework、Tutorial、Paper、Open Source 等）
- **不写入文件**：本技能只负责分析和输出数据，不直接写入 `knowledge/` 目录；写入操作由 curator Agent 执行
- **趋势发现**：必须基于本轮实际数据分析得出，不可使用预设结论
- **网络容错**：WebFetch 访问原文失败时，基于已有摘要信息完成分析，并在对应条目标注"基于元数据分析"

## 输出格式

```json
{
  "source": "github_trending",
  "skill": "tech-summary",
  "analyzed_at": "2026-05-16T12:00:00+08:00",
  "total": 10,
  "trends": [
    {
      "theme": "Agent 工程方法论成熟",
      "description": "多个高星项目围绕如何提升 AI Agent 编码质量和效率展开",
      "evidence": ["mattpocock/skills", "addyosmani/agent-skills", "rohitg00/agentmemory"]
    }
  ],
  "items": [
    {
      "url": "https://github.com/owner/repo",
      "title": "中文标题",
      "source": "github_trending",
      "popularity": "Stars: 15000 (本周+234)",
      "summary": "不超过50字的中文摘要，精准提炼项目核心价值。",
      "highlights": [
        "事实亮点一不超过30字",
        "事实亮点二不超过30字"
      ],
      "score": 8,
      "score_reason": "评分理由不超过50字",
      "tags": ["LLM", "Agent", "Tool"]
    }
  ]
}
```

### 输出字段说明

| 字段 | 类型 | 说明 |
|------|------|------|
| `source` | `string` | 数据来源标识 |
| `skill` | `string` | 固定值 `tech-summary` |
| `analyzed_at` | `string` | ISO 8601 格式分析时间（含时区） |
| `total` | `int` | 分析条目总数 |
| `trends` | `array` | 趋势发现列表 |
| `trends[].theme` | `string` | 趋势主题 |
| `trends[].description` | `string` | 趋势说明 |
| `trends[].evidence` | `array` | 支撑该趋势的条目列表 |
| `items` | `array` | 分析后的条目列表，按热度降序 |
| `items[].url` | `string` | 原文链接 |
| `items[].title` | `string` | 中文标题 |
| `items[].source` | `string` | 来源标识 |
| `items[].popularity` | `string` | 热度指标 |
| `items[].summary` | `string` | 重写的中文摘要，≤50 字 |
| `items[].highlights` | `array` | 技术亮点，2-3 条，每条 ≤30 字 |
| `items[].score` | `int` | 质量评分，1-10 |
| `items[].score_reason` | `string` | 评分理由，≤50 字 |
| `items[].tags` | `array` | 建议标签，2-5 个 |
