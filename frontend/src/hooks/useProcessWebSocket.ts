import { useCallback, useEffect, useRef, useState } from 'react';
import { api } from '../api/client';
import type { ProcessProgress } from '../api/client';

// WebSocket 消息类型
interface WsMessage {
  type: 'connected' | 'started' | 'progress' | 'item_done' | 'item_failed' | 'completed';
  data: Record<string, unknown>;
}

interface UseProcessWebSocketOptions {
  onItemDone?: (articleId: string, title: string) => void;
  onItemFailed?: (articleId: string, title: string, stage: string, error: string) => void;
  onCompleted?: (total: number, success: number, failed: number) => void;
}

export function useProcessWebSocket(options: UseProcessWebSocketOptions = {}) {
  const [connected, setConnected] = useState(false);
  const [progress, setProgress] = useState<ProcessProgress>({
    status: 'idle',
    total: 0,
    completed: 0,
    failed: 0,
    current_article: null,
    current_stage: null,
    started_at: null,
  });

  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<number | null>(null);
  const optionsRef = useRef(options);
  optionsRef.current = options;

  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      return;
    }

    const wsUrl = api.process.wsUrl();
    const ws = new WebSocket(wsUrl);

    ws.onopen = () => {
      setConnected(true);
      console.log('[ProcessWS] Connected');
    };

    ws.onclose = () => {
      setConnected(false);
      console.log('[ProcessWS] Disconnected');
      
      // 自动重连
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
      reconnectTimeoutRef.current = window.setTimeout(() => {
        connect();
      }, 3000);
    };

    ws.onerror = (error) => {
      console.error('[ProcessWS] Error:', error);
    };

    ws.onmessage = (event) => {
      try {
        const message: WsMessage = JSON.parse(event.data);
        handleMessage(message);
      } catch (e) {
        // 处理心跳
        if (event.data === 'ping') {
          ws.send('pong');
        }
      }
    };

    wsRef.current = ws;
  }, []);

  const handleMessage = useCallback((message: WsMessage) => {
    switch (message.type) {
      case 'connected':
        setProgress((prev) => ({
          ...prev,
          status: (message.data.status as ProcessProgress['status']) || 'idle',
          total: (message.data.total as number) || 0,
          completed: (message.data.completed as number) || 0,
          failed: (message.data.failed as number) || 0,
        }));
        break;

      case 'started':
        setProgress((prev) => ({
          ...prev,
          status: 'running',
        }));
        break;

      case 'progress':
        setProgress((prev) => ({
          ...prev,
          status: 'running',
          total: (message.data.total as number) || prev.total,
          completed: (message.data.completed as number) || prev.completed,
          failed: (message.data.failed as number) || prev.failed,
          current_article: (message.data.current as string) || null,
          current_stage: (message.data.stage as string) || null,
        }));
        break;

      case 'item_done':
        optionsRef.current.onItemDone?.(
          message.data.article_id as string,
          message.data.title as string
        );
        break;

      case 'item_failed':
        optionsRef.current.onItemFailed?.(
          message.data.article_id as string,
          message.data.title as string,
          message.data.stage as string,
          message.data.error as string
        );
        break;

      case 'completed':
        setProgress((prev) => ({
          ...prev,
          status: 'idle',
          current_article: null,
          current_stage: null,
        }));
        optionsRef.current.onCompleted?.(
          message.data.total as number,
          message.data.success as number,
          message.data.failed as number
        );
        break;
    }
  }, []);

  const disconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
  }, []);

  useEffect(() => {
    connect();
    return () => {
      disconnect();
    };
  }, [connect, disconnect]);

  return {
    connected,
    progress,
    connect,
    disconnect,
  };
}
