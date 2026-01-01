# FeedWise - 智能 RSS 阅读器

FeedWise 是一个智能 RSS 阅读助手，通过 AI 分析文章价值，帮助你高效阅读。

## ✨ 核心功能

- 🔄 **FreshRSS 同步** - 自动从 FreshRSS 获取订阅内容
- 🤖 **AI 智能分析** - 使用 LLM 分析文章，生成摘要和价值评分
- 📊 **智能排序** - 按价值、时间、来源排序，优先阅读高价值内容
- 🏷️ **自动标签** - AI 自动为文章打标签分类
- 📱 **现代 UI** - 简洁美观的 Web 界面

---

## 🚀 快速开始

### 1. 环境要求

- Python 3.11+
- Node.js 18+
- FreshRSS 实例（启用 Google Reader API）
- Ollama 或 OpenAI API

### 2. 安装后端

```bash
cd feedwise

# 创建虚拟环境
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# .venv\Scripts\activate   # Windows

# 安装依赖
pip install -e .
```

### 3. 配置环境变量

创建 `.env` 文件：

```env
# FreshRSS 配置（必填）
FRESHRSS_URL=http://your-freshrss-server:8080
FRESHRSS_USERNAME=admin
FRESHRSS_API_PASSWORD=your-api-password

# LLM 配置 - 选择一种

# 方式 A: Ollama（推荐本地部署）
LLM_PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=qwen2.5:7b

# 方式 B: OpenAI
# LLM_PROVIDER=openai
# OPENAI_API_KEY=sk-xxx
# OPENAI_BASE_URL=https://api.openai.com/v1
# OPENAI_MODEL=gpt-4o-mini

# 同步配置
SYNC_INTERVAL_MINUTES=30
```

### 4. 启动后端

```bash
cd feedwise
uvicorn feedwise.main:app --host 0.0.0.0 --port 8000
```

### 5. 安装并启动前端

```bash
cd feedwise/frontend

# 配置 API 地址
echo "VITE_API_BASE=http://your-server-ip:8000" > .env

# 安装依赖
npm install

# 启动开发服务器
npm run dev -- --host 0.0.0.0
```

### 6. 访问界面

- **前端界面**: http://your-server-ip:5173
- **API 文档**: http://your-server-ip:8000/docs

---

## 📖 操作指南

### 同步文章

**方式 1: 界面操作**

点击右上角的 **「同步」** 按钮，从 FreshRSS 拉取最新文章。

**方式 2: API 调用**

```bash
curl -X POST "http://localhost:8000/api/sync"
```

**自动同步**

系统默认每 30 分钟自动同步一次（可在 `.env` 中修改 `SYNC_INTERVAL_MINUTES`）。

---

### AI 分析文章

#### 方式 1: 界面批量分析（推荐）

1. 打开 FeedWise 首页
2. 点击 **「AI 批量分析」** 按钮（紫色渐变按钮）
3. 系统自动分析未分析的文章（每次 20 篇）
4. 进度条显示分析进度
5. 完成后自动刷新列表

#### 方式 2: API 批量分析

```bash
# 分析 20 篇未分析的文章
curl -X POST "http://localhost:8000/api/analysis/batch?limit=20"

# 返回示例
{
  "batch_id": "batch_12345",
  "message": "开始分析 20 篇文章",
  "count": 20
}

# 查看分析进度
curl "http://localhost:8000/api/analysis/batch/batch_12345"

# 进度示例
{
  "total": 20,
  "completed": 15,
  "failed": 0,
  "status": "running"  // running | completed
}
```

#### 方式 3: 单篇文章分析

```bash
# 分析指定文章
curl -X POST "http://localhost:8000/api/analysis/article?article_id=YOUR_ARTICLE_ID"
```

---

### 文章排序

| 排序方式 | 说明 |
|---------|------|
| **按价值** | 按 AI 评分从高到低排序，优先展示高价值文章 |
| **按时间** | 按发布时间从新到旧排序 |
| **按来源** | 按订阅源分组显示 |

---

### 文章筛选

| 筛选选项 | 说明 |
|---------|------|
| **未读** | 只显示未读文章 |
| **收藏** | 只显示已收藏文章 |
| **全部** | 显示所有文章 |

点击左侧边栏的具体 Feed 可以只查看该订阅源的文章。

---

## 🔧 API 参考

### 文章相关

| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/articles` | GET | 获取文章列表 |
| `/api/articles/{id}` | GET | 获取文章详情 |
| `/api/articles/{id}/read` | PATCH | 标记已读/未读 |
| `/api/articles/{id}/star` | PATCH | 收藏/取消收藏 |

### 分析相关

| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/analysis/batch` | POST | 批量分析文章 |
| `/api/analysis/batch/{id}` | GET | 获取批量分析进度 |
| `/api/analysis/article` | POST | 分析单篇文章 |
| `/api/analysis/article/{id}` | GET | 获取分析结果 |

### 同步相关

| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/sync` | POST | 触发同步 |
| `/api/sync/status` | GET | 获取同步状态 |

### Feed 相关

| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/feeds` | GET | 获取订阅源列表 |
| `/api/feeds/{id}/priority` | PATCH | 设置优先级 |

完整 API 文档请访问: http://localhost:8000/docs

---

## 📊 AI 分析结果说明

每篇文章分析后会生成以下信息：

| 字段 | 说明 | 示例 |
|------|------|------|
| **summary** | 文章摘要（中文） | "文章介绍了 2025 年 AI 领域的发展趋势..." |
| **value_score** | 价值评分 (1-10) | 7.5 |
| **reading_time** | 预估阅读时间（分钟） | 5 |
| **key_points** | 核心要点列表 | ["观点1", "观点2", "观点3"] |
| **tags** | 自动标签 | ["技术", "AI", "趋势"] |
| **language** | 内容语言 | "zh" / "en" |

### 价值评分标准

| 分数范围 | 含义 |
|---------|------|
| 8-10 | 🌟 高价值，值得深入阅读 |
| 6-8 | 👍 有价值，推荐阅读 |
| 4-6 | 📄 一般，可快速浏览 |
| 1-4 | ⏭️ 低价值，可跳过 |

---

## 🛠️ 故障排除

### 同步失败

1. 检查 FreshRSS 是否启用了 Google Reader API
2. 验证 API 密码是否正确
3. 检查网络连接

```bash
# 测试 FreshRSS 连接
curl -X POST "http://localhost:8000/api/settings/test-freshrss"
```

### AI 分析失败

1. 检查 Ollama 是否运行
2. 验证模型是否已下载

```bash
# 检查 Ollama
curl http://localhost:11434/api/tags

# 下载模型
ollama pull qwen2.5:7b
```

### 前端无法连接后端

1. 检查 `.env` 中的 `VITE_API_BASE` 配置
2. 确保后端允许 CORS

---

## 📁 项目结构

```
feedwise/
├── src/feedwise/
│   ├── api/           # API 路由
│   ├── core/          # 核心服务（同步、排序）
│   ├── llm/           # LLM 集成
│   ├── models/        # 数据模型
│   ├── fetcher/       # 全文抓取
│   └── main.py        # 应用入口
├── frontend/          # React 前端
│   ├── src/
│   │   ├── api/       # API 客户端
│   │   ├── components/# UI 组件
│   │   └── pages/     # 页面
│   └── package.json
├── .env.example       # 环境变量模板
└── pyproject.toml     # Python 依赖
```

---

## 📜 License

MIT License
