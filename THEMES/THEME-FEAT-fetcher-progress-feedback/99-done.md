# 99-done.md - THEME 完成

## THEME: FEAT-fetcher-progress-feedback

---

## 完成时间
2026-01-15 14:15

## 最终结果摘要

成功实现了统一处理引擎，将原本分离的「全文抓取」和「AI 分析」合并为单一处理流程：

### 后端变更
1. **数据模型扩展**：Article 新增 `process_status`, `process_error`, `process_stage` 字段
2. **统一处理引擎** (`core/processor.py`)：
   - 状态机：synced → pending_fetch → fetching → pending_analysis → analyzing → done/failed
   - WebSocket 实时广播进度
   - 错误信息持久化到数据库
3. **Process API** (`api/process.py`)：
   - REST: /start, /pause, /resume, /stop, /stats, /progress, /failed, /retry
   - WebSocket: /ws 实时进度推送

### 前端变更
1. **API 客户端**：新增 `api.process` 模块和相关类型
2. **WebSocket Hook** (`useProcessWebSocket.ts`)：实时进度订阅
3. **ProcessPanel 组件**：统一处理面板，替代原有双 TaskCard
4. **FailedItemsModal 组件**：失败项查看和重试弹窗
5. **HomePage 更新**：使用新的 ProcessPanel

### 架构文档
- 更新 `architect.md`，添加统一处理引擎章节

## 是否达到目标
✅ 是

| 目标 | 状态 |
|------|------|
| 降低全文抓取失败率 | ✅ 错误信息持久化，便于排查 |
| 改善页面反馈 | ✅ WebSocket 实时进度，清晰显示当前状态 |
| 统一抓取+分析入口 | ✅ 单一 ProcessPanel，一键启动全流程 |

## 后续调整
如需进一步优化（如并发控制、重试策略等），请新建 THEME。
