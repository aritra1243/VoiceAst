import { useState, useEffect, useRef } from 'react';

export function useWebSocket(onMessage) {
  const [status, setStatus] = useState('offline'); // 'online' | 'offline' | 'listening'
  const wsRef = useRef(null);
  const reconnectRef = useRef(null);

  const connect = () => {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const url = `${protocol}//${window.location.host}/ws`;
    const ws = new WebSocket(url);
    wsRef.current = ws;

    ws.onopen = () => {
      setStatus('online');
      if (reconnectRef.current) clearTimeout(reconnectRef.current);
    };

    ws.onmessage = (e) => {
      try {
        const data = JSON.parse(e.data);
        if (onMessage) onMessage(data);
      } catch (_) {}
    };

    ws.onclose = () => {
      setStatus('offline');
      reconnectRef.current = setTimeout(connect, 2500);
    };

    ws.onerror = () => {
      setStatus('offline');
      ws.close();
    };
  };

  useEffect(() => {
    connect();
    return () => {
      if (wsRef.current) wsRef.current.close();
      if (reconnectRef.current) clearTimeout(reconnectRef.current);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const send = (data) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(data));
    }
  };

  return { status, send, setStatus };
}
