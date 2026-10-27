import { useEffect, useRef, useCallback } from 'react'

type MessageHandler = (data: Record<string, unknown>) => void

export function useWebSocket(stationId: number | null, onMessage: MessageHandler) {
  const wsRef = useRef<WebSocket | null>(null)
  const reconnectTimer = useRef<ReturnType<typeof setTimeout> | null>(null)

  const connect = useCallback(() => {
    if (!stationId) return
    const WS_BASE = import.meta.env.VITE_WS_URL ||
      `${window.location.protocol === 'https:' ? 'wss' : 'ws'}://${window.location.host}`
    const url = `${WS_BASE}/ws/station/${stationId}`

    const ws = new WebSocket(url)
    wsRef.current = ws

    ws.onopen = () => console.log(`[WS] connected to station ${stationId}`)
    ws.onmessage = (e) => { try { onMessage(JSON.parse(e.data)) } catch { } }
    ws.onerror = () => console.warn('[WS] error')
    ws.onclose = () => {
      // Reconnect after 3s
      reconnectTimer.current = setTimeout(connect, 3_000)
    }
  }, [stationId, onMessage])

  useEffect(() => {
    connect()
    return () => {
      wsRef.current?.close()
      if (reconnectTimer.current) clearTimeout(reconnectTimer.current)
    }
  }, [connect])
}
