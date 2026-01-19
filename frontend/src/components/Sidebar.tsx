import { useQuery } from '@tanstack/react-query';
import { Folder, Rss, Star, Inbox, History, ThumbsUp, ThumbsDown } from 'lucide-react';
import { Link } from 'react-router-dom';
import { api } from '../api/client';
import { cn } from '../lib/utils';

// 最近浏览记录类型
interface RecentArticle {
  id: string;
  title: string;
  viewedAt: number;
}

// 获取最近浏览记录
function getRecentArticles(): RecentArticle[] {
  try {
    const data = localStorage.getItem('recentArticles');
    return data ? JSON.parse(data) : [];
  } catch {
    return [];
  }
}

interface SidebarProps {
  selectedFeed: string | null;
  selectedFilter: 'unread' | 'starred' | 'all';
  onSelectFeed: (feedId: string | null) => void;
  onSelectFilter: (filter: 'unread' | 'starred' | 'all') => void;
}

export function Sidebar({ 
  selectedFeed, 
  selectedFilter, 
  onSelectFeed, 
  onSelectFilter 
}: SidebarProps) {
  const { data: feedsData } = useQuery({
    queryKey: ['feeds'],
    queryFn: api.feeds.list,
  });

  const recentArticles = getRecentArticles().slice(0, 5);

  const filterItems = [
    { id: 'unread', label: '未读', icon: Inbox },
    { id: 'starred', label: '收藏', icon: Star },
    { id: 'all', label: '全部', icon: Rss },
  ] as const;

  return (
    <aside className="w-64 shrink-0 border-r bg-card">
      <div className="p-4">
        {/* Filters */}
        <div className="space-y-1 mb-6">
          {filterItems.map(({ id, label, icon: Icon }) => (
            <button
              key={id}
              onClick={() => {
                onSelectFilter(id);
                onSelectFeed(null);
              }}
              className={cn(
                "w-full flex items-center gap-2 px-3 py-2 rounded-md text-sm",
                "hover:bg-accent transition-colors",
                selectedFilter === id && !selectedFeed && "bg-accent font-medium"
              )}
            >
              <Icon className="h-4 w-4" />
              {label}
            </button>
          ))}
        </div>

        {/* Recent Articles */}
        {recentArticles.length > 0 && (
          <div className="mb-6">
            <div className="flex items-center gap-2 px-3 py-2 text-xs font-medium text-muted-foreground uppercase">
              <History className="h-3 w-3" />
              最近浏览
            </div>
            <div className="space-y-1">
              {recentArticles.map((article) => (
                <Link
                  key={article.id}
                  to={`/article/${encodeURIComponent(article.id)}`}
                  className="block w-full px-3 py-2 rounded-md text-sm hover:bg-accent transition-colors text-left truncate"
                  title={article.title}
                >
                  {article.title}
                </Link>
              ))}
            </div>
          </div>
        )}

        {/* Feeds by Category */}
        {feedsData?.categories && Object.entries(feedsData.categories).map(([category, feeds]) => (
          <div key={category} className="mb-4">
            <div className="flex items-center gap-2 px-3 py-2 text-xs font-medium text-muted-foreground uppercase">
              <Folder className="h-3 w-3" />
              {category}
            </div>
            <div className="space-y-1">
              {feeds.map((feed) => (
                <button
                  key={feed.id}
                  onClick={() => {
                    onSelectFeed(feed.id);
                    onSelectFilter('unread');
                  }}
                  className={cn(
                    "w-full flex items-center gap-2 px-3 py-2 rounded-md text-sm",
                    "hover:bg-accent transition-colors text-left",
                    selectedFeed === feed.id && "bg-accent font-medium"
                  )}
                >
                  {feed.icon_url ? (
                    <img src={feed.icon_url} alt="" className="w-4 h-4 rounded" />
                  ) : (
                    <Rss className="h-4 w-4 text-muted-foreground" />
                  )}
                  <span className="truncate flex-1">{feed.title}</span>
                  {(feed.likes_count > 0 || feed.dislikes_count > 0) && (
                    <span className="flex items-center gap-1 text-xs text-muted-foreground">
                      {feed.likes_count > 0 && (
                        <span className="flex items-center text-green-500">
                          <ThumbsUp className="h-3 w-3 mr-0.5" />
                          {feed.likes_count}
                        </span>
                      )}
                      {feed.dislikes_count > 0 && (
                        <span className="flex items-center text-red-500">
                          <ThumbsDown className="h-3 w-3 mr-0.5" />
                          {feed.dislikes_count}
                        </span>
                      )}
                    </span>
                  )}
                </button>
              ))}
            </div>
          </div>
        ))}
      </div>
    </aside>
  );
}



