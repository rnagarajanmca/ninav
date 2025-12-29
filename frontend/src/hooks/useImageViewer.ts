import type { PointerEvent, WheelEvent } from 'react'
import { useCallback, useRef, useState } from 'react'

export type ViewerMode = 'frame' | 'fill' | 'zoom'

const MIN_ZOOM = 0.5
const MAX_ZOOM = 5
const ZOOM_STEP = 0.25

export function useImageViewer() {
  const [viewerMode, setViewerMode] = useState<ViewerMode>('frame')
  const [zoomLevel, setZoomLevel] = useState(1)
  const [panOffset, setPanOffset] = useState({ x: 0, y: 0 })
  const [isPanning, setIsPanning] = useState(false)
  const pointerStartRef = useRef({ x: 0, y: 0 })
  const panStartRef = useRef({ x: 0, y: 0 })

  const resetZoomState = useCallback(() => {
    setViewerMode('frame')
    setZoomLevel(1)
    setPanOffset({ x: 0, y: 0 })
    setIsPanning(false)
    pointerStartRef.current = { x: 0, y: 0 }
    panStartRef.current = { x: 0, y: 0 }
  }, [])

  const cycleViewerMode = useCallback(() => {
    setViewerMode((mode) => {
      const modes: ViewerMode[] = ['frame', 'fill', 'zoom']
      const currentIndex = modes.indexOf(mode)
      const next = modes[(currentIndex + 1) % modes.length]
      return next
    })
    setZoomLevel(1)
    setPanOffset({ x: 0, y: 0 })
  }, [])

  const clampPanOffset = useCallback((offset: { x: number; y: number }) => {
    const maxPan = 200
    return {
      x: Math.max(-maxPan, Math.min(maxPan, offset.x)),
      y: Math.max(-maxPan, Math.min(maxPan, offset.y)),
    }
  }, [])

  const handleWheel = useCallback(
    (e: WheelEvent<HTMLDivElement>) => {
      if (viewerMode !== 'zoom') return
      e.preventDefault()
      const delta = e.deltaY > 0 ? -ZOOM_STEP : ZOOM_STEP
      setZoomLevel((prev) => Math.max(MIN_ZOOM, Math.min(MAX_ZOOM, prev + delta)))
    },
    [viewerMode]
  )

  const handlePointerDown = useCallback(
    (e: PointerEvent<HTMLDivElement>) => {
      if (viewerMode !== 'zoom') return
      e.preventDefault()
      setIsPanning(true)
      pointerStartRef.current = { x: e.clientX, y: e.clientY }
      panStartRef.current = panOffset
    },
    [viewerMode, panOffset]
  )

  const handlePointerMove = useCallback(
    (e: PointerEvent<HTMLDivElement>) => {
      if (!isPanning || viewerMode !== 'zoom') return
      const dx = e.clientX - pointerStartRef.current.x
      const dy = e.clientY - pointerStartRef.current.y
      const newOffset = {
        x: panStartRef.current.x + dx,
        y: panStartRef.current.y + dy,
      }
      setPanOffset(clampPanOffset(newOffset))
    },
    [isPanning, viewerMode, clampPanOffset]
  )

  const handlePointerUp = useCallback(() => {
    setIsPanning(false)
  }, [])

  const handleDoubleClick = useCallback(() => {
    if (viewerMode === 'zoom') {
      resetZoomState()
    } else {
      setViewerMode('zoom')
      setZoomLevel(1.5)
    }
  }, [viewerMode, resetZoomState])

  return {
    viewerMode,
    zoomLevel,
    panOffset,
    isPanning,
    cycleViewerMode,
    resetZoomState,
    handleWheel,
    handlePointerDown,
    handlePointerMove,
    handlePointerUp,
    handleDoubleClick,
  }
}
