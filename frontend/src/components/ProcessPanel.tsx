import { useState, useCallback } from 'react';
import { Play, Pause, Square, AlertCircle, CheckCircle, Loader2 } from 'lucide-react';
import { api } from '../api/client';
import type { ProcessStats } from '../api/client';
import { useProcessWebSocket } from '../hooks/useProcessWebSocket';
import { FailedItemsModal } from './FailedItemsModal';

interface ProcessPanelProps {
  onRefresh?: () => void;
}

export function ProcessPanel({ onRefresh }: ProcessPanelProps) {
  const [stats, setStats] = useState<ProcessStats | null>(null);
  const [loading, setLoading] = useState(false);
  const [showFailedModal, setShowFailedModal] = useState(false);

  const { connected, progress } = useProcessWebSocket({
    onCompleted: (total, success, failed) => {
      console.log(`处理完成: 总计 ${total}, 成功 ${success}, 失败 ${failed}`);
      refreshStats();
      onRefresh?.();
    },
    onItemFailed: (_articleId, title, stage, error) => {
      console.warn(`处理失败: ${title} (${stage}): ${error}`);
    },
  });

  const refreshStats = useCallback(async () => {
    try {
      const data = await api.process.stats();
      setStats(data);
    } catch (e) {
      console.error('获取统计失败:', e);
    }
  }, []);

  // 初始加载
  useState(() => {
    refreshStats();
  });

  const handleStart = async () => {
    setLoading(true);
    try {
      await api.process.start();
      await refreshStats();
    } catch (e) {
      console.error('启动失败:', e);
    } finally {
      setLoading(false);
    }
  };

  const handlePause = async () => {
    setLoading(true);
    try {
      await api.process.pause();
    } catch (e) {
      console.error('暂停失败:', e);
    } finally {
      setLoading(false);
    }
  };

  const handleResume = async () => {
    setLoading(true);
    try {
      await api.process.resume();
    } catch (e) {
      console.error('恢复失败:', e);
    } finally {
      setLoading(false);
    }
  };

  const handleStop = async () => {
    setLoading(true);
    try {
      await api.process.stop();
      await refreshStats();
    } catch (e) {
      console.error('停止失败:', e);
    } finally {
      setLoading(false);
    }
  };

  const handleRetry = async () => {
    setLoading(true);
    try {
      await api.process.retry();
      await refreshStats();
      setShowFailedModal(false);
    } catch (e) {
      console.error('重试失败:', e);
    } finally {
      setLoading(false);
    }
  };

  const isRunning = progress.status === 'running';
  const isPaused = progress.status === 'paused';
  const isIdle = progress.status === 'idle';

  const progressPercent = progress.total > 0
    ? Math.round(((progress.completed + progress.failed) / progress.total) * 100)
    : 0;

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-4">
      {/* 标题和状态 */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
            统一处理
          </h3>
          {connected ? (
            <span className="flex items-center gap-1 text-xs text-green-600 dark:text-green-400">
              <span className="w-2 h-2 bg-green-500 rounded-full animate-pulse" />
              已连接
            </span>
          ) : (
            <span className="flex items-center gap-1 text-xs text-gray-400">
              <span className="w-2 h-2 bg-gray-400 rounded-full" />
              未连接
            </span>
          )}
        </div>

        {/* 控制按钮 */}
        <div className="flex items-center gap-2">
          {isIdle && (
            <button
              onClick={handleStart}
              disabled={loading || (stats?.pending === 0)}
              className="flex items-center gap-1 px-3 py-1.5 text-sm bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4" />}
              开始处理
            </button>
          )}

          {isRunning && (
            <>
              <button
                onClick={handlePause}
                disabled={loading}
                className="flex items-center gap-1 px-3 py-1.5 text-sm bg-yellow-600 text-white rounded-md hover:bg-yellow-700 disabled:opacity-50"
              >
                <Pause className="w-4 h-4" />
                暂停
              </button>
              <button
                onClick={handleStop}
                disabled={loading}
                className="flex items-center gap-1 px-3 py-1.5 text-sm bg-red-600 text-white rounded-md hover:bg-red-700 disabled:opacity-50"
              >
                <Square className="w-4 h-4" />
                停止
              </button>
            </>
          )}

          {isPaused && (
            <>
              <button
                onClick={handleResume}
                disabled={loading}
                className="flex items-center gap-1 px-3 py-1.5 text-sm bg-green-600 text-white rounded-md hover:bg-green-700 disabled:opacity-50"
              >
                <Play className="w-4 h-4" />
                继续
              </button>
              <button
                onClick={handleStop}
                disabled={loading}
                className="flex items-center gap-1 px-3 py-1.5 text-sm bg-red-600 text-white rounded-md hover:bg-red-700 disabled:opacity-50"
              >
                <Square className="w-4 h-4" />
                停止
              </button>
            </>
          )}
        </div>
      </div>

      {/* 进度条 (运行时显示) */}
      {(isRunning || isPaused) && (
        <div className="mb-4">
          <div className="flex items-center justify-between text-sm text-gray-600 dark:text-gray-400 mb-1">
            <span>
              {progress.current_stage === 'fetch' ? '抓取中' : '分析中'}
              {progress.current_article && `: ${progress.current_article}`}
            </span>
            <span>{progressPercent}%</span>
          </div>
          <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2">
            <div
              className={`h-2 rounded-full transition-all duration-300 ${
                isPaused ? 'bg-yellow-500' : 'bg-blue-600'
              }`}
              style={{ width: `${progressPercent}%` }}
            />
          </div>
          <div className="flex items-center justify-between text-xs text-gray-500 dark:text-gray-400 mt-1">
            <span>已完成: {progress.completed}</span>
            <span>失败: {progress.failed}</span>
            <span>总计: {progress.total}</span>
          </div>
        </div>
      )}

      {/* 统计信息 */}
      {stats && isIdle && (
        <div className="grid grid-cols-4 gap-4">
          <div className="text-center p-3 bg-gray-50 dark:bg-gray-700 rounded-lg">
            <div className="text-2xl font-bold text-blue-600 dark:text-blue-400">
              {stats.pending}
            </div>
            <div className="text-xs text-gray-500 dark:text-gray-400">待处理</div>
          </div>
          <div className="text-center p-3 bg-gray-50 dark:bg-gray-700 rounded-lg">
            <div className="text-2xl font-bold text-yellow-600 dark:text-yellow-400">
              {stats.processing}
            </div>
            <div className="text-xs text-gray-500 dark:text-gray-400">处理中</div>
          </div>
          <div className="text-center p-3 bg-gray-50 dark:bg-gray-700 rounded-lg">
            <div className="flex items-center justify-center gap-1">
              <CheckCircle className="w-5 h-5 text-green-500" />
              <span className="text-2xl font-bold text-green-600 dark:text-green-400">
                {stats.done}
              </span>
            </div>
            <div className="text-xs text-gray-500 dark:text-gray-400">已完成</div>
          </div>
          <div
            className="text-center p-3 bg-gray-50 dark:bg-gray-700 rounded-lg cursor-pointer hover:bg-gray-100 dark:hover:bg-gray-600"
            onClick={() => stats.failed > 0 && setShowFailedModal(true)}
          >
            <div className="flex items-center justify-center gap-1">
              <AlertCircle className="w-5 h-5 text-red-500" />
              <span className="text-2xl font-bold text-red-600 dark:text-red-400">
                {stats.failed}
              </span>
            </div>
            <div className="text-xs text-gray-500 dark:text-gray-400">
              失败 {stats.failed > 0 && '(点击查看)'}
            </div>
          </div>
        </div>
      )}

      {/* 失败项弹窗 */}
      <FailedItemsModal
        open={showFailedModal}
        onClose={() => setShowFailedModal(false)}
        onRetry={handleRetry}
      />
    </div>
  );
}
