---
name: github-trending
description: 当需要采集 GitHub 热门开源项目时使用此技能
allowed-tools: Read, Grep, Glob, WebFetch
---

# GitHub Trending 采集技能

## 使用场景

当需要从 GitHub Trending 页面采集 AI/LLM/Agent 领域的热门开源项目时，使用本技能。该技能完成数据抓取、过滤、信息提取和结构化输出等全流程操作。

## 执行步骤

### 步骤 1：搜索热门仓库

通过 WebFetch 访问 GitHub Trending 页面，获取当日和本周热门仓库列表。

- **每日趋势**：`https://github.com/trending?since=daily`
- **每周趋势**：`https://github.com/trending?since=weekly`
- 可指定语言过滤，如 `https://github.com/trending/python?since=daily`

### 步骤 2：提取仓库信息

从页面内容中解析每个仓库的关键字段：

| 字段 | 说明 |
|------|------|
| `name` | 仓库名称（格式 `owner/repo`） |
| `url` | 仓库完整地址 |
| `description` | 仓库原始描述 |
| `language` | 主要编程语言 |
| `stars` | 总 Star 数 |
| `forks` | Fork 数 |
| `today_stars` | 今日新增 Star 数 |
| `topics` | 仓库 Topics 标签列表 |
| `license` | 开源许可证（如有） |

### 步骤 3：过滤 AI 相关内容

按以下规则筛选仓库：

**纳入标准**（标题、描述或 Topics 包含以下关键词之一）：
- 技术领域：`ai`, `llm`, `agent`, `machine-learning`, `deep-learning`, `nlp`, `transformer`, `rag`, `rlhf`, `fine-tuning`, `prompt-engineering`, `embedding`, `vector-database`, `inference`
- 模型/框架：`gpt`, `claude`, `llama`, `langchain`, `diffusion`, `stable-diffusion`, `whisper`, `chatglm`, `qwen`, `deepseek`, `mistral`
- 应用方向：`chatbot`, `code-generation`, `autonomous-agent`, `multi-agent`, `knowledge-graph`, `semantic-search`

**排除标准**（以下内容直接跳过）：
- 纯前端 UI 框架、CSS 库（与 AI 无直接关联）
- 通用 DevOps 工具、CI/CD、容器编排（不含 AI 特性）
- 游戏引擎、游戏素材、加密货币/区块链
- 面试题合集、Awesome 列表（非原创项目）
- 教程文档站、博客框架（非代码项目）

### 步骤 4：去重检查

- 使用 Glob 扫描 `knowledge/raw/` 和 `knowledge/articles/` 中已有记录
- 以 `url` 为唯一键，移除重复仓库
- 同一仓库在 daily 和 weekly 中同时出现时，仅保留一条

### 步骤 5：访问仓库详情

对通过过滤的每个仓库，通过 WebFetch 访问其 README 页面（`https://github.com/{owner}/{repo}`），获取更多上下文信息：
- 项目的核心功能和定位
- 技术架构亮点
- 与其他类似项目的差异

### 步骤 6：生成中文摘要

综合仓库 description 和 README 内容，为每个项目撰写中文摘要：
- 长度：80-150 字
- 语言：中文，核心术语缩写（如 LLM、RAG）可保留不译
- 内容：准确概括项目核心功能、技术亮点和应用场景
- 原则：**严格基于原文实际内容，禁止凭空编造**

### 步骤 7：排序并输出 JSON

- 综合 Star 数和今日新增 Star 数，按热度从高到低排列
- 输出结构化 JSON，格式见下方「输出格式」章节
- 至少输出 10 个有效条目

## 注意事项

- **禁止编造**：所有摘要和描述必须基于页面实际内容，严禁凭空杜撰项目功能或技术细节
- **时效性优先**：默认采集 daily 趋势，必要时可补充 weekly 趋势
- **语言过滤**：优先采集 `python`、`typescript`、`rust` 等 AI 领域常用语言的仓库
- **不写入文件**：本技能只负责采集和输出数据，不直接写入 `knowledge/` 目录；写入操作由 organizer Agent 执行
- **网络容错**：单次 WebFetch 失败不影响整体采集流程，记录失败条目并在输出中标注
- **避免 API 限流**：访问 README 详情时适当控制请求频率，避免触发 GitHub 限流

## 输出格式

```json
{
  "source": "github_trending",
  "skill": "github-trending",
  "collected_at": "2025-05-16T10:30:00+08:00",
  "items": [
    {
      "name": "owner/repo",
      "url": "https://github.com/owner/repo",
      "description": "仓库原始描述",
      "summary": "80-150 字中文摘要，综合 description 和 README 内容撰写",
      "language": "Python",
      "stars": 15000,
      "forks": 2300,
      "today_stars": 234,
      "topics": ["llm", "agent", "rag"],
      "license": "MIT"
    }
  ]
}
```

### 输出字段说明

| 字段 | 类型 | 说明 |
|------|------|------|
| `source` | `string` | 固定值 `github_trending`，标识数据来源 |
| `skill` | `string` | 固定值 `github-trending`，标识采集技能 |
| `collected_at` | `string` | ISO 8601 格式采集时间（含时区） |
| `items` | `array` | 采集到的仓库列表，按热度降序排列 |
| `items[].name` | `string` | 仓库名称，格式 `owner/repo` |
| `items[].url` | `string` | 仓库 GitHub 地址 |
| `items[].description` | `string` | 仓库原始英文描述 |
| `items[].summary` | `string` | AI 生成的中文摘要，80-150 字 |
| `items[].language` | `string` | 主要编程语言 |
| `items[].stars` | `int` | 总 Star 数 |
| `items[].forks` | `int` | Fork 数 |
| `items[].today_stars` | `int` | 今日新增 Star 数 |
| `items[].topics` | `array` | 仓库 Topics 标签列表 |
| `items[].license` | `string` | 开源许可证名称（如无则填 `null`） |
