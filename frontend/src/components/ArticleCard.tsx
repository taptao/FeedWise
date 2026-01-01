import { Link } from 'react-router-dom';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { Star, Clock, ExternalLink, AlertCircle } from 'lucide-react';
import { api, type Article } from '../api/client';
import { cn, formatDate, getScoreColor, getScoreBg } from '../lib/utils';

interface ArticleCardProps {
  article: Article;
}

export function ArticleCard({ article }: ArticleCardProps) {
  const queryClient = useQueryClient();

  const starMutation = useMutation({
    mutationFn: () => api.articles.toggleStar(article.id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['articles'] });
    },
  });

  const score = article.analysis?.value_score;
  const hasIncompleteContent = article.fetch_status === 'failed' || 
    (article.content_source === 'feed' && article.fetch_status !== 'skipped');

  return (
    <div className={cn(
      "group relative rounded-lg border bg-card p-4",
      "hover:shadow-md transition-shadow",
      article.is_read && "opacity-60"
    )}>
      {/* Score Badge */}
      {score !== null && score !== undefined && (
        <div className={cn(
          "absolute -top-2 -right-2 px-2 py-1 rounded-full text-xs font-bold",
          getScoreBg(score),
          getScoreColor(score)
        )}>
          {score.toFixed(1)}
        </div>
      )}

      {/* Header */}
      <div className="flex items-start gap-3 mb-2">
        {article.feed?.icon_url ? (
          <img 
            src={article.feed.icon_url} 
            alt="" 
            className="w-5 h-5 rounded"
          />
        ) : (
          <div className="w-5 h-5 rounded bg-muted" />
        )}
        
        <div className="flex-1 min-w-0">
          <Link 
            to={`/article/${encodeURIComponent(article.id)}`}
            className="block"
          >
            <h3 className="font-medium text-foreground line-clamp-2 group-hover:text-primary transition-colors">
              {article.title}
            </h3>
          </Link>
          
          <div className="flex items-center gap-2 mt-1 text-xs text-muted-foreground">
            <span>{article.feed?.title || '未知来源'}</span>
            {article.published_at && (
              <>
                <span>·</span>
                <span>{formatDate(article.published_at)}</span>
              </>
            )}
            {article.analysis?.reading_time && (
              <>
                <span>·</span>
                <span className="flex items-center gap-1">
                  <Clock className="h-3 w-3" />
                  {article.analysis.reading_time}分钟
                </span>
              </>
            )}
          </div>
        </div>

        {/* Star Button */}
        <button
          onClick={(e) => {
            e.preventDefault();
            starMutation.mutate();
          }}
          className={cn(
            "p-1 rounded hover:bg-accent transition-colors",
            article.is_starred ? "text-yellow-500" : "text-muted-foreground"
          )}
        >
          <Star className={cn("h-4 w-4", article.is_starred && "fill-current")} />
        </button>
      </div>

      {/* Summary */}
      {article.analysis?.summary && (
        <p className="text-sm text-muted-foreground line-clamp-2 mb-3">
          {article.analysis.summary}
        </p>
      )}

      {/* Incomplete Content Warning */}
      {hasIncompleteContent && (
        <div className="flex items-center gap-1 text-xs text-yellow-600 mb-3">
          <AlertCircle className="h-3 w-3" />
          <span>内容可能不完整</span>
        </div>
      )}

      {/* Tags */}
      {article.analysis?.tags && article.analysis.tags.length > 0 && (
        <div className="flex flex-wrap gap-1">
          {article.analysis.tags.slice(0, 4).map((tag, i) => (
            <span 
              key={i}
              className="px-2 py-0.5 text-xs rounded-full bg-secondary text-secondary-foreground"
            >
              {tag}
            </span>
          ))}
        </div>
      )}

      {/* Actions */}
      <div className="flex items-center gap-2 mt-3 pt-3 border-t">
        <Link
          to={`/article/${encodeURIComponent(article.id)}`}
          className="text-xs text-primary hover:underline"
        >
          阅读详情
        </Link>
        {article.url && (
          <a
            href={article.url}
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground"
          >
            <ExternalLink className="h-3 w-3" />
            原文
          </a>
        )}
      </div>
    </div>
  );
}

