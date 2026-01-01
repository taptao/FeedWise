import { useState, useEffect } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { ArrowUpDown, Sparkles, Loader2 } from 'lucide-react';
import { api } from '../api/client';
import { ArticleCard } from '../components/ArticleCard';
import { Sidebar } from '../components/Sidebar';
import { cn } from '../lib/utils';

type SortOption = 'value' | 'date' | 'feed';
type FilterOption = 'unread' | 'starred' | 'all';

export function HomePage() {
  const [sort, setSort] = useState<SortOption>('value');
  const [filter, setFilter] = useState<FilterOption>('unread');
  const [selectedFeed, setSelectedFeed] = useState<string | null>(null);
  const [page, setPage] = useState(1);
  const [batchAnalyzing, setBatchAnalyzing] = useState(false);
  const [batchProgress, setBatchProgress] = useState<{ total: number; completed: number } | null>(null);
  const queryClient = useQueryClient();

  const { data, isLoading, error } = useQuery({
    queryKey: ['articles', { sort, filter, feed_id: selectedFeed, page }],
    queryFn: () => api.articles.list({ sort, filter, feed_id: selectedFeed || undefined, page, limit: 20 }),
  });

  // 批量分析
  const handleBatchAnalysis = async () => {
    if (batchAnalyzing) return;
    
    setBatchAnalyzing(true);
    setBatchProgress(null);
    
    try {
      const result = await api.analysis.batch(20);
      if (result.count === 0) {
        alert('没有需要分析的文章');
        setBatchAnalyzing(false);
        return;
      }
      
      setBatchProgress({ total: result.count, completed: 0 });
      
      // 轮询检查进度
      const checkProgress = async () => {
        const status = await api.analysis.batchStatus(result.batch_id);
        setBatchProgress({ total: status.total, completed: status.completed });
        
        if (status.status === 'completed') {
          setBatchAnalyzing(false);
          setBatchProgress(null);
          // 刷新文章列表
          queryClient.invalidateQueries({ queryKey: ['articles'] });
        } else {
          setTimeout(checkProgress, 2000);
        }
      };
      
      setTimeout(checkProgress, 2000);
    } catch (err) {
      console.error('Batch analysis failed:', err);
      setBatchAnalyzing(false);
      setBatchProgress(null);
    }
  };

  const sortOptions: { value: SortOption; label: string }[] = [
    { value: 'value', label: '按价值' },
    { value: 'date', label: '按时间' },
    { value: 'feed', label: '按来源' },
  ];

  return (
    <div className="flex gap-6 -mx-4 -mt-6">
      {/* Sidebar */}
      <Sidebar
        selectedFeed={selectedFeed}
        selectedFilter={filter}
        onSelectFeed={setSelectedFeed}
        onSelectFilter={setFilter}
      />

      {/* Main Content */}
      <div className="flex-1 py-6 pr-4">
        {/* Toolbar */}
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-2xl font-bold">
              {selectedFeed ? '订阅文章' : filter === 'unread' ? '未读文章' : filter === 'starred' ? '收藏文章' : '所有文章'}
            </h1>
            {data && (
              <p className="text-sm text-muted-foreground">
                共 {data.total} 篇文章
              </p>
            )}
          </div>

          {/* Batch Analysis & Sort */}
          <div className="flex items-center gap-4">
            {/* Batch Analysis Button */}
            <button
              onClick={handleBatchAnalysis}
              disabled={batchAnalyzing}
              className={cn(
                "flex items-center gap-2 px-4 py-2 rounded-md text-sm font-medium transition-colors",
                batchAnalyzing
                  ? "bg-muted text-muted-foreground cursor-not-allowed"
                  : "bg-gradient-to-r from-purple-500 to-pink-500 text-white hover:from-purple-600 hover:to-pink-600"
              )}
            >
              {batchAnalyzing ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  {batchProgress
                    ? `分析中 ${batchProgress.completed}/${batchProgress.total}`
                    : '启动中...'}
                </>
              ) : (
                <>
                  <Sparkles className="h-4 w-4" />
                  AI 批量分析
                </>
              )}
            </button>

            {/* Sort Options */}
            <div className="flex items-center gap-2">
              <ArrowUpDown className="h-4 w-4 text-muted-foreground" />
              <div className="flex rounded-md border">
                {sortOptions.map((option) => (
                  <button
                    key={option.value}
                    onClick={() => setSort(option.value)}
                    className={cn(
                      "px-3 py-1.5 text-sm transition-colors",
                      "first:rounded-l-md last:rounded-r-md",
                      sort === option.value
                        ? "bg-primary text-primary-foreground"
                        : "hover:bg-accent"
                    )}
                  >
                    {option.label}
                  </button>
                ))}
              </div>
            </div>
          </div>
        </div>

        {/* Loading State */}
        {isLoading && (
          <div className="text-center py-12 text-muted-foreground">
            加载中...
          </div>
        )}

        {/* Error State */}
        {error && (
          <div className="text-center py-12 text-destructive">
            加载失败：{(error as Error).message}
          </div>
        )}

        {/* Empty State */}
        {data && data.items.length === 0 && (
          <div className="text-center py-12 text-muted-foreground">
            <p className="text-lg">暂无文章</p>
            <p className="text-sm mt-2">点击"同步"按钮获取最新内容</p>
          </div>
        )}

        {/* Article Grid */}
        {data && data.items.length > 0 && (
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            {data.items.map((article) => (
              <ArticleCard key={article.id} article={article} />
            ))}
          </div>
        )}

        {/* Pagination */}
        {data && data.total > 20 && (
          <div className="flex items-center justify-center gap-2 mt-8">
            <button
              onClick={() => setPage(Math.max(1, page - 1))}
              disabled={page === 1}
              className="px-4 py-2 rounded-md border disabled:opacity-50"
            >
              上一页
            </button>
            <span className="text-sm text-muted-foreground">
              第 {page} 页 / 共 {Math.ceil(data.total / 20)} 页
            </span>
            <button
              onClick={() => setPage(page + 1)}
              disabled={page * 20 >= data.total}
              className="px-4 py-2 rounded-md border disabled:opacity-50"
            >
              下一页
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

