# Plan: FEAT-fetcher-progress-feedback

## 实施清单

### 阶段 1：后端模型扩展

#### 1.1 修改 Article 模型
- **文件**: `src/feedwise/models/article.py`
- **操作**: 新增字段
  ```python
  process_status: str = Field(default="synced", description="处理状态: synced|pending_fetch|fetching|pending_analysis|analyzing|done|failed")
  process_error: str | None = Field(default=None, description="处理错误信息")
  process_stage: str | None = Field(default=None, description="失败阶段: fetch|analysis")
  ```

#### 1.2 数据迁移脚本
- **文件**: `src/feedwise/models/database.py`
- **操作**: 在 `init_db()` 中添加迁移逻辑，将旧 `fetch_status` 映射到新 `process_status`

---

### 阶段 2：后端处理引擎

#### 2.1 创建 ProcessEngine
- **文件**: `src/feedwise/core/processor.py` (新建)
- **类**: `ProcessEngine`
- **方法**:
  - `__init__(self)`: 初始化，创建 extractor 和 analyzer
  - `async start(self)`: 启动处理循环
  - `pause(self)`: 暂停处理
  - `async process_one(self, article: Article)`: 处理单篇文章
  - `async _do_fetch(self, article: Article)`: 执行抓取
  - `async _do_analysis(self, article: Article)`: 执行分析
  - `_get_next_status(self, current: str) -> str`: 状态转换
- **全局状态**:
  - `_engine: ProcessEngine | None`
  - `_ws_connections: set[WebSocket]`
  - `async broadcast(message: dict)`: 广播消息

#### 2.2 创建 Process API
- **文件**: `src/feedwise/api/process.py` (新建)
- **路由**:
  - `POST /api/process/start`: 启动处理
  - `POST /api/process/pause`: 暂停处理
  - `GET /api/process/stats`: 获取统计
  - `GET /api/process/ws`: WebSocket 端点
  - `POST /api/process/retry`: 重试失败项
  - `GET /api/process/failed`: 获取失败列表

#### 2.3 注册路由
- **文件**: `src/feedwise/main.py`
- **操作**: 添加 `from feedwise.api import process` 并注册 router

---

### 阶段 3：前端组件

#### 3.1 创建 WebSocket Hook
- **文件**: `frontend/src/hooks/useProcessWebSocket.ts` (新建)
- **功能**:
  - 连接 `/api/process/ws`
  - 自动重连
  - 解析消息更新状态
  - 返回 `{ stats, progress, isConnected }`

#### 3.2 创建 ProcessPanel 组件
- **文件**: `frontend/src/components/ProcessPanel.tsx` (新建)
- **功能**:
  - 显示统计数据 (待处理/处理中/已完成/失败)
  - 开始/暂停按钮
  - 进度条 + 当前处理项
  - 失败项查看/重试

#### 3.3 创建失败详情弹窗
- **文件**: `frontend/src/components/FailedItemsModal.tsx` (新建)
- **功能**:
  - 列表展示失败文章
  - 显示错误原因和失败阶段
  - 重试按钮

#### 3.4 更新 API Client
- **文件**: `frontend/src/api/client.ts`
- **操作**: 添加 `api.process` 命名空间

#### 3.5 更新 HomePage
- **文件**: `frontend/src/pages/HomePage.tsx`
- **操作**:
  - 移除双 TaskCard
  - 引入 ProcessPanel
  - 移除旧的 fetch/analysis 状态管理

---

### 阶段 4：清理与测试

#### 4.1 标记废弃 API
- **文件**: `src/feedwise/api/fetch.py`
- **操作**: 添加 deprecated 注释，保留兼容

#### 4.2 运行检查
- `ruff format src/`
- `ruff check src/`
- `pyright src/`

#### 4.3 前端检查
- `cd frontend && npm run build`

---

## 文件变更汇总

| 操作 | 文件 |
|------|------|
| 修改 | `src/feedwise/models/article.py` |
| 修改 | `src/feedwise/models/database.py` |
| 新建 | `src/feedwise/core/processor.py` |
| 新建 | `src/feedwise/api/process.py` |
| 修改 | `src/feedwise/main.py` |
| 修改 | `src/feedwise/api/fetch.py` |
| 新建 | `frontend/src/hooks/useProcessWebSocket.ts` |
| 新建 | `frontend/src/components/ProcessPanel.tsx` |
| 新建 | `frontend/src/components/FailedItemsModal.tsx` |
| 修改 | `frontend/src/api/client.ts` |
| 修改 | `frontend/src/pages/HomePage.tsx` |

---

## 执行顺序

1. [1.1] 修改 Article 模型
2. [1.2] 添加数据迁移逻辑
3. [2.1] 创建 ProcessEngine
4. [2.2] 创建 Process API
5. [2.3] 注册路由到 main.py
6. [4.2] 运行后端检查 (ruff + pyright)
7. [3.4] 更新 API Client
8. [3.1] 创建 WebSocket Hook
9. [3.2] 创建 ProcessPanel
10. [3.3] 创建 FailedItemsModal
11. [3.5] 更新 HomePage
12. [4.1] 标记废弃 API
13. [4.3] 运行前端检查

---

## 下一步

等待用户确认计划后进入 Execute 阶段。
