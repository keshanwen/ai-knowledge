# 项目四大模块关系流程图

```mermaid
flowchart TB
    subgraph A["AGENTS.md<br/>项目级指令"]
        A1["编码规范 (PEP8/snake_case/logging)"]
        A2["技术栈定义 (Python3.12/LangGraph/OpenClaw)"]
        A3["知识条目 JSON 格式规范"]
        A4["Agent 角色概览 + 红线约束"]
    end

    subgraph B[".opencode/agents/<br/>Agent 角色定义"]
        direction LR
        B1["collector.md<br/>采集 Agent"]
        B2["analyzer.md<br/>分析 Agent"]
        B3["curator.md<br/>整理 Agent"]
        B4["distributor.md<br/>分发 Agent"]
    end

    subgraph C[".opencode/skills/<br/>可复用技能"]
        C1["github-trending<br/>GitHub Trending 采集"]
        C2["tech-summary<br/>技术深度分析"]
  
  C3["push-to-channel<br/>渠道推送"]
    end

    subgraph D["knowleadge/<br/>数据存储"]
        D1["raw/<br/>原始采集数据"]
        D2["articles/<br/>结构化知识条目"]
    end

    A -->|"定义规范 + 约束"| B
    A -->|"定义 JSON 格式"| D2
    B1 -->|"调用 Skill"| C1
    B2 -->|"调用 Skill"| C2
    B1 -->|"产出原始数据"| D1
    B2 -->|"读取原始数据"| D1
    B2 -->|"产出分析结果"| B3
    B3 -->|"去重 + 格式化"| D2
    B4 -->|"读取 published 条目"| D2
    B4 -->|"调用 Skill"| C3
    C3 -->|"推送消息"| B4

    style A fill:#e1f5fe,stroke:#0288d1
    style B fill:#fff3e0,stroke:#f57c00
    style C fill:#e8f5e9,stroke:#388e3c
    style D fill:#fce4ec,stroke:#c62828
```

## 关系说明

| 关系 | 说明 |
|------|------|
| **AGENTS.md → Agents** | 定义编码规范、技术栈、JSON 格式和红线，所有 Agent 共享此上下文 |
| **AGENTS.md → articles/** | 定义知识条目的 `id`/`title`/`source_url`/`summary`/`tags`/`status` 等字段格式 |
| **collector → github-trending Skill** | 采集 Agent 通过 `skill("github-trending")` 加载采集工作流指令 |
| **collector → raw/** | 采集结果写入 `knowleadge/raw/`，如 `github-trending-2026-05-17.json` |
| **analyzer → tech-summary Skill** | 分析 Agent 通过 `skill("tech-summary")` 加载分析流程 |
| **analyzer → raw/** | 读取 `knowleadge/raw/` 中最新的采集数据 |
| **analyzer → curator** | 分析结果作为中间数据传递给整理 Agent（不应直接写文件） |
| **curator → articles/** | 去重审核后将标准化 JSON 写入 `knowleadge/articles/{id}.json` |
| **distributor → articles/** | 读取 `status: published` 的条目进行渠道分发 |
| **distributor → push-to-channel Skill** | 调用推送技能将内容发至 Telegram/飞书 |

## 数据流向

```
collector ──(产出)──▶ raw/ ──(消费)──▶ analyzer ──(中间数据)──▶ curator ──(格式化)──▶ articles/ ──(消费)──▶ distributor ──▶ Telegram/飞书
```
