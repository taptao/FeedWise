import { useEffect, useState } from 'react';
import { X, RefreshCw, ExternalLink, AlertTriangle } from 'lucide-react';
import { api } from '../api/client';
import type { FailedItem } from '../api/client';

interface FailedItemsModalProps {
  open: boolean;
  onClose: () => void;
  onRetry: () => void;
}

export function FailedItemsModal({ open, onClose, onRetry }: FailedItemsModalProps) {
  const [items, setItems] = useState<FailedItem[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(false);
  const limit = 10;

  useEffect(() => {
    if (open) {
      loadItems();
    }
  }, [open, page]);

  const loadItems = async () => {
    setLoading(true);
    try {
      const data = await api.process.failed(page, limit);
      setItems(data.items);
      setTotal(data.total);
    } catch (e) {
      console.error('加载失败列表失败:', e);
    } finally {
      setLoading(false);
    }
  };

  if (!open) return null;

  const totalPages = Math.ceil(total / limit);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* 背景遮罩 */}
      <div
        className="absolute inset-0 bg-black/50"
        onClick={onClose}
      />

      {/* 弹窗内容 */}
      <div className="relative bg-white dark:bg-gray-800 rounded-lg shadow-xl w-full max-w-2xl max-h-[80vh] flex flex-col">
        {/* 标题栏 */}
        <div className="flex items-center justify-between p-4 border-b border-gray-200 dark:border-gray-700">
          <div className="flex items-center gap-2">
            <AlertTriangle className="w-5 h-5 text-red-500" />
            <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
              失败项目 ({total})
            </h2>
          </div>
          <button
            onClick={onClose}
            className="p-1 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* 列表内容 */}
        <div className="flex-1 overflow-y-auto p-4">
          {loading ? (
            <div className="flex items-center justify-center py-8">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600" />
            </div>
          ) : items.length === 0 ? (
            <div className="text-center py-8 text-gray-500 dark:text-gray-400">
              没有失败的项目
            </div>
          ) : (
            <div className="space-y-3">
              {items.map((item) => (
                <div
                  key={item.article_id}
                  className="p-3 bg-gray-50 dark:bg-gray-700 rounded-lg"
                >
                  <div className="flex items-start justify-between gap-2">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <h4 className="font-medium text-gray-900 dark:text-white truncate">
                          {item.title}
                        </h4>
                        {item.url && (
                          <a
                            href={item.url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-gray-400 hover:text-blue-500"
                          >
                            <ExternalLink className="w-4 h-4" />
                          </a>
                        )}
                      </div>
                      <div className="text-sm text-gray-500 dark:text-gray-400 mt-1">
                        来源: {item.feed_title}
                        {item.stage && (
                          <span className="ml-2">
                            阶段: <span className="text-yellow-600">{item.stage === 'fetch' ? '抓取' : '分析'}</span>
                          </span>
                        )}
                      </div>
                    </div>
                  </div>
                  <div className="mt-2 text-sm text-red-600 dark:text-red-400 bg-red-50 dark:bg-red-900/20 p-2 rounded">
                    {item.error}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* 分页和操作 */}
        <div className="flex items-center justify-between p-4 border-t border-gray-200 dark:border-gray-700">
          {/* 分页 */}
          <div className="flex items-center gap-2">
            <button
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              disabled={page === 1 || loading}
              className="px-3 py-1 text-sm border border-gray-300 dark:border-gray-600 rounded hover:bg-gray-100 dark:hover:bg-gray-700 disabled:opacity-50"
            >
              上一页
            </button>
            <span className="text-sm text-gray-600 dark:text-gray-400">
              {page} / {totalPages || 1}
            </span>
            <button
              onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
              disabled={page >= totalPages || loading}
              className="px-3 py-1 text-sm border border-gray-300 dark:border-gray-600 rounded hover:bg-gray-100 dark:hover:bg-gray-700 disabled:opacity-50"
            >
              下一页
            </button>
          </div>

          {/* 重试按钮 */}
          <button
            onClick={onRetry}
            disabled={total === 0 || loading}
            className="flex items-center gap-1 px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50"
          >
            <RefreshCw className="w-4 h-4" />
            全部重试
          </button>
        </div>
      </div>
    </div>
  );
}
