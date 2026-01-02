const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000';

interface ArticleListParams {
  sort?: 'value' | 'date' | 'feed';
  filter?: 'unread' | 'starred' | 'all';
  feed_id?: string;
  min_score?: number;
  page?: number;
  limit?: number;
}

interface Article {
  id: string;
  title: string;
  author: string | null;
  url: string | null;
  published_at: string | null;
  is_read: boolean;
  is_starred: boolean;
  content_source: string;
  fetch_status: string | null;
  feed: {
    id: string;
    title: string;
    icon_url: string | null;
    category: string | null;
  } | null;
  analysis: {
    summary: string | null;
    value_score: number | null;
    reading_time: number | null;
    tags: string[];
    key_points: string[];
  } | null;
}

interface ArticleDetail extends Article {
  content: string | null;
  content_html: string | null;
  feed_id: string;
}

interface Feed {
  id: string;
  title: string;
  url: string;
  site_url: string | null;
  icon_url: string | null;
  priority: number;
  fetch_full_text: string;
}

interface FeedsResponse {
  total: number;
  categories: Record<string, Feed[]>;
}

interface AnalysisResult {
  article_id: string;
  summary: string;
  key_points: string[];
  value_score: number;
  reading_time: number;
  language: string;
  tags: string[];
}

interface SyncResult {
  success: boolean;
  feeds_synced: number;
  articles_fetched: number;
  status: string;
  error: string | null;
}

interface Settings {
  freshrss_url: string;
  freshrss_username: string;
  freshrss_configured: boolean;
  llm_provider: string;
  openai_base_url: string;
  openai_model: string;
  ollama_host: string;
  ollama_model: string;
  llm_configured: boolean;
  sync_interval_minutes: number;
}

// 任务统计类型
interface TaskStats {
  pending: number;
  completed: number;
  failed: number;
  total: number;
}

// 任务进度类型
interface TaskProgress {
  batch_id?: string;
  status: 'idle' | 'running';
  total?: number;
  completed?: number;
  failed?: number;
  skipped?: number;
  current_item?: string;
  last_batch_id?: string;
  last_completed_at?: string;
}

// 失败项类型
interface FailedItem {
  article_id: string;
  title: string;
  url: string | null;
  feed_title: string;
  error: string;
}

async function fetchApi<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers,
    },
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
    throw new Error(error.detail || 'Request failed');
  }

  return response.json();
}

export const api = {
  articles: {
    list: (params: ArticleListParams = {}) => {
      const searchParams = new URLSearchParams();
      if (params.sort) searchParams.set('sort', params.sort);
      if (params.filter) searchParams.set('filter', params.filter);
      if (params.feed_id) searchParams.set('feed_id', params.feed_id);
      if (params.min_score !== undefined) searchParams.set('min_score', String(params.min_score));
      if (params.page) searchParams.set('page', String(params.page));
      if (params.limit) searchParams.set('limit', String(params.limit));
      
      return fetchApi<{ total: number; page: number; limit: number; items: Article[] }>(
        `/api/articles?${searchParams.toString()}`
      );
    },

    get: (id: string) => fetchApi<ArticleDetail>(`/api/articles/detail?article_id=${encodeURIComponent(id)}`),

    markRead: (id: string, read = true) =>
      fetchApi<{ id: string; is_read: boolean }>(`/api/articles/read?article_id=${encodeURIComponent(id)}&read=${read}`, {
        method: 'PATCH',
      }),

    toggleStar: (id: string) =>
      fetchApi<{ id: string; is_starred: boolean }>(`/api/articles/star?article_id=${encodeURIComponent(id)}`, {
        method: 'PATCH',
      }),

    fetchFull: (id: string) =>
      fetchApi<{ success: boolean; content?: string; error?: string }>(
        `/api/articles/fetch-full?article_id=${encodeURIComponent(id)}`,
        { method: 'POST' }
      ),
  },

  feeds: {
    list: () => fetchApi<FeedsResponse>('/api/feeds'),

    get: (id: string) => fetchApi<Feed>(`/api/feeds/${id}`),

    setPriority: (id: string, priority: number) =>
      fetchApi<{ id: string; priority: number }>(`/api/feeds/${id}/priority?priority=${priority}`, {
        method: 'PATCH',
      }),

    setFetchMode: (id: string, mode: 'auto' | 'always' | 'never') =>
      fetchApi<{ id: string; fetch_full_text: string }>(`/api/feeds/${id}/fetch-mode?mode=${mode}`, {
        method: 'PATCH',
      }),
  },

  analysis: {
    get: (articleId: string) => fetchApi<AnalysisResult>(`/api/analysis/article?article_id=${encodeURIComponent(articleId)}`),

    trigger: (articleId: string) =>
      fetchApi<AnalysisResult>(`/api/analysis/article?article_id=${encodeURIComponent(articleId)}`, { method: 'POST' }),

    stream: (articleId: string) => {
      return new EventSource(`${API_BASE}/api/analysis/stream/${articleId}`);
    },

    batch: (limit = 20) =>
      fetchApi<{ batch_id: string; message: string; count: number }>(
        `/api/analysis/batch?limit=${limit}`,
        { method: 'POST' }
      ),

    batchStatus: (batchId: string) =>
      fetchApi<{ total: number; completed: number; failed: number; status: string }>(
        `/api/analysis/batch/${batchId}`
      ),

    // 新增：统计信息
    stats: () => fetchApi<TaskStats>('/api/analysis/stats'),

    // 新增：失败列表
    failed: (page = 1, limit = 20) =>
      fetchApi<{ total: number; page: number; limit: number; items: FailedItem[] }>(
        `/api/analysis/failed?page=${page}&limit=${limit}`
      ),

    // 新增：重试失败
    retry: () =>
      fetchApi<{ reset_count: number; batch_id: string; message: string }>(
        '/api/analysis/retry',
        { method: 'POST' }
      ),
  },

  // 新增：全文抓取模块
  fetch: {
    // 获取统计信息
    stats: () => fetchApi<TaskStats>('/api/fetch/stats'),

    // 获取当前进度
    progress: () => fetchApi<TaskProgress>('/api/fetch/progress'),

    // 获取失败列表
    failed: (page = 1, limit = 20) =>
      fetchApi<{ total: number; page: number; limit: number; items: FailedItem[] }>(
        `/api/fetch/failed?page=${page}&limit=${limit}`
      ),

    // 触发批量抓取
    batch: (limit = 20) =>
      fetchApi<{ batch_id: string; message: string; count: number }>(
        `/api/fetch/batch?limit=${limit}`,
        { method: 'POST' }
      ),

    // 重试失败
    retry: () =>
      fetchApi<{ reset_count: number; message: string }>(
        '/api/fetch/retry',
        { method: 'POST' }
      ),
  },

  sync: {
    trigger: () => fetchApi<SyncResult>('/api/sync', { method: 'POST' }),

    status: () =>
      fetchApi<{ items: Array<{ id: number; sync_type: string; status: string; articles_fetched: number; started_at: string; completed_at: string | null }> }>(
        '/api/sync/status'
      ),
  },

  settings: {
    get: () => fetchApi<Settings>('/api/settings'),

    testFreshRSS: () =>
      fetchApi<{ success: boolean; message: string }>('/api/settings/test-freshrss', {
        method: 'POST',
      }),

    testLLM: () =>
      fetchApi<{ success: boolean; message: string }>('/api/settings/test-llm', {
        method: 'POST',
      }),
  },
};

export type { Article, ArticleDetail, Feed, FeedsResponse, AnalysisResult, Settings, TaskStats, TaskProgress, FailedItem };

