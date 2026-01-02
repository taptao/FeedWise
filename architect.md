# FeedWise 架构说明

> 本文档是 FeedWise 项目的架构单一事实源（Single Source of Truth），任何代码或架构变更必须对齐并同步更新。

---

## 1. 概览

### 项目目标
FeedWise 是一个智能 RSS 阅读助手，从 FreshRSS 同步订阅内容，通过 LLM 分析文章价值并智能排序，帮助用户高效阅读。

### 关键能力
- **FreshRSS 同步**：自动从 FreshRSS 获取订阅源和未读文章
- **全文抓取**：智能检测并抓取 RSS 摘要型内容的原文
- **AI 分析**：使用 LLM 生成摘要、评分、标签
- **智能排序**：按价值、时间、来源多维排序
- **Web 界面**：现代化的 React 前端

### 技术栈

| 层级 | 技术 |
|------|------|
| 后端框架 | FastAPI |
| ORM/数据模型 | SQLModel + SQLAlchemy |
| 数据库 | SQLite (aiosqlite 异步) |
| 定时任务 | APScheduler |
| 全文抓取 | trafilatura |
| LLM | OpenAI / Ollama (工厂模式) |
| 前端 | React + Vite + TypeScript + Tailwind |
| 部署 | Docker Compose |

---

## 2. 模块与目录职责

### 目录结构

```
feedwise/
├── src/feedwise/          # 后端源码
│   ├── main.py            # FastAPI 入口
│   ├── config.py          # 配置管理
│   ├── api/               # API 路由层
│   ├── core/              # 核心业务逻辑
│   ├── fetcher/           # 全文抓取
│   ├── llm/               # LLM 集成
│   ├── models/            # 数据模型
│   ├── scheduler/         # 定时任务
│   └── utils/             # 工具函数
├── frontend/              # React 前端
├── docker/                # Dockerfile
├── docker-compose.yml     # 容器编排
└── data/                  # 数据持久化
```

### 后端分层

#### API Layer (`api/`)
HTTP 路由层，处理请求/响应，调用 Core 层。

| 模块 | 职责 |
|------|------|
| `articles.py` | 文章列表、详情、读/星标、手动抓取 |
| `feeds.py` | 订阅源列表、优先级设置 |
| `analysis.py` | AI 分析触发、查询、批量、流式 |
| `fetch.py` | 抓取状态、触发、重试 |
| `sync.py` | FreshRSS 同步触发 |
| `settings.py` | 系统设置、连接测试 |

#### Core Layer (`core/`)
核心业务逻辑，不直接处理 HTTP。

| 模块 | 职责 |
|------|------|
| `freshrss.py` | FreshRSS Google Reader API 客户端 |
| `sync.py` | 同步服务：拉取 feeds/articles，写库 |
| `fetch_runner.py` | 全文抓取执行器：批量并发抓取 |
| `ranking.py` | 文章排序器：聚合查询、多维排序 |

#### Support Layers

| 层 | 模块 | 职责 |
|----|------|------|
| `fetcher/` | `detector.py` | 内容完整性检测 |
| | `extractor.py` | trafilatura 全文提取 |
| `llm/` | `base.py` | Provider 抽象基类 |
| | `factory.py` | 工厂函数 |
| | `analyzer.py` | 文章分析器 |
| | `openai.py` | OpenAI 实现 |
| | `ollama.py` | Ollama 实现 |
| `models/` | `database.py` | 数据库初始化/会话 |
| | `feed.py` | Feed 实体 |
| | `article.py` | Article 实体 |
| | `analysis.py` | ArticleAnalysis 实体 |
| | `sync.py` | SyncStatus 实体 |
| `scheduler/` | `tasks.py` | 定时任务定义 |
| `utils/` | `html_parser.py` | HTML 解析工具 |

#### 入口与配置

| 模块 | 职责 |
|------|------|
| `main.py` | FastAPI 入口，lifespan 管理 |
| `config.py` | Pydantic Settings，从 .env 加载 |

### 前端结构 (`frontend/`)

| 目录/文件 | 职责 |
|-----------|------|
| `src/pages/` | 页面组件（HomePage, ArticlePage, SettingsPage） |
| `src/components/` | UI 组件（Layout, Sidebar, ArticleCard） |
| `src/api/client.ts` | API 客户端封装 |

### 部署目录

| 目录/文件 | 职责 |
|-----------|------|
| `docker/backend.Dockerfile` | 后端镜像构建 |
| `docker/frontend.Dockerfile` | 前端镜像构建 |
| `docker-compose.yml` | 容器编排（后端 8000，前端 5173） |
| `data/` | SQLite 数据库挂载点 |

---

## 3. 核心流程

### 系统整体架构图

```
┌─────────────────────────────────────────────────────────────────────────┐
│                              用户浏览器                                  │
└─────────────────────────────────┬───────────────────────────────────────┘
                                  │ HTTP
                                  ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                         Frontend (React/Vite)                           │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐                │
│  │ HomePage │  │ Article  │  │ Settings │  │ Sidebar  │                │
│  │          │  │   Page   │  │   Page   │  │          │                │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘                │
│                         │                                               │
│                    api/client.ts                                        │
└─────────────────────────────────┬───────────────────────────────────────┘
                                  │ REST API
                                  ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                          Backend (FastAPI)                              │
│  ┌───────────────────────────────────────────────────────────────────┐  │
│  │                           API Layer                               │  │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌─────────┐ │  │
│  │  │ articles │ │  feeds   │ │ analysis │ │  fetch   │ │  sync   │ │  │
│  │  └────┬─────┘ └────┬─────┘ └────┬─────┘ └────┬─────┘ └────┬────┘ │  │
│  └───────┼────────────┼────────────┼────────────┼────────────┼──────┘  │
│          │            │            │            │            │         │
│  ┌───────┴────────────┴────────────┴────────────┴────────────┴──────┐  │
│  │                          Core Layer                              │  │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────────┐  │  │
│  │  │ ranking  │  │   sync   │  │ freshrss │  │   fetch_runner   │  │  │
│  │  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────────┬─────────┘  │  │
│  └───────┼─────────────┼─────────────┼─────────────────┼────────────┘  │
│          │             │             │                 │               │
│  ┌───────┴─────────────┴─────────────┴─────────────────┴────────────┐  │
│  │                       Support Layers                             │  │
│  │  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌────────┐  │  │
│  │  │  llm/   │  │ fetcher │  │ models/ │  │scheduler│  │ utils/ │  │  │
│  │  └────┬────┘  └────┬────┘  └────┬────┘  └────┬────┘  └────────┘  │  │
│  └───────┼────────────┼────────────┼────────────┼───────────────────┘  │
└──────────┼────────────┼────────────┼────────────┼───────────────────────┘
           │            │            │            │
           ▼            ▼            ▼            ▼
    ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐
    │  LLM     │  │   Web    │  │  SQLite  │  │ FreshRSS │
    │(OpenAI/  │  │  Pages   │  │ Database │  │  Server  │
    │ Ollama)  │  │          │  │          │  │          │
    └──────────┘  └──────────┘  └──────────┘  └──────────┘
```

### 数据流向图

```
┌────────────┐     同步触发      ┌────────────┐    Google Reader API    ┌────────────┐
│  Scheduler │ ───────────────▶ │    Sync    │ ◀────────────────────▶ │  FreshRSS  │
│   (定时)    │                  │  Service   │                        │   Server   │
└────────────┘                  └─────┬──────┘                        └────────────┘
                                      │
                                      │ 写入 Feed/Article
                                      │ fetch_status=pending
                                      ▼
┌────────────┐    查询 pending   ┌────────────┐     HTTP GET          ┌────────────┐
│  Scheduler │ ───────────────▶ │   Fetch    │ ────────────────────▶ │   Web      │
│   (定时)    │                  │   Runner   │ ◀──────────────────── │   Pages    │
└────────────┘                  └─────┬──────┘     HTML Content       └────────────┘
                                      │
                                      │ 更新 full_content
                                      │ fetch_status=success/failed
                                      ▼
┌────────────┐    触发分析       ┌────────────┐      Prompt           ┌────────────┐
│  API 请求  │ ───────────────▶ │  Analyzer  │ ────────────────────▶ │    LLM     │
│  (用户)    │                  │            │ ◀──────────────────── │  Provider  │
└────────────┘                  └─────┬──────┘   JSON (分析结果)       └────────────┘
                                      │
                                      │ 写入 ArticleAnalysis
                                      ▼
┌────────────┐    查询文章       ┌────────────┐
│  Frontend  │ ───────────────▶ │   Ranker   │ ───▶ 聚合排序后返回
│            │ ◀─────────────── │            │
└────────────┘   排序后的列表    └────────────┘
```

### 流程描述

#### 启动流程
```
main.py lifespan
  → get_settings() 加载配置
  → init_db() 初始化数据库表
  → create_scheduler() 启动定时任务
  → 注册路由 + CORS 中间件
```

#### 定时任务
- 任务：`sync_and_fetch_task`
- 触发：启动时立即执行一次 + 按 `sync_interval_minutes` 周期
- 流程：同步 FreshRSS → 等待 2s → 全文抓取

#### FreshRSS 同步 (`core.sync`)
1. 调用 FreshRSSClient 拉取 feeds 列表
2. Upsert 到 Feed 表
3. 拉取未读 articles
4. 写入 Article 表，`fetch_status=pending`

#### 全文抓取 (`core.fetch_runner`)
1. 查询 `fetch_status=pending` 的文章
2. 按 Feed 配置或智能检测决定是否抓取
3. 并发调用 trafilatura 抓取原文
4. 更新 `full_content`、`content_source`、`fetch_status`
5. 批次状态存内存字典

#### LLM 分析 (`api.analysis` + `llm.analyzer`)
1. API 触发单篇或批量分析
2. ArticleAnalyzer 构建 prompt
3. 调用 LLMProvider（OpenAI/Ollama）
4. 解析 JSON 响应为 AnalysisResult
5. 存入 ArticleAnalysis 表

#### 排序查询 (`core.ranking`)
- 聚合 Article + ArticleAnalysis + Feed
- 支持排序：按价值分 / 时间 / 来源
- 支持筛选：未读 / 收藏 / 全部

---

## 4. 数据模型与状态

### 实体

| 实体 | 用途 | 关键字段 |
|------|------|----------|
| Feed | 订阅源 | id, title, url, fetch_full_text (always/auto/never) |
| Article | 文章 | id, feed_id, title, content, full_content, fetch_status, is_read, is_starred |
| ArticleAnalysis | AI 分析结果 | article_id, summary, key_points, value_score, tags |
| SyncStatus | 同步记录 | sync_type, status, articles_fetched |

### 状态枚举

#### fetch_status（文章抓取状态）
| 值 | 含义 |
|----|------|
| pending | 待抓取 |
| success | 抓取成功 |
| failed | 抓取失败 |
| skipped | 已跳过（无需抓取或配置为 never） |

### 内存状态（非持久化）

| 状态 | 存储 | 用途 |
|------|------|------|
| 抓取批次状态 | `FetchBatchStatus` / `_fetch_status` dict | 追踪批量抓取进度 |
| 分析批次状态 | `_batch_status` dict | 追踪批量分析进度 |

> 注意：批次状态仅存于内存，服务重启后丢失，用于任务进度监控。

