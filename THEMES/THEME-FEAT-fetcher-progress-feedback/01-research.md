# Research: FEAT-fetcher-progress-feedback

## 1. 现有架构分析

### 1.1 全文抓取流程

```
用户触发 → API /fetch-full 或 /fetch/batch
         ↓
    FullTextExtractor.fetch()
         ↓
    trafilatura (fetch_url + extract)
         ↓
    更新 Article.full_content / fetch_status
         ↓
    返回结果
```

### 1.2 涉及文件

| 文件 | 职责 |
|------|------|
| `src/feedwise/fetcher/extractor.py` | trafilatura 封装，执行实际抓取 |
| `src/feedwise/core/fetch_runner.py` | 批量抓取执行器，管理并发和状态 |
| `src/feedwise/api/articles.py` | 单篇抓取 API `/fetch-full` |
| `src/feedwise/api/fetch.py` | 批量抓取 API `/fetch/batch`, `/fetch/progress` |
| `src/feedwise/models/article.py` | Article 模型，含 fetch_status 字段 |
| `frontend/src/pages/ArticlePage.tsx` | 文章详情页，单篇抓取按钮 |
| `frontend/src/pages/HomePage.tsx` | 首页，批量抓取 TaskCard |
| `frontend/src/components/TaskCard.tsx` | 任务卡片组件 |
| `frontend/src/api/client.ts` | API 客户端 |

### 1.3 数据模型

**Article 模型关键字段：**
- `fetch_status`: `pending | success | failed | skipped`
- `full_content`: 抓取到的全文
- `content_source`: `feed | fetched`

**内存状态（非持久化）：**
- `FetchBatchStatus`: 批次进度、错误列表
- `_fetch_status` dict: 全局批次状态存储

## 2. 问题定位

### 2.1 后端问题

| 问题 | 位置 | 影响 |
|------|------|------|
| 错误信息未持久化 | `fetch_runner.py` | 重启后丢失错误详情 |
| 单篇抓取无详细错误 | `articles.py` `/fetch-full` | 前端无法显示具体原因 |
| 无重试计数 | `Article` 模型 | 无法限制重试次数 |

### 2.2 前端问题

| 问题 | 位置 | 影响 |
|------|------|------|
| 单篇抓取无错误展示 | `ArticlePage.tsx` L53-56 | 用户不知道失败原因 |
| 抓取状态无视觉区分 | `ArticlePage.tsx` | pending/failed 显示相同 |
| 批量进度无实时更新 | `HomePage.tsx` | 2秒轮询间隔较长 |

### 2.3 具体代码问题

**ArticlePage.tsx 第 53-56 行：**
```tsx
const fetchFullMutation = useMutation({
  mutationFn: () => api.articles.fetchFull(id!),
  onSuccess: () => {
    queryClient.invalidateQueries({ queryKey: ['article', id] });
  },
  // 缺少 onError 处理
  // 缺少对 success: false 的处理
});
```

**问题：** `fetchFull` 返回 `{ success: false, error: "..." }` 时，HTTP 状态码是 200，所以 `onSuccess` 会被调用，但前端没有检查 `success` 字段。

**articles.py 第 108-115 行：**
```python
if result.success and result.content:
    # ... 成功处理
    return {"success": True, ...}

article.fetch_status = "failed"
await session.commit()
return {"success": False, "error": result.error}
# 错误信息未存入数据库
```

## 3. 技术约束

- 不修改 trafilatura 核心逻辑
- 不引入新的抓取库
- 保持 API 向后兼容
- 遵循现有代码风格（ruff + pyright strict）

## 4. 待澄清问题

1. 是否需要将错误信息持久化到数据库？（需要新增字段）
2. 是否需要实现自动重试机制？
3. 批量抓取进度是否需要 WebSocket 实时推送？还是保持轮询？

## 5. 下一步

等待用户确认后进入 Design 阶段，探索解决方案。
