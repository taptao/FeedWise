import { useQuery, useMutation } from '@tanstack/react-query';
import { CheckCircle, XCircle, Loader2 } from 'lucide-react';
import { api } from '../api/client';
import { cn } from '../lib/utils';

export function SettingsPage() {
  const { data: settings, isLoading } = useQuery({
    queryKey: ['settings'],
    queryFn: api.settings.get,
  });

  const testFreshRSSMutation = useMutation({
    mutationFn: api.settings.testFreshRSS,
  });

  const testLLMMutation = useMutation({
    mutationFn: api.settings.testLLM,
  });

  if (isLoading) {
    return (
      <div className="max-w-2xl mx-auto py-12 text-center text-muted-foreground">
        加载中...
      </div>
    );
  }

  if (!settings) {
    return (
      <div className="max-w-2xl mx-auto py-12 text-center text-destructive">
        加载设置失败
      </div>
    );
  }

  return (
    <div className="max-w-2xl mx-auto">
      <h1 className="text-2xl font-bold mb-8">设置</h1>

      {/* FreshRSS Settings */}
      <section className="bg-card rounded-lg border p-6 mb-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold">FreshRSS 配置</h2>
          <span className={cn(
            "flex items-center gap-1 text-sm",
            settings.freshrss_configured ? "text-green-500" : "text-yellow-500"
          )}>
            {settings.freshrss_configured ? (
              <>
                <CheckCircle className="h-4 w-4" />
                已配置
              </>
            ) : (
              <>
                <XCircle className="h-4 w-4" />
                未配置
              </>
            )}
          </span>
        </div>

        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-muted-foreground mb-1">
              服务器地址
            </label>
            <input
              type="text"
              value={settings.freshrss_url || ''}
              readOnly
              className="w-full px-3 py-2 rounded-md border bg-muted"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-muted-foreground mb-1">
              用户名
            </label>
            <input
              type="text"
              value={settings.freshrss_username || ''}
              readOnly
              className="w-full px-3 py-2 rounded-md border bg-muted"
            />
          </div>

          <button
            onClick={() => testFreshRSSMutation.mutate()}
            disabled={testFreshRSSMutation.isPending}
            className={cn(
              "flex items-center gap-2 px-4 py-2 rounded-md",
              "border hover:bg-accent transition-colors",
              "disabled:opacity-50"
            )}
          >
            {testFreshRSSMutation.isPending && <Loader2 className="h-4 w-4 animate-spin" />}
            测试连接
          </button>

          {testFreshRSSMutation.data && (
            <div className={cn(
              "p-3 rounded-md text-sm",
              testFreshRSSMutation.data.success ? "bg-green-500/10 text-green-600" : "bg-destructive/10 text-destructive"
            )}>
              {testFreshRSSMutation.data.message}
            </div>
          )}
        </div>
      </section>

      {/* LLM Settings */}
      <section className="bg-card rounded-lg border p-6 mb-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold">AI 配置</h2>
          <span className={cn(
            "flex items-center gap-1 text-sm",
            settings.llm_configured ? "text-green-500" : "text-yellow-500"
          )}>
            {settings.llm_configured ? (
              <>
                <CheckCircle className="h-4 w-4" />
                已配置
              </>
            ) : (
              <>
                <XCircle className="h-4 w-4" />
                未配置
              </>
            )}
          </span>
        </div>

        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-muted-foreground mb-1">
              提供商
            </label>
            <input
              type="text"
              value={settings.llm_provider.toUpperCase()}
              readOnly
              className="w-full px-3 py-2 rounded-md border bg-muted"
            />
          </div>

          {settings.llm_provider === 'openai' && (
            <>
              <div>
                <label className="block text-sm font-medium text-muted-foreground mb-1">
                  Base URL
                </label>
                <input
                  type="text"
                  value={settings.openai_base_url}
                  readOnly
                  className="w-full px-3 py-2 rounded-md border bg-muted"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-muted-foreground mb-1">
                  模型
                </label>
                <input
                  type="text"
                  value={settings.openai_model}
                  readOnly
                  className="w-full px-3 py-2 rounded-md border bg-muted"
                />
              </div>
            </>
          )}

          {settings.llm_provider === 'ollama' && (
            <>
              <div>
                <label className="block text-sm font-medium text-muted-foreground mb-1">
                  Ollama Host
                </label>
                <input
                  type="text"
                  value={settings.ollama_host}
                  readOnly
                  className="w-full px-3 py-2 rounded-md border bg-muted"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-muted-foreground mb-1">
                  模型
                </label>
                <input
                  type="text"
                  value={settings.ollama_model}
                  readOnly
                  className="w-full px-3 py-2 rounded-md border bg-muted"
                />
              </div>
            </>
          )}

          <button
            onClick={() => testLLMMutation.mutate()}
            disabled={testLLMMutation.isPending}
            className={cn(
              "flex items-center gap-2 px-4 py-2 rounded-md",
              "border hover:bg-accent transition-colors",
              "disabled:opacity-50"
            )}
          >
            {testLLMMutation.isPending && <Loader2 className="h-4 w-4 animate-spin" />}
            测试连接
          </button>

          {testLLMMutation.data && (
            <div className={cn(
              "p-3 rounded-md text-sm",
              testLLMMutation.data.success ? "bg-green-500/10 text-green-600" : "bg-destructive/10 text-destructive"
            )}>
              {testLLMMutation.data.message}
            </div>
          )}
        </div>
      </section>

      {/* Sync Settings */}
      <section className="bg-card rounded-lg border p-6">
        <h2 className="text-lg font-semibold mb-4">同步设置</h2>
        <div>
          <label className="block text-sm font-medium text-muted-foreground mb-1">
            同步间隔
          </label>
          <input
            type="text"
            value={`${settings.sync_interval_minutes} 分钟`}
            readOnly
            className="w-full px-3 py-2 rounded-md border bg-muted"
          />
        </div>
      </section>

      {/* Info */}
      <p className="text-sm text-muted-foreground mt-6 text-center">
        配置项通过 <code className="bg-muted px-1 rounded">.env</code> 文件管理，修改后需重启服务
      </p>
    </div>
  );
}



