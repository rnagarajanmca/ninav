import React, { useCallback, useEffect, useRef, useState } from 'react'
import type { CSSProperties, FormEvent, PointerEvent as ReactPointerEvent, WheelEvent as ReactWheelEvent } from 'react'
import type { ImageMetadata } from '../types/media'
import { formatFileSize, getFolderFromPath, resolveMediaUrl } from '../lib/api'

type ViewerMode = 'frame' | 'fill' | 'zoom'

const VIEWER_MODE_OPTIONS: { key: ViewerMode; label: string; icon: string }[] = [
  { key: 'frame', label: 'Frame', icon: '🖼️' },
  { key: 'fill', label: 'Fill', icon: '🪟' },
  { key: 'zoom', label: 'Zoom', icon: '🔍' },
]

const VIEWER_MODE_MESSAGES: Record<ViewerMode, string> = {
  frame: 'Fit to frame',
  fill: 'Fill view',
  zoom: 'Zoom & pan',
}

const MIN_ZOOM = 0.5
const MAX_ZOOM = 5
const ZOOM_STEP = 0.25

interface LightboxProps {
  image: ImageMetadata
  imageIndex: number
  totalImages: number
  onClose: () => void
  onPrevious?: () => void
  onNext?: () => void
  showPrevious?: boolean
  showNext?: boolean
  favorites: Set<string>
  onToggleFavorite: (image: ImageMetadata, options?: { silent?: boolean; context?: string }) => void
  onRename: (image: ImageMetadata, newName: string) => Promise<void>
  onDelete: (image: ImageMetadata) => Promise<void>
  renamePending: boolean
  deletePending: boolean
  renameError: string | null
  deleteError: string | null
}

export const Lightbox: React.FC<LightboxProps> = ({
  image,
  imageIndex,
  totalImages,
  onClose,
  onPrevious,
  onNext,
  showPrevious = false,
  showNext = false,
  favorites,
  onToggleFavorite,
  onRename,
  onDelete,
  renamePending,
  deletePending,
  renameError,
  deleteError,
}) => {
  const [isRenaming, setIsRenaming] = useState(false)
  const [confirmDelete, setConfirmDelete] = useState(false)
  const [renameDraft, setRenameDraft] = useState('')
  const [showDetails, setShowDetails] = useState(true)
  const [lightboxNotice, setLightboxNotice] = useState<string | null>(null)
  const [viewerMode, setViewerMode] = useState<ViewerMode>('frame')
  const [baseViewerMode, setBaseViewerMode] = useState<Exclude<ViewerMode, 'zoom'>>('frame')
  const [zoomLevel, setZoomLevel] = useState(1)
  const [panOffset, setPanOffset] = useState({ x: 0, y: 0 })
  const [isPanning, setIsPanning] = useState(false)
  const viewerRef = useRef<HTMLDivElement | null>(null)
  const panStartRef = useRef<{ pointerId: number; x: number; y: number; panX: number; panY: number } | null>(null)

  const isFavorite = favorites.has(image.id)

  useEffect(() => {
    setRenameDraft(image.name)
    setIsRenaming(false)
    setConfirmDelete(false)
    resetZoomState()
  }, [image])

  const resetZoomState = useCallback(() => {
    setViewerMode('frame')
    setZoomLevel(1)
    setPanOffset({ x: 0, y: 0 })
    setIsPanning(false)
    panStartRef.current = null
  }, [])

  const clampPanOffset = useCallback((offset: { x: number; y: number }, zoom = zoomLevel) => {
    const viewer = viewerRef.current
    if (!viewer || zoom <= 1) {
      return { x: 0, y: 0 }
    }
    const maxX = ((zoom - 1) * viewer.clientWidth) / 2
    const maxY = ((zoom - 1) * viewer.clientHeight) / 2
    return {
      x: Math.max(-maxX, Math.min(maxX, offset.x)),
      y: Math.max(-maxY, Math.min(maxY, offset.y)),
    }
  }, [zoomLevel])

  const handleViewerModeChange = useCallback((mode: ViewerMode, { announce = true, source = 'unknown' } = {}) => {
    setViewerMode((current) => {
      if (current === mode) {
        return current
      }
      if (mode !== 'zoom') {
        setBaseViewerMode(mode)
        setZoomLevel(1)
        setPanOffset({ x: 0, y: 0 })
        setIsPanning(false)
        panStartRef.current = null
      } else if (current !== 'zoom') {
        setZoomLevel(1.5)
        setPanOffset({ x: 0, y: 0 })
        panStartRef.current = null
      }
      if (announce) {
        flashLightboxNotice(VIEWER_MODE_MESSAGES[mode])
      }
      return mode
    })
  }, [])

  const cycleViewerMode = useCallback((source = 'button') => {
    const currentIndex = VIEWER_MODE_OPTIONS.findIndex((option) => option.key === viewerMode)
    const nextOption = VIEWER_MODE_OPTIONS[(currentIndex + 1) % VIEWER_MODE_OPTIONS.length]
    handleViewerModeChange(nextOption.key, { source })
  }, [viewerMode, handleViewerModeChange])

  const toggleZoomShortcut = useCallback((source = 'shortcut') => {
    if (viewerMode === 'zoom') {
      handleViewerModeChange(baseViewerMode, { source })
    } else {
      handleViewerModeChange('zoom', { source })
    }
  }, [viewerMode, baseViewerMode, handleViewerModeChange])

  const viewerImageStyle = React.useMemo<CSSProperties>(() => {
    if (viewerMode === 'zoom') {
      return {
        transform: `translate3d(${panOffset.x}px, ${panOffset.y}px, 0) scale(${zoomLevel})`,
        cursor: isPanning ? 'grabbing' : 'grab',
        transition: isPanning ? 'none' : 'transform 0.12s ease-out',
        objectFit: 'contain',
      }
    }
    return {
      objectFit: viewerMode === 'fill' ? 'cover' : 'contain',
      cursor: 'zoom-in',
      transform: 'scale(1)',
      transition: 'object-fit 0.2s ease',
    }
  }, [isPanning, panOffset.x, panOffset.y, viewerMode, zoomLevel])

  const handleViewerWheel = useCallback((event: ReactWheelEvent<HTMLDivElement>) => {
    event.preventDefault()
    if (viewerMode !== 'zoom') {
      handleViewerModeChange('zoom', { announce: false, source: 'wheel' })
    }
    const direction = event.deltaY < 0 ? 1 : -1
    setZoomLevel((current) => {
      const next = Math.max(MIN_ZOOM, Math.min(MAX_ZOOM, current + direction * ZOOM_STEP))
      setPanOffset((prev) => clampPanOffset(prev, next))
      return next
    })
  }, [viewerMode, handleViewerModeChange, clampPanOffset])

  const handleViewerPointerDown = useCallback((event: ReactPointerEvent<HTMLDivElement>) => {
    if (viewerMode !== 'zoom') {
      return
    }
    event.preventDefault()
    event.currentTarget.setPointerCapture(event.pointerId)
    panStartRef.current = {
      pointerId: event.pointerId,
      x: event.clientX,
      y: event.clientY,
      panX: panOffset.x,
      panY: panOffset.y,
    }
    setIsPanning(true)
  }, [viewerMode, panOffset.x, panOffset.y])

  const handleViewerPointerMove = useCallback((event: ReactPointerEvent<HTMLDivElement>) => {
    if (viewerMode !== 'zoom') {
      return
    }
    const start = panStartRef.current
    if (!start || start.pointerId !== event.pointerId) {
      return
    }
    event.preventDefault()
    const deltaX = event.clientX - start.x
    const deltaY = event.clientY - start.y
    setPanOffset(clampPanOffset({ x: start.panX + deltaX, y: start.panY + deltaY }))
  }, [viewerMode, clampPanOffset])

  const handleViewerPointerUpOrCancel = useCallback((event: ReactPointerEvent<HTMLDivElement>) => {
    if (panStartRef.current?.pointerId !== event.pointerId) {
      return
    }
    event.preventDefault()
    event.currentTarget.releasePointerCapture(event.pointerId)
    panStartRef.current = null
    setIsPanning(false)
  }, [])

  const flashLightboxNotice = useCallback((message: string) => {
    setLightboxNotice(message)
    window.setTimeout(() => {
      setLightboxNotice((current) => (current === message ? null : current))
    }, 2000)
  }, [])

  const handleRenameSubmit = async (event: FormEvent) => {
    event.preventDefault()
    if (renamePending) return
    const trimmed = renameDraft.trim()
    if (!trimmed) {
      // Could add error handling here
      return
    }
    try {
      await onRename(image, trimmed)
      setIsRenaming(false)
    } catch (error) {
      // Error is handled via props
    }
  }

  const handleDeleteImage = async () => {
    try {
      await onDelete(image)
      setConfirmDelete(false)
    } catch (error) {
      // Error is handled via props
    }
  }

  const toggleDetailsPanel = useCallback(() => {
    setShowDetails((prev) => !prev)
  }, [])

  const handleShare = async () => {
    const shareUrl = resolveMediaUrl(image.url)
    try {
      if (navigator.share) {
        await navigator.share({ title: image.name, url: shareUrl })
      } else if (navigator.clipboard?.writeText) {
        await navigator.clipboard.writeText(shareUrl)
        flashLightboxNotice('Link copied to clipboard')
      } else {
        window.open(shareUrl, '_blank')
      }
    } catch (error) {
      console.error('Share failed', error)
      setLightboxNotice('Unable to share')
    }
  }

  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'ArrowRight' && showNext) {
        event.preventDefault()
        onNext?.()
      } else if (event.key === 'ArrowLeft' && showPrevious) {
        event.preventDefault()
        onPrevious?.()
      } else if (event.key.toLowerCase() === 'f') {
        event.preventDefault()
        onToggleFavorite(image)
      } else if (event.key.toLowerCase() === 'z') {
        event.preventDefault()
        cycleViewerMode()
      } else if (event.key.toLowerCase() === 'i') {
        event.preventDefault()
        toggleDetailsPanel()
      } else if (event.key === 'Escape') {
        onClose()
      }
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [image, showNext, showPrevious, onNext, onPrevious, onToggleFavorite, cycleViewerMode, toggleDetailsPanel, onClose])

  return (
    <div className="lightbox" role="dialog" aria-modal="true" onClick={onClose}>
      <div className="lightbox__content" onClick={(e) => e.stopPropagation()}>
        <header className="lightbox__topbar">
          <button type="button" className="lightbox__back" onClick={onClose}>
            ← Back to grid
          </button>
          <div className="lightbox__topbarInfo">
            <h3>{image.name}</h3>
            <p>
              {imageIndex + 1} of {totalImages}
            </p>
          </div>
          <div className="lightbox__actionsCluster">
            <button
              type="button"
              className={`icon-pill ${isRenaming ? 'is-active' : ''}`}
              onClick={() => {
                setIsRenaming((value) => !value)
                setRenameDraft(image.name)
                setConfirmDelete(false)
              }}
              aria-pressed={isRenaming}
            >
              ✎
              <span>Rename</span>
            </button>
            <button
              type="button"
              className="icon-pill danger"
              onClick={() => {
                setConfirmDelete((value) => !value)
                setIsRenaming(false)
              }}
              disabled={deletePending}
              aria-pressed={confirmDelete}
            >
              🗑
              <span>Trash</span>
            </button>
            <button
              type="button"
              className="icon-pill secondary"
              onClick={() => cycleViewerMode('button')}
              aria-label={`Change viewer mode (current: ${VIEWER_MODE_MESSAGES[viewerMode]})`}
            >
              {VIEWER_MODE_OPTIONS.find((option) => option.key === viewerMode)?.icon ?? '🖼️'}
              <span>{VIEWER_MODE_MESSAGES[viewerMode]}</span>
            </button>
            <button
              type="button"
              className={`icon-pill secondary ${isFavorite ? 'is-active' : ''}`}
              onClick={() => onToggleFavorite(image)}
              aria-pressed={isFavorite}
            >
              {isFavorite ? '❤️' : '🤍'}
              <span>{isFavorite ? 'Favorited' : 'Favorite'}</span>
            </button>
            <button type="button" className="icon-pill secondary" onClick={handleShare}>
              🔗<span>Share</span>
            </button>
            <a
              href={resolveMediaUrl(image.url)}
              download={image.name}
              className="icon-pill secondary"
              aria-label="Download original file"
            >
              ⬇<span>Download</span>
            </a>
            <button type="button" className={`icon-pill secondary ${showDetails ? 'is-active' : ''}`} onClick={toggleDetailsPanel} aria-pressed={showDetails}>
              ℹ️<span>Info</span>
            </button>
          </div>
        </header>
        {lightboxNotice && <p className="lightbox__notice">{lightboxNotice}</p>}
        <div
          className={`lightbox__viewer viewer-mode--${viewerMode}`}
          ref={viewerRef}
          onWheel={handleViewerWheel}
          onPointerDown={handleViewerPointerDown}
          onPointerMove={handleViewerPointerMove}
          onPointerUp={handleViewerPointerUpOrCancel}
          onPointerLeave={handleViewerPointerUpOrCancel}
          onPointerCancel={handleViewerPointerUpOrCancel}
          onDoubleClick={() => toggleZoomShortcut('double_click')}
        >
          {showPrevious && (
            <button type="button" className="lightbox__nav lightbox__nav--left" onClick={onPrevious}>
              ‹
            </button>
          )}
          <img
            src={resolveMediaUrl(image.url)}
            alt={image.name}
            className="lightbox__viewerImage"
            style={viewerImageStyle}
          />
          {showNext && (
            <button type="button" className="lightbox__nav lightbox__nav--right" onClick={onNext}>
              ›
            </button>
          )}
        </div>
        {(isRenaming || confirmDelete) && (
          <div className="lightbox__actionBar">
            {isRenaming ? (
              <form className="action-bar-content" onSubmit={handleRenameSubmit}>
                <div className="action-bar-text">
                  <strong>Rename file</strong>
                </div>
                <div className="action-bar-controls">
                  <input
                    id="rename-input"
                    type="text"
                    value={renameDraft}
                    onChange={(event) => setRenameDraft(event.target.value)}
                    disabled={renamePending}
                    autoFocus
                    className="action-bar-input"
                    placeholder="Enter new name..."
                  />
                  <button type="submit" disabled={renamePending}>
                    {renamePending ? 'Saving…' : 'Save'}
                  </button>
                  <button
                    type="button"
                    className="ghost"
                    onClick={() => {
                      setIsRenaming(false)
                      setRenameDraft(image.name)
                    }}
                    disabled={renamePending}
                  >
                    Cancel
                  </button>
                </div>
              </form>
            ) : (
              <div className="action-bar-content">
                <div className="action-bar-text">
                  <strong>Move to trash?</strong>
                  <p>This file will stay in .trash until you empty it.</p>
                </div>
                <div className="action-bar-controls">
                  <button type="button" className="ghost" onClick={() => setConfirmDelete(false)} disabled={deletePending}>
                    Keep file
                  </button>
                  <button type="button" className="danger" onClick={handleDeleteImage} disabled={deletePending}>
                    {deletePending ? 'Moving…' : 'Confirm'}
                  </button>
                </div>
              </div>
            )}
          </div>
        )}
        {(renameError || deleteError) && (
          <div className="lightbox__actionBar lightbox__actionBar--error">
            <div className="action-bar-content">
              <p className="error-text">{renameError || deleteError}</p>
            </div>
          </div>
        )}
        {(showDetails || isRenaming || confirmDelete) && (
          <section className="lightbox__metaPanel">
            {(renameError || deleteError) && <p className="error-text">{renameError || deleteError}</p>}
            {showDetails && (
              <div className="lightbox__metaDetails">
                <dl>
                  <div>
                    <dt>Folder</dt>
                    <dd>{getFolderFromPath(image.relative_path) || 'Root'}</dd>
                  </div>
                  <div>
                    <dt>Size</dt>
                    <dd>{formatFileSize(image.size_bytes)}</dd>
                  </div>
                  <div>
                    <dt>Modified</dt>
                    <dd>{new Date(image.modified_at).toLocaleString()}</dd>
                  </div>
                  <div>
                    <dt>Relative path</dt>
                    <dd>{image.relative_path}</dd>
                  </div>
                </dl>
              </div>
            )}
          </section>
        )}
      </div>
    </div>
  )
}