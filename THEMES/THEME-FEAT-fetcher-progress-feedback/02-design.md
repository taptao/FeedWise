# Design: FEAT-fetcher-progress-feedback

## 1. 设计理念

**统一任务队列 + 单一处理引擎**

用户不需要理解"抓取"和"分析"的区别，只关心文章是否"处理完成"。

## 2. 统一状态机

每篇文章的处理状态：
```
synced → pending_fetch → fetching → pending_analysis → analyzing → done
                ↓                          ↓
           fetch_failed              analysis_failed
```

## 3. 后端设计

### 3.1 Article 模型扩展
```python
# 新增字段
process_status: str  # synced|pending_fetch|fetching|pending_analysis|analyzing|done|failed
process_error: str | None  # 错误信息
process_stage: str | None  # 失败阶段: fetch|analysis
```

### 3.2 统一处理引擎 (`core/processor.py`)
- 单一后台 worker 循环处理队列
- 自动判断每篇文章下一步操作
- 支持 start/pause 控制

### 3.3 API 简化 (`api/process.py`)
```
POST /api/process/start   - 开始处理
POST /api/process/pause   - 暂停
GET  /api/process/stats   - 统计 (pending/processing/done/failed)
GET  /api/process/ws      - WebSocket 实时进度
POST /api/process/retry   - 重试失败项
```

### 3.4 WebSocket 消息格式
```json
{"type": "progress", "data": {"total": 17, "completed": 5, "current": "文章标题..."}}
{"type": "item_done", "data": {"article_id": "xxx", "status": "done"}}
{"type": "item_failed", "data": {"article_id": "xxx", "stage": "fetch", "error": "403"}}
{"type": "paused", "data": {}}
{"type": "completed", "data": {"total": 17, "success": 15, "failed": 2}}
```

## 4. 前端设计

### 4.1 统一任务面板 (替换两个 TaskCard)
```
┌─────────────────────────────────────────────────────────┐
│                    智能处理                              │
│  ┌─────────────────────────────────────────────────┐   │
│  │  待处理: 17  │  处理中: 3  │  已完成: 42  │  失败: 2 │   │
│  └─────────────────────────────────────────────────┘   │
│                                                         │
│  [▶ 开始处理]   [⏸ 暂停]                               │
│                                                         │
│  ┌─────────────────────────────────────────────────┐   │
│  │ ████████████░░░░░░░░  12/17  正在分析: xxx...   │   │
│  └─────────────────────────────────────────────────┘   │
│                                                         │
│  失败 (2):  [查看详情]  [重试]                          │
└─────────────────────────────────────────────────────────┘
```

### 4.2 新增组件
- `ProcessPanel.tsx` - 统一任务面板
- `useProcessWebSocket.ts` - WebSocket hook
- `FailedItemsModal.tsx` - 失败详情弹窗

### 4.3 删除/废弃
- 移除 `TaskCard.tsx` 双卡片模式
- 移除 `api.fetch.*` 和 `api.analysis.batch*` 相关调用

## 5. 架构图

```
┌─────────────────────────────────────────────────────────────┐
│                        Frontend                             │
│  ┌────────────────────────────────────────────────────┐    │
│  │              ProcessPanel (统一面板)                │    │
│  │  useProcessWebSocket ←──── WebSocket ────────┐     │    │
│  └────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                        Backend                              │
│  ┌──────────────┐    ┌──────────────────────────────┐      │
│  │ api/process  │───▶│     core/processor.py        │      │
│  │  /start      │    │  ┌────────────────────────┐  │      │
│  │  /pause      │    │  │   ProcessEngine        │  │      │
│  │  /ws         │    │  │   - run_loop()         │  │      │
│  └──────────────┘    │  │   - process_one()      │  │      │
│                      │  │   - broadcast()        │  │      │
│                      │  └───────────┬────────────┘  │      │
│                      └──────────────┼───────────────┘      │
│                                     │                      │
│                      ┌──────────────┼───────────────┐      │
│                      │              ▼               │      │
│                      │  ┌─────────────────────┐    │      │
│                      │  │ FullTextExtractor   │    │      │
│                      │  └─────────────────────┘    │      │
│                      │              ▼               │      │
│                      │  ┌─────────────────────┐    │      │
│                      │  │  ArticleAnalyzer    │    │      │
│                      │  └─────────────────────┘    │      │
│                      └──────────────────────────────┘      │
│                                     │                      │
│                                     ▼                      │
│                      ┌──────────────────────────────┐      │
│                      │   Article (process_status)   │      │
│                      └──────────────────────────────┘      │
└─────────────────────────────────────────────────────────────┘
```

## 6. 迁移策略

1. 保留旧 API 但标记 deprecated
2. 旧 `fetch_status` 字段映射到新 `process_status`
3. 前端逐步切换到新组件

## 7. 下一步

等待确认后进入 Plan 阶段，制定详细实施清单。
