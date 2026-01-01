import { Outlet, Link, useLocation } from 'react-router-dom';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { RefreshCw, Settings, Rss } from 'lucide-react';
import { api } from '../api/client';
import { cn } from '../lib/utils';

export function Layout() {
  const location = useLocation();
  const queryClient = useQueryClient();

  const syncMutation = useMutation({
    mutationFn: api.sync.trigger,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['articles'] });
      queryClient.invalidateQueries({ queryKey: ['feeds'] });
    },
  });

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="sticky top-0 z-50 border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
        <div className="container flex h-14 items-center justify-between px-4">
          <Link to="/" className="flex items-center gap-2 font-semibold">
            <Rss className="h-5 w-5 text-primary" />
            <span className="text-lg">FeedWise</span>
          </Link>

          <div className="flex items-center gap-2">
            <button
              onClick={() => syncMutation.mutate()}
              disabled={syncMutation.isPending}
              className={cn(
                "inline-flex items-center gap-2 rounded-md px-3 py-2 text-sm font-medium",
                "bg-primary text-primary-foreground hover:bg-primary/90",
                "disabled:opacity-50 disabled:cursor-not-allowed",
                "transition-colors"
              )}
            >
              <RefreshCw className={cn("h-4 w-4", syncMutation.isPending && "animate-spin")} />
              {syncMutation.isPending ? "同步中..." : "同步"}
            </button>

            <Link
              to="/settings"
              className={cn(
                "inline-flex items-center justify-center rounded-md p-2",
                "hover:bg-accent hover:text-accent-foreground",
                "transition-colors",
                location.pathname === '/settings' && "bg-accent"
              )}
            >
              <Settings className="h-5 w-5" />
            </Link>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="container mx-auto px-4 py-6">
        <Outlet />
      </main>
    </div>
  );
}

