import { useQuery } from '@tanstack/react-query';
import { Folder, Rss, Star, Inbox } from 'lucide-react';
import { api } from '../api/client';
import { cn } from '../lib/utils';

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
                  <span className="truncate">{feed.title}</span>
                </button>
              ))}
            </div>
          </div>
        ))}
      </div>
    </aside>
  );
}

