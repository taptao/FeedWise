import { useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { ArrowLeft, ExternalLink, Star, Clock, Sparkles, Download } from 'lucide-react';
import { api } from '../api/client';
import { cn, formatDate, getScoreColor } from '../lib/utils';

type ViewMode = 'summary' | 'full';

export function ArticlePage() {
  const { id } = useParams<{ id: string }>();
  const queryClient = useQueryClient();
  const [viewMode, setViewMode] = useState<ViewMode>('summary');

  const { data: article, isLoading, error } = useQuery({
    queryKey: ['article', id],
    queryFn: () => api.articles.get(id!),
    enabled: !!id,
  });

  const { data: analysis } = useQuery({
    queryKey: ['analysis', id],
    queryFn: () => api.analysis.get(id!),
    enabled: !!id,
    retry: false,
  });

  const markReadMutation = useMutation({
    mutationFn: () => api.articles.markRead(id!, true),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['articles'] });
    },
  });

  const starMutation = useMutation({
    mutationFn: () => api.articles.toggleStar(id!),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['article', id] });
      queryClient.invalidateQueries({ queryKey: ['articles'] });
    },
  });

  const analyzeMutation = useMutation({
    mutationFn: () => api.analysis.trigger(id!),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['analysis', id] });
    },
  });

  const fetchFullMutation = useMutation({
    mutationFn: () => api.articles.fetchFull(id!),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['article', id] });
    },
  });

  // Mark as read on mount
  if (article && !article.is_read && !markReadMutation.isPending) {
    markReadMutation.mutate();
  }

  if (isLoading) {
    return (
      <div className="max-w-3xl mx-auto py-12 text-center text-muted-foreground">
        加载中...
      </div>
    );
  }

  if (error || !article) {
    return (
      <div className="max-w-3xl mx-auto py-12 text-center text-destructive">
        文章不存在或加载失败
      </div>
    );
  }

  return (
    <div className="max-w-3xl mx-auto">
      {/* Header */}
      <div className="flex items-center gap-4 mb-6">
        <Link
          to="/"
          className="p-2 rounded-md hover:bg-accent transition-colors"
        >
          <ArrowLeft className="h-5 w-5" />
        </Link>

        <div className="flex-1" />

        {article.url && (
          <a
            href={article.url}
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground"
          >
            <ExternalLink className="h-4 w-4" />
            原文链接
          </a>
        )}

        <button
          onClick={() => starMutation.mutate()}
          className={cn(
            "p-2 rounded-md hover:bg-accent transition-colors",
            article.is_starred ? "text-yellow-500" : "text-muted-foreground"
          )}
        >
          <Star className={cn("h-5 w-5", article.is_starred && "fill-current")} />
        </button>
      </div>

      {/* Article Title */}
      <h1 className="text-3xl font-bold mb-4">{article.title}</h1>

      {/* Meta Info */}
      <div className="flex items-center gap-4 text-sm text-muted-foreground mb-6">
        {article.author && <span>{article.author}</span>}
        {article.published_at && <span>{formatDate(article.published_at)}</span>}
        {analysis?.reading_time && (
          <span className="flex items-center gap-1">
            <Clock className="h-4 w-4" />
            {analysis.reading_time}分钟阅读
          </span>
        )}
      </div>

      {/* Analysis Section */}
      {analysis && (
        <div className="bg-card rounded-lg border p-6 mb-8">
          <div className="flex items-center justify-between mb-4">
            <h2 className="font-semibold flex items-center gap-2">
              <Sparkles className="h-5 w-5 text-primary" />
              AI 分析
            </h2>
            {analysis.value_score !== null && (
              <span className={cn("text-2xl font-bold", getScoreColor(analysis.value_score))}>
                {analysis.value_score.toFixed(1)} 分
              </span>
            )}
          </div>

          {/* Summary */}
          <div className="mb-4">
            <h3 className="text-sm font-medium text-muted-foreground mb-2">摘要</h3>
            <p className="text-foreground">{analysis.summary}</p>
          </div>

          {/* Key Points */}
          {analysis.key_points && analysis.key_points.length > 0 && (
            <div className="mb-4">
              <h3 className="text-sm font-medium text-muted-foreground mb-2">关键要点</h3>
              <ul className="space-y-2">
                {analysis.key_points.map((point, i) => (
                  <li key={i} className="flex items-start gap-2">
                    <span className="text-primary">•</span>
                    <span>{point}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Tags */}
          {analysis.tags && analysis.tags.length > 0 && (
            <div className="flex flex-wrap gap-2">
              {analysis.tags.map((tag, i) => (
                <span
                  key={i}
                  className="px-3 py-1 text-sm rounded-full bg-secondary text-secondary-foreground"
                >
                  {tag}
                </span>
              ))}
            </div>
          )}
        </div>
      )}

      {/* No Analysis - Trigger Button */}
      {!analysis && (
        <div className="bg-card rounded-lg border p-6 mb-8 text-center">
          <p className="text-muted-foreground mb-4">此文章尚未进行 AI 分析</p>
          <button
            onClick={() => analyzeMutation.mutate()}
            disabled={analyzeMutation.isPending}
            className={cn(
              "inline-flex items-center gap-2 px-4 py-2 rounded-md",
              "bg-primary text-primary-foreground hover:bg-primary/90",
              "disabled:opacity-50"
            )}
          >
            <Sparkles className="h-4 w-4" />
            {analyzeMutation.isPending ? "分析中..." : "开始分析"}
          </button>
        </div>
      )}

      {/* View Mode Toggle */}
      <div className="flex items-center gap-2 mb-6">
        <button
          onClick={() => setViewMode('summary')}
          className={cn(
            "px-4 py-2 rounded-md text-sm",
            viewMode === 'summary' ? "bg-primary text-primary-foreground" : "bg-secondary"
          )}
        >
          摘要视图
        </button>
        <button
          onClick={() => setViewMode('full')}
          className={cn(
            "px-4 py-2 rounded-md text-sm",
            viewMode === 'full' ? "bg-primary text-primary-foreground" : "bg-secondary"
          )}
        >
          原文视图
        </button>

        {article.content_source === 'feed' && article.fetch_status !== 'success' && (
          <button
            onClick={() => fetchFullMutation.mutate()}
            disabled={fetchFullMutation.isPending}
            className="flex items-center gap-1 px-4 py-2 rounded-md text-sm border hover:bg-accent"
          >
            <Download className="h-4 w-4" />
            {fetchFullMutation.isPending ? "抓取中..." : "抓取全文"}
          </button>
        )}
      </div>

      {/* Content */}
      <div className="prose prose-neutral dark:prose-invert max-w-none">
        {viewMode === 'summary' && analysis?.summary ? (
          <div>
            <p className="text-lg">{analysis.summary}</p>
            {analysis.key_points && analysis.key_points.length > 0 && (
              <ul>
                {analysis.key_points.map((point, i) => (
                  <li key={i}>{point}</li>
                ))}
              </ul>
            )}
          </div>
        ) : article.content_html ? (
          <div dangerouslySetInnerHTML={{ __html: article.content_html }} />
        ) : article.content ? (
          <div className="whitespace-pre-wrap">{article.content}</div>
        ) : (
          <p className="text-muted-foreground">暂无内容</p>
        )}
      </div>
    </div>
  );
}



