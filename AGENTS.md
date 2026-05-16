# AGENTS.md

## 项目概述

AI 知识库助手：自动从 GitHub Trending 和 Hacker News 采集 AI/LLM/Agent 领域的技术动态，经 AI 分析后结构化存储为 JSON 知识条目，并通过 Telegram、飞书等渠道分发推送。

## 技术栈

| 类别 | 技术 |
|------|------|
| 运行环境 | Python 3.12 |
| AI 编排 | OpenCode Agent + 国产大模型（DeepSeek / Qwen 等） |
| 工作流引擎 | LangGraph |
| 多渠道分发 | OpenClaw（Telegram / 飞书） |

## 项目结构

```
ai-knowleadge-base/
├── AGENTS.md                    # 本文件
├── .opencode/
│   ├── agents/                  # OpenCode Agent 定义
│   │   ├── collector.md         # 采集 Agent
│   │   ├── analyzer.md          # 分析 Agent
│   │   ├── curator.md           # 整理 Agent
│   │   └── distributor.md       # 分发 Agent
│   └── skills/                  # OpenCode Skill 定义
│       ├── fetch-github-trending.md
│       ├── fetch-hackernews.md
│       └── push-to-channel.md
├── knowleadge/
│   ├── raw/                     # 原始采集数据（Markdown / HTML）
│   └── articles/                # 结构化知识条目（JSON）
└── README.md
```

## 编码规范

- **风格指南**：严格遵循 [PEP 8](https://peps.python.org/pep-0008/)
- **命名规范**：变量/函数/方法使用 `snake_case`，类名使用 `PascalCase`
- **Docstring**：采用 [Google 风格](https://google.github.io/styleguide/pyguide.html#38-comments-and-docstrings)，必须包含 `Args`、`Returns`、`Raises`
- **日志**：统一使用 `logging` 模块，**禁止使用裸 `print()`** 输出调试或运行信息
- **类型注解**：所有函数必须添加完整的类型注解

## 知识条目 JSON 格式

每个结构化知识条目存储为独立的 JSON 文件，文件名格式 `{id}.json`。

```json
{
  "id": "2025-05-16-001",
  "title": "OpenAI 发布 GPT-5 技术报告",
  "source_url": "https://news.ycombinator.com/item?id=12345678",
  "source_type": "hackernews",
  "summary": "OpenAI 正式发布 GPT-5，在推理能力和多模态理解上取得突破性进展...",
  "tags": ["LLM", "OpenAI", "推理"],
  "status": "published",
  "created_at": "2025-05-16T10:30:00+08:00",
  "push_channels": ["telegram", "feishu"],
  "push_status": {
    "telegram": "success",
    "feishu": "pending"
  }
}
```

### 字段说明

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | `str` | 唯一标识，格式 `YYYY-MM-DD-NNN` |
| `title` | `str` | 中文标题 |
| `source_url` | `str` | 原文链接 |
| `source_type` | `str` | 来源类型：`hackernews` / `github_trending` |
| `summary` | `str` | AI 生成的中文摘要（200 字以内） |
| `tags` | `list[str]` | 标签列表 |
| `status` | `str` | 状态：`draft` / `reviewed` / `published` / `archived` |
| `created_at` | `str` | ISO 8601 创建时间（含时区） |
| `push_channels` | `list[str]` | 目标分发渠道列表 |
| `push_status` | `dict` | 各渠道推送状态 |

## Agent 角色概览

| 角色 | Agent 文件 | 职责 | 输入 | 输出 |
|------|-----------|------|------|------|
| **采集** | `collector.md` | 定时抓取 GitHub Trending 和 Hacker News 的 AI/LLM/Agent 相关条目，保存原始内容 | 定时触发 / 手动触发 | `knowleadge/raw/*.md` |
| **分析** | `analyzer.md` | 读取原始内容，调用 LLM 提取关键信息并生成中文摘要和标签 | `knowleadge/raw/*.md` | 结构化中间数据 |
| **整理** | `curator.md` | 对分析结果去重、审核质量，生成最终 JSON 知识条目 | 分析结果 | `knowleadge/articles/{id}.json` |
| **分发** | `distributor.md` | 将状态为 `published` 的条目通过 OpenClaw 推送到指定渠道 | `knowleadge/articles/*.json` | Telegram / 飞书消息 |

## 红线（绝对禁止）

- 禁止在代码中硬编码 API Key、Token 或任何凭据，必须通过环境变量或 `.env` 文件读取
- 禁止将 `.env` 或包含敏感信息的文件提交到 Git 仓库
- 禁止使用裸 `print()` 输出日志信息，一律使用 `logging` 模块
- 禁止将未经 AI 分析的原始内容直接分发到渠道
- 禁止重复推送同一条目（以 `id` 去重）
- 禁止在 `knowleadge/articles/` 中手动编辑 JSON（应由整理 Agent 统一生成）
- 禁止使用 `os.system()` 或 `subprocess` 拼接外部输入执行 shell 命令
- 禁止在 AI prompt 中夹带个人身份信息或敏感数据
