import { useQuery } from '@tanstack/react-query';
import { ThumbsUp, ThumbsDown, Rss, TrendingUp, TrendingDown } from 'lucide-react';
import { cn } from '../lib/utils';

export function FeedStatsPage() {
  const { data, isLoading } = useQuery({
    queryKey: ['feeds-ratings'],
    queryFn: () => fetch(`${import.meta.env.VITE_API_BASE || 'http://localhost:8000'}/api/feeds/stats/ratings`).then(r => r.json()),
  });

  if (isLoading) {
    return (
      <div className="max-w-4xl mx-auto py-12 text-center text-muted-foreground">
        加载中...
      </div>
    );
  }

  const feeds = data?.feeds || [];
  const hasRatings = feeds.some((f: any) => f.likes_count > 0 || f.dislikes_count > 0);

  return (
    <div className="max-w-4xl mx-auto">
      <h1 className="text-2xl font-bold mb-6">订阅源质量统计</h1>
      
      {!hasRatings ? (
        <div className="text-center py-12 text-muted-foreground">
          <p>暂无评价数据</p>
          <p className="text-sm mt-2">在阅读文章时点击喜欢/不喜欢按钮来评价内容质量</p>
        </div>
      ) : (
        <div className="space-y-2">
          {feeds.map((feed: any) => {
            const total = feed.likes_count + feed.dislikes_count;
            const likePercent = total > 0 ? (feed.likes_count / total) * 100 : 0;
            
            return (
              <div
                key={feed.id}
                className="flex items-center gap-4 p-4 bg-card rounded-lg border"
              >
                {/* Icon */}
                {feed.icon_url ? (
                  <img src={feed.icon_url} alt="" className="w-8 h-8 rounded" />
                ) : (
                  <Rss className="w-8 h-8 text-muted-foreground" />
                )}

                {/* Title & Category */}
                <div className="flex-1 min-w-0">
                  <div className="font-medium truncate">{feed.title}</div>
                  {feed.category && (
                    <div className="text-xs text-muted-foreground">{feed.category}</div>
                  )}
                </div>

                {/* Progress Bar */}
                {total > 0 && (
                  <div className="w-32 h-2 bg-muted rounded-full overflow-hidden">
                    <div
                      className="h-full bg-green-500"
                      style={{ width: `${likePercent}%` }}
                    />
                  </div>
                )}

                {/* Stats */}
                <div className="flex items-center gap-4 text-sm">
                  <span className="flex items-center gap-1 text-green-500">
                    <ThumbsUp className="h-4 w-4" />
                    {feed.likes_count}
                  </span>
                  <span className="flex items-center gap-1 text-red-500">
                    <ThumbsDown className="h-4 w-4" />
                    {feed.dislikes_count}
                  </span>
                  <span className={cn(
                    "flex items-center gap-1 font-medium min-w-[3rem] justify-end",
                    feed.score > 0 ? "text-green-500" : feed.score < 0 ? "text-red-500" : "text-muted-foreground"
                  )}>
                    {feed.score > 0 ? (
                      <TrendingUp className="h-4 w-4" />
                    ) : feed.score < 0 ? (
                      <TrendingDown className="h-4 w-4" />
                    ) : null}
                    {feed.score > 0 ? '+' : ''}{feed.score}
                  </span>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
