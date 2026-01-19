import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { CheckCircle, XCircle, Loader2, Save } from 'lucide-react';
import { useState, useEffect } from 'react';
import { api } from '../api/client';
import { cn } from '../lib/utils';

export function SettingsPage() {
  const queryClient = useQueryClient();
  const { data: settings, isLoading } = useQuery({
    queryKey: ['settings'],
    queryFn: api.settings.get,
  });

  // 编辑状态
  const [editMode, setEditMode] = useState(false);
  const [formData, setFormData] = useState({
    llm_provider: '',
    ollama_host: '',
    ollama_model: '',
    openai_base_url: '',
    openai_model: '',
    analysis_prompt_criteria: '',
  });

  // 同步 settings 到 formData
  useEffect(() => {
    if (settings) {
      setFormData({
        llm_provider: settings.llm_provider,
        ollama_host: settings.ollama_host,
        ollama_model: settings.ollama_model,
        openai_base_url: settings.openai_base_url,
        openai_model: settings.openai_model,
        analysis_prompt_criteria: settings.analysis_prompt_criteria || '',
      });
    }
  }, [settings]);

  const updateMutation = useMutation({
    mutationFn: api.settings.update,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['settings'] });
      setEditMode(false);
    },
  });

  const testFreshRSSMutation = useMutation({
    mutationFn: api.settings.testFreshRSS,
  });

  const testLLMMutation = useMutation({
    mutationFn: api.settings.testLLM,
  });

  const handleSave = () => {
    updateMutation.mutate(formData);
  };

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
          <div className="flex items-center gap-2">
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
            <button
              onClick={() => setEditMode(!editMode)}
              className="text-sm text-primary hover:underline ml-2"
            >
              {editMode ? '取消' : '编辑'}
            </button>
          </div>
        </div>

        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-muted-foreground mb-1">
              提供商
            </label>
            {editMode ? (
              <select
                value={formData.llm_provider}
                onChange={(e) => setFormData({ ...formData, llm_provider: e.target.value })}
                className="w-full px-3 py-2 rounded-md border bg-background"
              >
                <option value="ollama">Ollama</option>
                <option value="openai">OpenAI</option>
              </select>
            ) : (
              <input
                type="text"
                value={settings.llm_provider.toUpperCase()}
                readOnly
                className="w-full px-3 py-2 rounded-md border bg-muted"
              />
            )}
          </div>

          {(editMode ? formData.llm_provider : settings.llm_provider) === 'openai' && (
            <>
              <div>
                <label className="block text-sm font-medium text-muted-foreground mb-1">
                  Base URL
                </label>
                <input
                  type="text"
                  value={editMode ? formData.openai_base_url : settings.openai_base_url}
                  onChange={(e) => setFormData({ ...formData, openai_base_url: e.target.value })}
                  readOnly={!editMode}
                  className={cn("w-full px-3 py-2 rounded-md border", editMode ? "bg-background" : "bg-muted")}
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-muted-foreground mb-1">
                  模型
                </label>
                <input
                  type="text"
                  value={editMode ? formData.openai_model : settings.openai_model}
                  onChange={(e) => setFormData({ ...formData, openai_model: e.target.value })}
                  readOnly={!editMode}
                  className={cn("w-full px-3 py-2 rounded-md border", editMode ? "bg-background" : "bg-muted")}
                />
              </div>
            </>
          )}

          {(editMode ? formData.llm_provider : settings.llm_provider) === 'ollama' && (
            <>
              <div>
                <label className="block text-sm font-medium text-muted-foreground mb-1">
                  Ollama Host
                </label>
                <input
                  type="text"
                  value={editMode ? formData.ollama_host : settings.ollama_host}
                  onChange={(e) => setFormData({ ...formData, ollama_host: e.target.value })}
                  readOnly={!editMode}
                  className={cn("w-full px-3 py-2 rounded-md border", editMode ? "bg-background" : "bg-muted")}
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-muted-foreground mb-1">
                  模型
                </label>
                <input
                  type="text"
                  value={editMode ? formData.ollama_model : settings.ollama_model}
                  onChange={(e) => setFormData({ ...formData, ollama_model: e.target.value })}
                  readOnly={!editMode}
                  className={cn("w-full px-3 py-2 rounded-md border", editMode ? "bg-background" : "bg-muted")}
                />
              </div>
            </>
          )}

          <div className="flex gap-2">
            {editMode && (
              <button
                onClick={handleSave}
                disabled={updateMutation.isPending}
                className={cn(
                  "flex items-center gap-2 px-4 py-2 rounded-md",
                  "bg-primary text-primary-foreground hover:bg-primary/90 transition-colors",
                  "disabled:opacity-50"
                )}
              >
                {updateMutation.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Save className="h-4 w-4" />}
                保存
              </button>
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
          </div>

          {updateMutation.data && (
            <div className={cn(
              "p-3 rounded-md text-sm",
              updateMutation.data.success ? "bg-green-500/10 text-green-600" : "bg-destructive/10 text-destructive"
            )}>
              {updateMutation.data.message}
            </div>
          )}

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

      {/* Analysis Criteria Settings */}
      <section className="bg-card rounded-lg border p-6 mt-6">
        <h2 className="text-lg font-semibold mb-4">AI 分析评分标准</h2>
        <p className="text-sm text-muted-foreground mb-4">
          自定义文章价值评分标准，留空使用默认标准
        </p>
        <div>
          <label className="block text-sm font-medium text-muted-foreground mb-1">
            评分标准 (Markdown 格式)
          </label>
          <textarea
            value={editMode ? formData.analysis_prompt_criteria : (settings.analysis_prompt_criteria || '')}
            onChange={(e) => setFormData({ ...formData, analysis_prompt_criteria: e.target.value })}
            readOnly={!editMode}
            placeholder={`## 价值评分标准 (1-10)
- 9-10: 突破性内容、重大新闻、深度原创分析
- 7-8: 高质量技术文章、有价值的见解
- 5-6: 一般性信息、常规更新
- 3-4: 旧闻、重复内容、广告软文
- 1-2: 垃圾内容、无实质内容`}
            rows={8}
            className={cn(
              "w-full px-3 py-2 rounded-md border font-mono text-sm",
              editMode ? "bg-background" : "bg-muted"
            )}
          />
        </div>
      </section>

      {/* Info */}
      <p className="text-sm text-muted-foreground mt-6 text-center">
        AI 配置可在线修改，其他配置通过 <code className="bg-muted px-1 rounded">.env</code> 文件管理
      </p>
    </div>
  );
}



