import { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { ArrowLeft, ExternalLink, Star, Clock, Sparkles, Download, BookOpen, Loader2, ThumbsUp, ThumbsDown } from 'lucide-react';
import { api } from '../api/client';
import { cn, formatDate, getScoreColor } from '../lib/utils';

// 保存最近浏览记录
function saveRecentArticle(id: string, title: string) {
  try {
    const data = localStorage.getItem('recentArticles');
    const recent = data ? JSON.parse(data) : [];
    // 移除已存在的相同文章
    const filtered = recent.filter((a: { id: string }) => a.id !== id);
    // 添加到开头
    filtered.unshift({ id, title, viewedAt: Date.now() });
    // 只保留最近 10 条
    localStorage.setItem('recentArticles', JSON.stringify(filtered.slice(0, 10)));
  } catch {
    // ignore
  }
}

export function ArticlePage() {
  const { id } = useParams<{ id: string }>();
  const queryClient = useQueryClient();
  const [deepSummary, setDeepSummary] = useState<string | null>(null);
  const [isGeneratingDeep, setIsGeneratingDeep] = useState(false);

  const { data: article, isLoading, error } = useQuery({
    queryKey: ['article', id],
    queryFn: () => api.articles.get(id!),
    enabled: !!id,
  });

  // 保存到最近浏览
  useEffect(() => {
    if (article && id) {
      saveRecentArticle(id, article.title);
    }
  }, [article, id]);

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

  const rateMutation = useMutation({
    mutationFn: (rating: number) => api.articles.rate(id!, rating),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['article', id] });
      queryClient.invalidateQueries({ queryKey: ['feeds'] });
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

        {/* Like/Dislike Buttons */}
        <div className="flex items-center gap-1 border-l pl-3 ml-1">
          <button
            onClick={() => rateMutation.mutate(article.user_rating === 1 ? 0 : 1)}
            className={cn(
              "p-2 rounded-md hover:bg-accent transition-colors",
              article.user_rating === 1 ? "text-green-500" : "text-muted-foreground"
            )}
            title="喜欢"
          >
            <ThumbsUp className={cn("h-5 w-5", article.user_rating === 1 && "fill-current")} />
          </button>
          <button
            onClick={() => rateMutation.mutate(article.user_rating === -1 ? 0 : -1)}
            className={cn(
              "p-2 rounded-md hover:bg-accent transition-colors",
              article.user_rating === -1 ? "text-red-500" : "text-muted-foreground"
            )}
            title="不喜欢"
          >
            <ThumbsDown className={cn("h-5 w-5", article.user_rating === -1 && "fill-current")} />
          </button>
        </div>
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
          {/* Header with Score */}
          <div className="flex items-center justify-between mb-6">
            <h2 className="font-semibold flex items-center gap-2 text-lg">
              <Sparkles className="h-5 w-5 text-primary" />
              AI 分析
            </h2>
            {analysis.value_score !== null && (
              <div className="text-right">
                <span className={cn("text-3xl font-bold", getScoreColor(analysis.value_score))}>
                  {analysis.value_score.toFixed(1)}
                </span>
                <span className="text-sm text-muted-foreground ml-1">/ 10</span>
              </div>
            )}
          </div>

          {/* Quick Stats */}
          <div className="grid grid-cols-3 gap-4 mb-6 p-4 bg-secondary/30 rounded-lg">
            <div className="text-center">
              <div className="text-2xl font-semibold">{analysis.reading_time || '-'}</div>
              <div className="text-xs text-muted-foreground">分钟阅读</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-semibold">{analysis.key_points?.length || 0}</div>
              <div className="text-xs text-muted-foreground">关键要点</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-semibold uppercase">{analysis.language || '-'}</div>
              <div className="text-xs text-muted-foreground">语言</div>
            </div>
          </div>

          {/* Summary */}
          <div className="mb-6">
            <h3 className="text-sm font-medium text-muted-foreground mb-2 flex items-center gap-2">
              <BookOpen className="h-4 w-4" />
              内容摘要
            </h3>
            <p className="text-foreground leading-relaxed">{analysis.summary}</p>
          </div>

          {/* Key Points */}
          {analysis.key_points && analysis.key_points.length > 0 && (
            <div className="mb-6">
              <h3 className="text-sm font-medium text-muted-foreground mb-3">关键要点</h3>
              <div className="space-y-2">
                {analysis.key_points.map((point, i) => (
                  <div key={i} className="flex items-start gap-3 p-3 bg-secondary/30 rounded-lg">
                    <span className="flex-shrink-0 w-6 h-6 rounded-full bg-primary/20 text-primary text-sm flex items-center justify-center font-medium">
                      {i + 1}
                    </span>
                    <span className="text-sm">{point}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Deep Summary */}
          {deepSummary && (
            <div className="mb-6 p-4 bg-primary/5 border border-primary/20 rounded-lg">
              <h3 className="text-sm font-medium text-primary mb-2">精华阅读版</h3>
              <div className="text-sm leading-relaxed whitespace-pre-wrap">{deepSummary}</div>
            </div>
          )}

          {/* Tags */}
          {analysis.tags && analysis.tags.length > 0 && (
            <div className="flex flex-wrap gap-2 mb-6">
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

          {/* Deep Summary Button */}
          <button
            onClick={async () => {
              if (!article.content && !article.full_content) return;
              setIsGeneratingDeep(true);
              try {
                const content = article.full_content || article.content || '';
                const controller = new AbortController();
                const timeoutId = setTimeout(() => controller.abort(), 180000); // 3分钟超时
                
                const response = await fetch(`${import.meta.env.VITE_API_BASE || 'http://localhost:8000'}/api/analysis/deep-summary`, {
                  method: 'POST',
                  headers: { 'Content-Type': 'application/json' },
                  body: JSON.stringify({ article_id: id, content, title: article.title }),
                  signal: controller.signal,
                });
                clearTimeout(timeoutId);
                
                if (!response.ok) {
                  const err = await response.json();
                  throw new Error(err.detail || '生成失败');
                }
                const data = await response.json();
                if (data.summary) {
                  setDeepSummary(data.summary);
                }
              } catch (e) {
                const error = e as Error;
                if (error.name === 'AbortError') {
                  alert('生成超时，请稍后重试');
                } else {
                  alert(`生成失败: ${error.message}`);
                }
                console.error('精华版生成失败:', e);
              } finally {
                setIsGeneratingDeep(false);
              }
            }}
            disabled={isGeneratingDeep || !!deepSummary}
            className={cn(
              "w-full flex items-center justify-center gap-2 px-4 py-3 rounded-lg",
              "bg-primary/10 text-primary hover:bg-primary/20 transition-colors",
              "disabled:opacity-50 disabled:cursor-not-allowed"
            )}
          >
            {isGeneratingDeep ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin" />
                正在生成精华版（可能需要1-2分钟）...
              </>
            ) : deepSummary ? (
              <>
                <Sparkles className="h-4 w-4" />
                已生成精华版
              </>
            ) : (
              <>
                <Sparkles className="h-4 w-4" />
                生成精华阅读版（保留关键内容，快速了解全文）
              </>
            )}
          </button>
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

      {/* Fetch Full Text Button */}
      {article.content_source === 'feed' && article.fetch_status !== 'success' && (
        <div className="flex items-center gap-2 mb-6">
          <button
            onClick={() => fetchFullMutation.mutate()}
            disabled={fetchFullMutation.isPending}
            className="flex items-center gap-1 px-4 py-2 rounded-md text-sm border hover:bg-accent"
          >
            <Download className="h-4 w-4" />
            {fetchFullMutation.isPending ? "抓取中..." : "抓取全文"}
          </button>
        </div>
      )}

      {/* Article Content */}
      <div className="bg-card rounded-lg border p-6 md:p-8">
        <h2 className="text-lg font-semibold mb-6 pb-4 border-b flex items-center gap-2">
          <BookOpen className="h-5 w-5 text-muted-foreground" />
          正文内容
        </h2>
        <article className="prose prose-neutral dark:prose-invert max-w-none prose-headings:font-semibold prose-p:leading-7 prose-p:text-base prose-li:leading-7 prose-img:rounded-lg prose-a:text-primary prose-blockquote:border-l-primary prose-blockquote:bg-muted/50 prose-blockquote:py-1 prose-blockquote:px-4 prose-blockquote:rounded-r-lg prose-code:bg-muted prose-code:px-1.5 prose-code:py-0.5 prose-code:rounded prose-code:before:content-none prose-code:after:content-none prose-pre:bg-muted prose-pre:border">
          {article.full_content ? (
            <div className="space-y-4">
              {article.full_content.split('\n').map((line, i) => {
                const trimmed = line.trim();
                if (!trimmed) return null;
                // 检测标题
                if (trimmed.startsWith('# ')) return <h1 key={i}>{trimmed.slice(2)}</h1>;
                if (trimmed.startsWith('## ')) return <h2 key={i}>{trimmed.slice(3)}</h2>;
                if (trimmed.startsWith('### ')) return <h3 key={i}>{trimmed.slice(4)}</h3>;
                // 检测列表
                if (trimmed.startsWith('- ') || trimmed.startsWith('* ')) {
                  return <li key={i} className="ml-4">{trimmed.slice(2)}</li>;
                }
                if (/^\d+\.\s/.test(trimmed)) {
                  return <li key={i} className="ml-4 list-decimal">{trimmed.replace(/^\d+\.\s/, '')}</li>;
                }
                // 检测代码块
                if (trimmed.startsWith('```')) return null;
                // 普通段落
                return <p key={i}>{trimmed}</p>;
              })}
            </div>
          ) : article.content_html ? (
            <div dangerouslySetInnerHTML={{ __html: article.content_html }} />
          ) : article.content ? (
            <div className="space-y-4">
              {article.content.split('\n').map((line, i) => {
                const trimmed = line.trim();
                if (!trimmed) return null;
                return <p key={i}>{trimmed}</p>;
              })}
            </div>
          ) : (
            <p className="text-muted-foreground text-center py-8">暂无内容</p>
          )}
        </article>
      </div>
    </div>
  );
}



