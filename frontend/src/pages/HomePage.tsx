import { useState, useEffect } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { ArrowUpDown, Sparkles, Download } from 'lucide-react';
import { api } from '../api/client';
import type { TaskStats, TaskProgress } from '../api/client';
import { ArticleCard } from '../components/ArticleCard';
import { Sidebar } from '../components/Sidebar';
import { TaskCard } from '../components/TaskCard';
import { cn } from '../lib/utils';

type SortOption = 'value' | 'date' | 'feed';
type FilterOption = 'unread' | 'starred' | 'all';

export function HomePage() {
  const [sort, setSort] = useState<SortOption>('value');
  const [filter, setFilter] = useState<FilterOption>('unread');
  const [selectedFeed, setSelectedFeed] = useState<string | null>(null);
  const [page, setPage] = useState(1);
  const queryClient = useQueryClient();

  // 抓取状态
  const [fetchStats, setFetchStats] = useState<TaskStats | null>(null);
  const [fetchProgress, setFetchProgress] = useState<TaskProgress | null>(null);
  const [isFetching, setIsFetching] = useState(false);

  // 分析状态
  const [analysisStats, setAnalysisStats] = useState<TaskStats | null>(null);
  const [analysisProgress, setAnalysisProgress] = useState<TaskProgress | null>(null);
  const [isAnalyzing, setIsAnalyzing] = useState(false);

  const { data, isLoading, error } = useQuery({
    queryKey: ['articles', { sort, filter, feed_id: selectedFeed, page }],
    queryFn: () => api.articles.list({ sort, filter, feed_id: selectedFeed || undefined, page, limit: 20 }),
  });

  // 初始加载统计
  useEffect(() => {
    const loadStats = async () => {
      try {
        const [fetchStatsData, analysisStatsData] = await Promise.all([
          api.fetch.stats(),
          api.analysis.stats(),
        ]);
        setFetchStats(fetchStatsData);
        setAnalysisStats(analysisStatsData);
      } catch (err) {
        console.error('Failed to load stats:', err);
      }
    };
    loadStats();
  }, []);

  // 刷新统计
  const refreshStats = async () => {
    try {
      const [fetchStatsData, analysisStatsData] = await Promise.all([
        api.fetch.stats(),
        api.analysis.stats(),
      ]);
      setFetchStats(fetchStatsData);
      setAnalysisStats(analysisStatsData);
    } catch (err) {
      console.error('Failed to refresh stats:', err);
    }
  };

  // 抓取处理
  const handleFetchBatch = async () => {
    if (isFetching) return;
    
    setIsFetching(true);
    setFetchProgress(null);
    
    try {
      const result = await api.fetch.batch(20);
      if (result.count === 0) {
        setIsFetching(false);
        return;
      }
      
      // 轮询检查进度
      const checkProgress = async () => {
        try {
          const progress = await api.fetch.progress();
          setFetchProgress(progress);
          
          if (progress.status === 'idle') {
            setIsFetching(false);
            setFetchProgress(null);
            refreshStats();
            queryClient.invalidateQueries({ queryKey: ['articles'] });
          } else {
            setTimeout(checkProgress, 2000);
          }
        } catch {
          setIsFetching(false);
          setFetchProgress(null);
        }
      };
      
      setTimeout(checkProgress, 1000);
    } catch (err) {
      console.error('Batch fetch failed:', err);
      setIsFetching(false);
      setFetchProgress(null);
    }
  };

  // 抓取重试
  const handleFetchRetry = async () => {
    if (isFetching) return;
    
    try {
      await api.fetch.retry();
      handleFetchBatch();
    } catch (err) {
      console.error('Fetch retry failed:', err);
    }
  };

  // 分析处理
  const handleBatchAnalysis = async () => {
    if (isAnalyzing) return;
    
    setIsAnalyzing(true);
    setAnalysisProgress(null);
    
    try {
      const result = await api.analysis.batch(20);
      if (result.count === 0) {
        setIsAnalyzing(false);
        return;
      }
      
      setAnalysisProgress({ status: 'running', total: result.count, completed: 0 });
      
      // 轮询检查进度
      const checkProgress = async () => {
        try {
          const status = await api.analysis.batchStatus(result.batch_id);
          setAnalysisProgress({ 
            status: status.status as 'idle' | 'running', 
            total: status.total, 
            completed: status.completed,
            failed: status.failed,
          });
          
          if (status.status === 'completed') {
            setIsAnalyzing(false);
            setAnalysisProgress(null);
            refreshStats();
            queryClient.invalidateQueries({ queryKey: ['articles'] });
          } else {
            setTimeout(checkProgress, 2000);
          }
        } catch {
          setIsAnalyzing(false);
          setAnalysisProgress(null);
        }
      };
      
      setTimeout(checkProgress, 2000);
    } catch (err) {
      console.error('Batch analysis failed:', err);
      setIsAnalyzing(false);
      setAnalysisProgress(null);
    }
  };

  // 分析重试
  const handleAnalysisRetry = async () => {
    if (isAnalyzing) return;
    
    try {
      await api.analysis.retry();
      handleBatchAnalysis();
    } catch (err) {
      console.error('Analysis retry failed:', err);
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
        {/* Task Cards */}
        <div className="flex gap-4 mb-6">
          <TaskCard
            title="全文抓取"
            icon={<Download className="h-4 w-4" />}
            stats={fetchStats}
            progress={fetchProgress}
            isRunning={isFetching}
            colorClass="from-blue-500 to-cyan-500"
            onStart={handleFetchBatch}
            onRetry={handleFetchRetry}
          />
          <TaskCard
            title="AI 分析"
            icon={<Sparkles className="h-4 w-4" />}
            stats={analysisStats}
            progress={analysisProgress}
            isRunning={isAnalyzing}
            colorClass="from-purple-500 to-pink-500"
            onStart={handleBatchAnalysis}
            onRetry={handleAnalysisRetry}
          />
        </div>

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
