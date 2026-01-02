import { Loader2, RefreshCw } from 'lucide-react';
import { cn } from '../lib/utils';
import type { TaskStats, TaskProgress } from '../api/client';

interface TaskCardProps {
  title: string;
  icon: React.ReactNode;
  stats: TaskStats | null;
  progress: TaskProgress | null;
  isRunning: boolean;
  colorClass: string;
  onStart: () => void;
  onRetry: () => void;
}

export function TaskCard({
  title,
  icon,
  stats,
  progress,
  isRunning,
  colorClass,
  onStart,
  onRetry,
}: TaskCardProps) {
  const hasFailures = stats && stats.failed > 0;
  const hasPending = stats && stats.pending > 0;
  const progressPercent = progress?.total 
    ? Math.round(((progress.completed || 0) + (progress.failed || 0)) / progress.total * 100) 
    : 0;

  return (
    <div className="flex-1 rounded-lg border bg-card p-4 shadow-sm">
      {/* 标题行 */}
      <div className="flex items-center gap-2 mb-3">
        <div className={cn("p-1.5 rounded-md", colorClass.replace('from-', 'bg-').split(' ')[0] + '/10')}>
          {icon}
        </div>
        <h3 className="font-medium">{title}</h3>
      </div>

      {/* 统计行 */}
      {stats && (
        <div className="space-y-1.5 text-sm mb-3">
          <div className="flex justify-between">
            <span className="text-muted-foreground">待处理</span>
            <span className={cn(stats.pending > 0 ? "text-amber-600 font-medium" : "text-muted-foreground")}>
              {stats.pending}
            </span>
          </div>
          <div className="flex justify-between">
            <span className="text-muted-foreground">已完成</span>
            <span className="text-green-600">{stats.completed}</span>
          </div>
          <div className="flex justify-between items-center">
            <span className="text-muted-foreground">失败</span>
            <div className="flex items-center gap-2">
              <span className={cn(stats.failed > 0 ? "text-red-500 font-medium" : "text-muted-foreground")}>
                {stats.failed}
              </span>
              {hasFailures && !isRunning && (
                <button
                  onClick={onRetry}
                  className="text-xs text-blue-500 hover:text-blue-600 flex items-center gap-1"
                >
                  <RefreshCw className="h-3 w-3" />
                  重试
                </button>
              )}
            </div>
          </div>
        </div>
      )}

      {/* 进度条 */}
      {isRunning && progress && progress.status === 'running' && (
        <div className="mb-3">
          <div className="flex justify-between text-xs text-muted-foreground mb-1">
            <span>进度</span>
            <span>{progress.completed || 0}/{progress.total || 0}</span>
          </div>
          <div className="h-2 bg-muted rounded-full overflow-hidden">
            <div 
              className={cn("h-full transition-all duration-300 bg-gradient-to-r", colorClass)}
              style={{ width: `${progressPercent}%` }}
            />
          </div>
          {progress.current_item && (
            <p className="text-xs text-muted-foreground mt-1 truncate">
              {progress.current_item}
            </p>
          )}
        </div>
      )}

      {/* 操作按钮 */}
      <button
        onClick={onStart}
        disabled={isRunning || !hasPending}
        className={cn(
          "w-full py-2 rounded-md text-sm font-medium transition-colors flex items-center justify-center gap-2",
          isRunning
            ? "bg-muted text-muted-foreground cursor-not-allowed"
            : hasPending
              ? cn("text-white bg-gradient-to-r", colorClass, "hover:opacity-90")
              : "bg-muted text-muted-foreground cursor-not-allowed"
        )}
      >
        {isRunning ? (
          <>
            <Loader2 className="h-4 w-4 animate-spin" />
            处理中...
          </>
        ) : hasPending ? (
          <>
            {icon}
            开始
          </>
        ) : (
          <>
            <span className="text-green-600">✓</span>
            已完成
          </>
        )}
      </button>
    </div>
  );
}


