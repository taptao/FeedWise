import { useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { ArrowUpDown, Tag, X } from 'lucide-react';
import { api } from '../api/client';
import { ArticleCard } from '../components/ArticleCard';
import { Sidebar } from '../components/Sidebar';
import { ProcessPanel } from '../components/ProcessPanel';
import { cn } from '../lib/utils';

type SortOption = 'value' | 'date' | 'feed';
type FilterOption = 'unread' | 'starred' | 'all';

export function HomePage() {
  const [sort, setSort] = useState<SortOption>('value');
  const [filter, setFilter] = useState<FilterOption>('unread');
  const [selectedFeed, setSelectedFeed] = useState<string | null>(null);
  const [selectedTag, setSelectedTag] = useState<string | null>(null);
  const [page, setPage] = useState(1);
  const queryClient = useQueryClient();

  const { data, isLoading, error } = useQuery({
    queryKey: ['articles', { sort, filter, feed_id: selectedFeed, tag: selectedTag, page }],
    queryFn: () => api.articles.list({ sort, filter, feed_id: selectedFeed || undefined, tag: selectedTag || undefined, page, limit: 20 }),
  });

  const { data: tagsData } = useQuery({
    queryKey: ['tags'],
    queryFn: () => api.articles.tags(),
  });

  const handleRefresh = () => {
    queryClient.invalidateQueries({ queryKey: ['articles'] });
    queryClient.invalidateQueries({ queryKey: ['tags'] });
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
        {/* Process Panel (新的统一处理面板) */}
        <div className="mb-6">
          <ProcessPanel onRefresh={handleRefresh} />
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

        {/* Tag Filter */}
        {tagsData && tagsData.tags.length > 0 && (
          <div className="mb-4 flex flex-wrap items-center gap-2">
            <Tag className="h-4 w-4 text-muted-foreground" />
            {selectedTag && (
              <button
                onClick={() => setSelectedTag(null)}
                className="flex items-center gap-1 px-2 py-1 text-xs bg-primary text-primary-foreground rounded-full"
              >
                {selectedTag}
                <X className="h-3 w-3" />
              </button>
            )}
            {tagsData.tags.slice(0, 15).map((tag) => (
              tag.name !== selectedTag && (
                <button
                  key={tag.name}
                  onClick={() => setSelectedTag(tag.name)}
                  className="px-2 py-1 text-xs bg-accent hover:bg-accent/80 rounded-full transition-colors"
                >
                  {tag.name} ({tag.count})
                </button>
              )
            ))}
          </div>
        )}

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
