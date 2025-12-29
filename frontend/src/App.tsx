import { useEffect, useMemo, useRef, useState } from 'react'
import './App.css'
import './components/Timeline.css'

import { SidebarNav } from './components/SidebarNav'
import { PersonGrid } from './components/PersonGrid'
import { Lightbox } from './components/Lightbox'
import { ImageGrid } from './components/ImageGrid'
import { TopNav } from './components/TopNav'
import { SettingsModal } from './components/SettingsModal'
import {
  assignFaces as assignFacesRequest,
  createPerson as createPersonRequest,
  deleteImage as deleteImageRequest,
  deletePerson as deletePersonRequest,
  fetchFaceClusters,
  fetchFaces,
  fetchImages,
  fetchPersons,
  getFolderFromPath,
  mergePersons as mergePersonsRequest,
  renameImage as renameImageRequest,
  renamePerson as renamePersonRequest,
  resolveMediaUrl,
} from './lib/api'
import type { FaceCluster, FaceItem, ImageMetadata, PersonItem } from './types/media'
import { useFavorites } from './hooks/useFavorites'
import { useViewRouting } from './hooks/useViewRouting'
import { useTimeline } from './hooks/useTimeline'
import { useImageViewer } from './hooks/useImageViewer'

const ALL_FOLDERS = ''

const logUXEvent = (eventName: string, payload?: Record<string, unknown>) => {
  if (typeof window === 'undefined') return
  const entry = {
    event: eventName,
    payload,
    timestamp: new Date().toISOString(),
  }
  if (typeof navigator !== 'undefined' && typeof navigator.sendBeacon === 'function') {
    try {
      const blob = new Blob([JSON.stringify(entry)], { type: 'application/json' })
      const ok = navigator.sendBeacon('/api/telemetry', blob)
      if (ok) {
        return
      }
    } catch (error) {
      console.debug('Telemetry beacon failed', error)
    }
  }
  console.info('[ux-event]', entry)
}

type GalleryState = {
  items: ImageMetadata[]
  total: number
  loading: boolean
  error?: string
}

type PersonState = {
  items: PersonItem[]
  loading: boolean
  error?: string
}

type ViewKey =
  | 'all'
  | 'timeline'
  | 'faces'
  | 'memories'
  | 'albums'
  | 'favorites'
  | 'videos'
  | 'imports'

function App() {
  const [gallery, setGallery] = useState<GalleryState>({
    items: [],
    total: 0,
    loading: true,
  })
  const [activeFolder, setActiveFolder] = useState<string>(ALL_FOLDERS)
  const [activeView, setActiveView] = useState<ViewKey>('all')
  const [previewImage, setPreviewImage] = useState<ImageMetadata | null>(null)
  const [deleteError, setDeleteError] = useState<string | null>(null)
  const [confirmDelete, setConfirmDelete] = useState(false)
  const [renamePending, setRenamePending] = useState(false)
  const [renameError, setRenameError] = useState<string | null>(null)
  const [deletePending, setDeletePending] = useState(false)
  const [galleryVersion, setGalleryVersion] = useState(0)
  const [renameDraft, setRenameDraft] = useState('')
  const [isRenaming, setIsRenaming] = useState(false)
  const [isSettingsOpen, setIsSettingsOpen] = useState(false)
  const [persons, setPersons] = useState<PersonState>({
    items: [],
    loading: false,
  })
  const [selectedPersonId, setSelectedPersonId] = useState<string | null>(null)
  const [personFaces, setPersonFaces] = useState<{
    items: FaceItem[]
    loading: boolean
    error?: string
  }>({
    items: [],
    loading: false,
  })
  const [unassignedFaces, setUnassignedFaces] = useState<{
    items: FaceItem[]
    loading: boolean
    error?: string
  }>({
    items: [],
    loading: false,
  })
  const [faceClusters, setFaceClusters] = useState<{
    items: FaceCluster[]
    loading: boolean
    error?: string
  }>({
    items: [],
    loading: false,
  })
  const [selectedFaceIds, setSelectedFaceIds] = useState<Set<string>>(new Set())
  const [selectedClusterId, setSelectedClusterId] = useState<number | null>(null)
  const [viewMode, setViewMode] = useState<'all' | 'clustered'>('clustered')
  const [assigning, setAssigning] = useState(false)
  const [assignmentError, setAssignmentError] = useState<string | null>(null)
  const [personsVersion, setPersonsVersion] = useState(0)
  const [personFacesVersion, setPersonFacesVersion] = useState(0)
  const [unassignedVersion, setUnassignedVersion] = useState(0)
  const [showCreatePersonDialog, setShowCreatePersonDialog] = useState(false)
  const [newPersonName, setNewPersonName] = useState('')
  const [creatingPerson, setCreatingPerson] = useState(false)
  const [editingPerson, setEditingPerson] = useState<PersonItem | null>(null)
  const [editPersonName, setEditPersonName] = useState('')
  const [renamingPerson, setRenamingPerson] = useState(false)
  const [deletingPerson, setDeletingPerson] = useState<PersonItem | null>(null)
  const [mergingPerson, setMergingPerson] = useState<PersonItem | null>(null)
  const [mergeTargetId, setMergeTargetId] = useState<string>('')

  // Custom hooks
  const { favorites, favoriteCount, toggleFavorite, isFavorite } = useFavorites()
  const {
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
  } = useImageViewer()
  const panStartRef = useRef<{ x: number; y: number } | null>(null)

  // Computed values that need to be defined before being used
  const filteredImages = useMemo(() => {
    let items = gallery.items
    if (activeView === 'favorites') {
      items = items.filter((image) => favorites.has(image.id))
    }
    if (activeFolder !== ALL_FOLDERS) {
      items = items.filter((image) => {
        const folderPath = getFolderFromPath(image.relative_path) || ''
        return folderPath === activeFolder
      })
    }
    return items
  }, [activeFolder, gallery.items, activeView, favorites])

  const { viewTitle, viewSubtitle, isFavoritesView, isTimelineView, showGrid, showFaces } = useViewRouting(activeView)
  const { timelineGroups, monthGroups } = useTimeline(filteredImages)

  const libraryStatus = useMemo(() => {
    const total = gallery.total
    const hasImages = total > 0
    return { total, hasImages }
  }, [gallery.total])

  const activePerson = useMemo(() => {
    return persons.items.find((p) => p.id === selectedPersonId)
  }, [persons.items, selectedPersonId])

  useEffect(() => {
    let cancelled = false

    async function load() {
      setGallery((prev) => ({ ...prev, loading: true, error: undefined }))
      try {
        // Fetch first page quickly for immediate display (30 images ~1-2 weeks)
        const firstPage = await fetchImages({ page: 1, page_size: 30 })
        if (!cancelled) {
          setGallery({
            items: firstPage.items,
            total: firstPage.total,
            loading: false,
          })

          // Load remaining pages in background if there are more
          if (firstPage.total > firstPage.items.length) {
            loadRemainingPages(firstPage.total, firstPage.items.length)
          }
        }
      } catch (error) {
        if (!cancelled) {
          setGallery((prev) => ({
            ...prev,
            loading: false,
            error: error instanceof Error ? error.message : 'Unknown error',
          }))
        }
      }
    }

    async function loadRemainingPages(total: number, loaded: number) {
      const pageSize = 60
      let currentPage = 2
      const items: ImageMetadata[] = [...gallery.items]

      while (items.length < total && !cancelled) {
        try {
          const page = await fetchImages({ page: currentPage, page_size: pageSize })
          if (!cancelled && page.items.length > 0) {
            items.push(...page.items)
            setGallery((prev) => ({
              ...prev,
              items: [...items],
            }))
            currentPage++
          } else {
            break
          }
        } catch (error) {
          console.error('Failed to load page', currentPage, error)
          break
        }
      }
    }

    load()
    return () => {
      cancelled = true
    }
  }, [galleryVersion])

  useEffect(() => {
    if (activeView !== 'faces') {
      return
    }
    let cancelled = false
    async function loadPersons() {
      setPersons((prev) => ({ ...prev, loading: true, error: undefined }))
      try {
        const data = await fetchPersons()
        if (!cancelled) {
          setPersons({ items: data.items, loading: false })
        }
      } catch (error) {
        if (!cancelled) {
          setPersons((prev) => ({
            ...prev,
            loading: false,
            error: error instanceof Error ? error.message : 'Unknown error',
          }))
        }
      }
    }
    loadPersons()
    return () => {
      cancelled = true
    }
  }, [activeView, personsVersion])

  useEffect(() => {
    if (activeView !== 'faces') {
      // Clear selection when leaving Faces view
      setSelectedPersonId(null)
      return
    }
    // Clear selection if no persons exist
    if (persons.items.length === 0) {
      setSelectedPersonId(null)
      return
    }
    // Clear selection if the selected person no longer exists (was deleted)
    if (selectedPersonId && !persons.items.some((p) => p.id === selectedPersonId)) {
      setSelectedPersonId(null)
    }
  }, [activeView, persons.items, selectedPersonId])

  useEffect(() => {
    if (activeView !== 'faces' || !selectedPersonId) {
      return
    }
    let cancelled = false
    async function loadFaces() {
      setPersonFaces((prev) => ({ ...prev, loading: true, error: undefined }))
      try {
        const data = await fetchFaces({ person_id: selectedPersonId ?? undefined, limit: 120 })
        if (!cancelled) {
          setPersonFaces({ items: data.items, loading: false })
        }
      } catch (error) {
        if (!cancelled) {
          setPersonFaces((prev) => ({
            ...prev,
            loading: false,
            error: error instanceof Error ? error.message : 'Unknown error',
          }))
        }
      }
    }
    loadFaces()
    return () => {
      cancelled = true
    }
  }, [activeView, selectedPersonId, personFacesVersion])

  useEffect(() => {
    if (activeView !== 'faces') {
      return
    }
    let cancelled = false
    async function loadUnassigned() {
      setUnassignedFaces((prev) => ({ ...prev, loading: true, error: undefined }))
      try {
        const data = await fetchFaces({ status: 'unassigned', limit: 120 })
        if (!cancelled) {
          setUnassignedFaces({ items: data.items, loading: false })
        }
      } catch (error) {
        if (!cancelled) {
          setUnassignedFaces((prev) => ({
            ...prev,
            loading: false,
            error: error instanceof Error ? error.message : 'Unknown error',
          }))
        }
      }
    }
    loadUnassigned()
    return () => {
      cancelled = true
    }
  }, [activeView, unassignedVersion])

  useEffect(() => {
    if (activeView !== 'faces' || viewMode !== 'clustered') {
      return
    }
    let cancelled = false
    async function loadClusters() {
      setFaceClusters((prev) => ({ ...prev, loading: true, error: undefined }))
      try {
        const data = await fetchFaceClusters({ threshold: 0.6, min_cluster_size: 1 })
        if (!cancelled) {
          setFaceClusters({ items: data.clusters, loading: false })
        }
      } catch (error) {
        if (!cancelled) {
          setFaceClusters((prev) => ({
            ...prev,
            loading: false,
            error: error instanceof Error ? error.message : 'Unknown error',
          }))
        }
      }
    }
    loadClusters()
    return () => {
      cancelled = true
    }
  }, [activeView, viewMode, unassignedVersion])

  useEffect(() => {
    if (activeView !== 'faces') {
      setSelectedFaceIds(new Set())
    }
  }, [activeView])

  useEffect(() => {
    if (!previewImage) {
      setRenameDraft('')
      setIsRenaming(false)
      setRenameError(null)
      setDeleteError(null)
      setConfirmDelete(false)
      resetZoomState()
      return
    }
    setRenameDraft(previewImage.name)
    setIsRenaming(false)
    setRenameError(null)
    setDeleteError(null)
    setConfirmDelete(false)
    resetZoomState()
  }, [previewImage, resetZoomState])

  const folderSummary = useMemo(() => {
    const map = new Map<string, { key: string; label: string; count: number }>()
    gallery.items.forEach((image) => {
      const folderPath = getFolderFromPath(image.relative_path)
      const key = folderPath || ''
      const label = folderPath || 'Root'
      const current = map.get(key)
      if (current) {
        current.count += 1
      } else {
        map.set(key, { key, label, count: 1 })
      }
    })
    return Array.from(map.values()).sort((a, b) => a.label.localeCompare(b.label))
  }, [gallery.items])

  const previewIndex = useMemo(() => {
    if (!previewImage) return -1
    return filteredImages.findIndex((image) => image.id === previewImage.id)
  }, [filteredImages, previewImage])

  const showPreviousImage = () => {
    if (previewIndex > 0) {
      setPreviewImage(filteredImages[previewIndex - 1])
    }
  }

  const showNextImage = () => {
    if (previewIndex !== -1 && previewIndex < filteredImages.length - 1) {
      setPreviewImage(filteredImages[previewIndex + 1])
    }
  }

  const previewHasPrev = previewIndex > 0
  const previewHasNext = previewIndex >= 0 && previewIndex < filteredImages.length - 1

  const refreshGallery = () => {
    setGalleryVersion((prev) => prev + 1)
  }

  const toggleFavoriteWrapper = (target?: ImageMetadata, options?: { silent?: boolean; context?: string }) => {
    if (!target) return
    toggleFavorite(target.id)
    logUXEvent('favorite.toggle', {
      action: favorites.has(target.id) ? 'removed' : 'added',
      imageId: target.id,
      context: options?.context ?? 'unspecified',
    })
  }

  const toggleFaceSelection = (faceId: string) => {
    setSelectedFaceIds((prev) => {
      const next = new Set(prev)
      if (next.has(faceId)) {
        next.delete(faceId)
      } else {
        next.add(faceId)
      }
      return next
    })
  }

  const handleCreatePerson = async () => {
    if (!newPersonName.trim()) return
    setCreatingPerson(true)
    try {
      const newPerson = await createPersonRequest(newPersonName.trim())
      setPersonsVersion((prev) => prev + 1)
      setSelectedPersonId(newPerson.id)
      setShowCreatePersonDialog(false)
      setNewPersonName('')
    } catch (error) {
      alert(error instanceof Error ? error.message : 'Failed to create person')
    } finally {
      setCreatingPerson(false)
    }
  }

  const handleAssignFaces = async () => {
    if (!activePerson || selectedFaceIds.size === 0) return
    setAssigning(true)
    setAssignmentError(null)
    try {
      await assignFacesRequest(activePerson.id, Array.from(selectedFaceIds))
      setSelectedFaceIds(new Set())
      setPersonFacesVersion((prev) => prev + 1)
      setUnassignedVersion((prev) => prev + 1)
      setPersonsVersion((prev) => prev + 1)
    } catch (error) {
      setAssignmentError(error instanceof Error ? error.message : 'Failed to assign faces')
    } finally {
      setAssigning(false)
    }
  }

  const handleEditPerson = (person: PersonItem) => {
    setEditingPerson(person)
    setEditPersonName(person.label)
  }

  const handleSavePersonName = async () => {
    if (!editingPerson || !editPersonName.trim()) return
    setRenamingPerson(true)
    try {
      await renamePersonRequest(editingPerson.id, editPersonName.trim())
      setPersonsVersion((prev) => prev + 1)
      setEditingPerson(null)
      setEditPersonName('')
    } catch (error) {
      alert(error instanceof Error ? error.message : 'Failed to rename person')
    } finally {
      setRenamingPerson(false)
    }
  }

  const handleDeletePerson = (person: PersonItem) => {
    setDeletingPerson(person)
  }

  const handleConfirmDelete = async () => {
    if (!deletingPerson) return
    try {
      await deletePersonRequest(deletingPerson.id)
      setPersonsVersion((prev) => prev + 1)
      setUnassignedVersion((prev) => prev + 1)
      if (selectedPersonId === deletingPerson.id) {
        setSelectedPersonId(null)
      }
      setDeletingPerson(null)
    } catch (error) {
      alert(error instanceof Error ? error.message : 'Failed to delete person')
    }
  }

  const handleMergePerson = (person: PersonItem) => {
    setMergingPerson(person)
    setMergeTargetId('')
  }

  const handleConfirmMerge = async () => {
    if (!mergingPerson || !mergeTargetId) return
    try {
      await mergePersonsRequest(mergeTargetId, [mergingPerson.id])
      setPersonsVersion((prev) => prev + 1)
      setPersonFacesVersion((prev) => prev + 1)
      setMergingPerson(null)
      setMergeTargetId('')
      setSelectedPersonId(mergeTargetId)
    } catch (error) {
      alert(error instanceof Error ? error.message : 'Failed to merge persons')
    }
  }

  return (
    <div className="app-shell">
      <SidebarNav
        activeItem={activeView}
        onSelect={(key) => {
          setActiveView(key as ViewKey)
        }}
        counts={{
          all: gallery.total,
          favorites: favoriteCount,
          faces: persons.items.length,
        }}
      />
      <main className="workspace">
        <TopNav onSettingsClick={() => setIsSettingsOpen(true)} />

        {!isTimelineView && !showFaces && (
          <section className="workspace__header">
            <div className="header-left">
              <p className="eyebrow">{activeView === 'all' ? 'Library overview' : 'Preview'}</p>
              <h1>{viewTitle}</h1>
              <p className="subtitle">{viewSubtitle}</p>
              {activeView === 'all' && folderSummary.length > 0 && (
                <div className="folder-filter">
                  <button
                    type="button"
                    className={`folder-chip ${activeFolder === ALL_FOLDERS ? 'is-active' : ''}`}
                    onClick={() => setActiveFolder(ALL_FOLDERS)}
                  >
                    All folders <span>{gallery.total}</span>
                  </button>
                  {folderSummary.map((folder) => (
                    <button
                      key={folder.key || 'root'}
                      type="button"
                      className={`folder-chip ${activeFolder === folder.key ? 'is-active' : ''}`}
                      onClick={() => setActiveFolder(folder.key)}
                    >
                      {folder.label} <span>{folder.count}</span>
                    </button>
                  ))}
                </div>
              )}
            </div>

            <dl className="stats">
              <div>
                <dt>Total items</dt>
                <dd>{libraryStatus.hasImages ? libraryStatus.total.toLocaleString() : '--'}</dd>
              </div>
              <div>
                <dt>Status</dt>
                <dd>{gallery.loading ? 'Refreshing…' : libraryStatus.hasImages ? 'Synced' : 'Awaiting media'}</dd>
              </div>
            </dl>
          </section>
        )}

        <section className="workspace__content">
          {showGrid && (
            <>
              {isTimelineView ? (
                <div className="timeline-container">
                  {monthGroups.length > 0 && (
                    <div className="timeline-navigator">
                      {monthGroups.map((month) => (
                        <button
                          key={month.key}
                          type="button"
                          className="timeline-navigator__item"
                          onClick={() => {
                            document.getElementById(`timeline-month-${month.key}`)?.scrollIntoView({ behavior: 'smooth', block: 'start' })
                          }}
                        >
                          <span className="timeline-navigator__label">{month.label}</span>
                          <span className="timeline-navigator__count">{month.count}</span>
                        </button>
                      ))}
                    </div>
                  )}
                  <div className="timeline">
                    {timelineGroups.length === 0 && !gallery.loading && !gallery.error && (
                      <div className="empty-state">
                        <p>No images found for the selected filters.</p>
                        <small>Try adjusting the folder filter or add more media to your library.</small>
                      </div>
                    )}
                    {timelineGroups.map((group, index) => (
                      <div key={group.key}>
                        {group.isNewYear && (
                          <div className="timeline__year-divider" id={`timeline-year-${group.yearLabel}`}>
                            {group.yearLabel}
                          </div>
                        )}
                        {group.isNewMonth && (
                          <div className="timeline__month-divider" id={`timeline-month-${group.date.getFullYear()}-${String(group.date.getMonth() + 1).padStart(2, '0')}`}>
                            {group.date.toLocaleDateString('en-US', { month: 'long' })}
                          </div>
                        )}
                        <div id={`timeline-day-${group.key}`} className="timeline__group">
                          <header className="timeline__groupHeader">
                            <h3>{group.label}</h3>
                            <span className="timeline__groupCount">{group.count} {group.count === 1 ? 'item' : 'items'}</span>
                          </header>
                          <ImageGrid
                            images={group.images}
                            loading={false}
                            error={undefined}
                            onSelect={(image) => setPreviewImage(image)}
                            favoriteIds={favorites}
                            onToggleFavorite={(image) => toggleFavorite(image.id)}
                          />
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              ) : (
                <ImageGrid
                  images={filteredImages}
                  loading={gallery.loading}
                  error={gallery.error}
                  onSelect={(image) => setPreviewImage(image)}
                  favoriteIds={favorites}
                  onToggleFavorite={(image) => toggleFavoriteWrapper(image, { silent: true })}
                />
              )}
              {activeFolder !== ALL_FOLDERS && (
                <p className="subtitle">
                  Showing folder: <strong>{folderSummary.find((folder) => folder.key === activeFolder)?.label ?? 'Root'}</strong>
                  {` • ${filteredImages.length.toLocaleString()} item${filteredImages.length === 1 ? '' : 's'}`}
                </p>
              )}
            </>
          )}
          {showFaces && !activePerson && (
            <div className="faces-layout">
              <div className="faces-layout__header">
                <div className="faces-header-content">
                  <div>
                    <h1 className="faces-layout__title">Detected Faces</h1>
                    <p className="faces-layout__subtitle">
                      {faceClusters.items.length > 0
                        ? `Found ${faceClusters.items.length} unique faces grouped by similarity. Click to view photos.`
                        : 'No faces detected yet. Run face scanning from Settings.'}
                    </p>
                  </div>
                  <div className="faces-header-actions">
                    <button
                      type="button"
                      className="btn-new-person"
                      onClick={() => setShowCreatePersonDialog(true)}
                    >
                      + New Person
                    </button>
                  </div>
                </div>
              </div>

              {faceClusters.loading && (
                <div className="empty-state">
                  <p>Loading faces…</p>
                </div>
              )}
              {!faceClusters.loading && faceClusters.error && (
                <div className="empty-state error">
                  <p>{faceClusters.error}</p>
                </div>
              )}
              {!faceClusters.loading && !faceClusters.error && faceClusters.items.length === 0 && (
                <div className="empty-state">
                  <p>No faces detected yet.</p>
                  <small>Run face scanning from the Settings menu to detect faces in your photos.</small>
                </div>
              )}
              {!faceClusters.loading && !faceClusters.error && faceClusters.items.length > 0 && (
                <div className="person-photos-grid">
                  {faceClusters.items.map((cluster) => {
                    const representativeFace = cluster.faces[0]
                    const count = cluster.face_ids.length
                    return (
                      <div
                        key={cluster.cluster_id}
                        className="person-photo-item"
                        onClick={() => {
                          // Find the image in gallery and open it
                          const image = gallery.items.find(img => img.relative_path === representativeFace.relative_path)
                          if (image) {
                            setPreviewImage(image)
                          }
                        }}
                        style={{ cursor: 'pointer', position: 'relative' }}
                      >
                        <img src={resolveMediaUrl(representativeFace.image_url)} alt="" />
                        {count > 1 && (
                          <div style={{
                            position: 'absolute',
                            bottom: '4px',
                            right: '4px',
                            background: 'rgba(0,0,0,0.7)',
                            color: 'white',
                            padding: '2px 6px',
                            borderRadius: '4px',
                            fontSize: '12px',
                            fontWeight: 'bold'
                          }}>
                            {count}
                          </div>
                        )}
                      </div>
                    )
                  })}
                </div>
              )}

              {persons.items.length > 0 && (
                <div style={{ marginTop: '2rem' }}>
                  <h2>Named People ({persons.items.length})</h2>
                  <PersonGrid
                    persons={persons.items}
                    loading={persons.loading}
                    error={persons.error}
                    selectedId={selectedPersonId}
                    onSelect={(id: string) => setSelectedPersonId(id)}
                  />
                </div>
              )}
            </div>
          )}

          {showFaces && activePerson && (
            <div className="person-detail-view">
              <div className="person-detail-header">
                <div className="person-detail-header-left">
                  <button
                    type="button"
                    className="ghost btn-back"
                    onClick={() => setSelectedPersonId(null)}
                  >
                    ← Back
                  </button>
                  <div>
                    <h1 className="person-detail-title">{activePerson.label}</h1>
                    <p className="person-detail-subtitle">
                      {activePerson.face_count} {activePerson.face_count === 1 ? 'photo' : 'photos'}
                    </p>
                  </div>
                </div>
                <div className="person-actions">
                  <button
                    type="button"
                    className="ghost"
                    onClick={() => handleEditPerson(activePerson)}
                    title="Rename person"
                  >
                    Rename
                  </button>
                  <button
                    type="button"
                    className="ghost"
                    onClick={() => handleMergePerson(activePerson)}
                    title="Merge into another person"
                  >
                    Merge...
                  </button>
                  <button
                    type="button"
                    className="danger"
                    onClick={() => handleDeletePerson(activePerson)}
                    title="Delete person"
                  >
                    Delete
                  </button>
                </div>
              </div>

              <div className="person-detail-body">
                {personFaces.loading && (
                  <div className="empty-state">
                    <p>Loading photos…</p>
                  </div>
                )}
                {!personFaces.loading && personFaces.error && (
                  <div className="empty-state error">
                    <p>{personFaces.error}</p>
                  </div>
                )}
                {!personFaces.loading && !personFaces.error && personFaces.items.length === 0 && (
                  <div className="empty-state">
                    <p>No photos found for {activePerson.label}.</p>
                    <small>Assign faces to this person to see photos here.</small>
                  </div>
                )}
                {!personFaces.loading && !personFaces.error && personFaces.items.length > 0 && (
                  <div className="person-photos-grid">
                    {personFaces.items.map((face) => (
                      <div key={face.id} className="person-photo-item">
                        <img src={resolveMediaUrl(face.image_url)} alt="" />
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          )}

          {!showGrid && !showFaces && (
            <div className="empty-state">
              {activeView === 'memories' ? (
                <>
                  <p>Memories are on the way.</p>
                  <small>We’re curating smart collections based on events, people, and places. Keep an eye on this space.</small>
                </>
              ) : (
                <>
                  <p>We&apos;re polishing this surface.</p>
                  <small>Check back soon or keep exploring the full library.</small>
                </>
              )}
            </div>
          )}
        </section>
        {previewImage && (
          <Lightbox
            image={previewImage}
            imageIndex={previewIndex}
            totalImages={filteredImages.length}
            onClose={() => setPreviewImage(null)}
            onPrevious={previewHasPrev ? showPreviousImage : undefined}
            onNext={previewHasNext ? showNextImage : undefined}
            showPrevious={previewHasPrev}
            showNext={previewHasNext}
            favorites={favorites}
            onToggleFavorite={toggleFavoriteWrapper}
            onRename={async (image, newName) => {
              try {
                const updated = await renameImageRequest(image.relative_path, newName)
                setPreviewImage(updated)
                refreshGallery()
              } catch (error) {
                throw error
              }
            }}
            onDelete={async (image) => {
              try {
                await deleteImageRequest(image.relative_path)
                const fallbackPreview = previewIndex !== -1 && previewIndex < filteredImages.length - 1 ? filteredImages[previewIndex + 1] : null
                setPreviewImage(fallbackPreview)
                refreshGallery()
              } catch (error) {
                throw error
              }
            }}
            renamePending={renamePending}
            deletePending={deletePending}
            renameError={renameError}
            deleteError={deleteError}
          />
        )}
      </main>

      {showCreatePersonDialog && (
        <div
          className="modal-overlay"
          onClick={() => setShowCreatePersonDialog(false)}
        >
          <div
            className="modal-content"
            onClick={(e) => e.stopPropagation()}
          >
            <h2 className="modal-title">Create New Person</h2>
            <form
              className="modal-form"
              onSubmit={(e) => {
                e.preventDefault()
                handleCreatePerson()
              }}
            >
              <div className="form-group">
                <label htmlFor="person-name" className="form-label">
                  Name
                </label>
                <input
                  id="person-name"
                  type="text"
                  className="form-input"
                  value={newPersonName}
                  onChange={(e) => setNewPersonName(e.target.value)}
                  placeholder="Enter person's name"
                  autoFocus
                  disabled={creatingPerson}
                />
              </div>
              <div className="modal-actions">
                <button
                  type="button"
                  className="btn-cancel"
                  onClick={() => {
                    setShowCreatePersonDialog(false)
                    setNewPersonName('')
                  }}
                  disabled={creatingPerson}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="btn-submit"
                  disabled={!newPersonName.trim() || creatingPerson}
                >
                  {creatingPerson ? 'Creating…' : 'Create'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Edit Person Dialog */}
      {editingPerson && (
        <div
          className="modal-overlay"
          onClick={() => {
            setEditingPerson(null)
            setEditPersonName('')
          }}
        >
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <h2 className="modal-title">Rename Person</h2>
            <form
              className="modal-form"
              onSubmit={(e) => {
                e.preventDefault()
                handleSavePersonName()
              }}
            >
              <div className="form-group">
                <label htmlFor="edit-person-name" className="form-label">
                  Name
                </label>
                <input
                  id="edit-person-name"
                  type="text"
                  className="form-input"
                  value={editPersonName}
                  onChange={(e) => setEditPersonName(e.target.value)}
                  placeholder="Enter person's name"
                  autoFocus
                  disabled={renamingPerson}
                />
              </div>
              <div className="modal-actions">
                <button
                  type="button"
                  className="btn-cancel"
                  onClick={() => {
                    setEditingPerson(null)
                    setEditPersonName('')
                  }}
                  disabled={renamingPerson}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="btn-submit"
                  disabled={!editPersonName.trim() || renamingPerson}
                >
                  {renamingPerson ? 'Saving…' : 'Save'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Merge Person Dialog */}
      {mergingPerson && (
        <div
          className="modal-overlay"
          onClick={() => {
            setMergingPerson(null)
            setMergeTargetId('')
          }}
        >
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <h2 className="modal-title">Merge Person</h2>
            <div className="modal-form">
              <p style={{ marginBottom: '1rem', color: 'var(--text-muted)' }}>
                Merge "{mergingPerson.label}" ({mergingPerson.face_count} face{mergingPerson.face_count === 1 ? '' : 's'})
                into another person. All faces will be transferred and "{mergingPerson.label}" will be deleted.
              </p>
              <div className="form-group">
                <label htmlFor="merge-target" className="form-label">
                  Merge into
                </label>
                <select
                  id="merge-target"
                  className="form-input"
                  value={mergeTargetId}
                  onChange={(e) => setMergeTargetId(e.target.value)}
                  autoFocus
                >
                  <option value="">Select a person...</option>
                  {persons.items
                    .filter((p) => p.id !== mergingPerson.id)
                    .map((person) => (
                      <option key={person.id} value={person.id}>
                        {person.label} ({person.face_count} face{person.face_count === 1 ? '' : 's'})
                      </option>
                    ))}
                </select>
              </div>
              <div className="modal-actions">
                <button
                  type="button"
                  className="btn-cancel"
                  onClick={() => {
                    setMergingPerson(null)
                    setMergeTargetId('')
                  }}
                >
                  Cancel
                </button>
                <button
                  type="button"
                  className="btn-submit"
                  onClick={handleConfirmMerge}
                  disabled={!mergeTargetId}
                >
                  Merge
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {deletingPerson && (
        <div
          className="modal-overlay"
          onClick={() => setDeletingPerson(null)}
        >
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <h2 className="modal-title">Delete Person?</h2>
            <div className="modal-form">
              <p style={{ marginBottom: '1rem', color: 'var(--text-muted)' }}>
                Are you sure you want to delete "{deletingPerson.label}"?
              </p>
              <p style={{ marginBottom: '1rem', color: 'var(--text-muted)' }}>
                This will unassign all {deletingPerson.face_count} face{deletingPerson.face_count === 1 ? '' : 's'}.
                The person record will be permanently deleted.
              </p>
              <div className="modal-actions">
                <button
                  type="button"
                  className="btn-cancel"
                  onClick={() => setDeletingPerson(null)}
                >
                  Cancel
                </button>
                <button
                  type="button"
                  className="danger"
                  onClick={handleConfirmDelete}
                >
                  Delete Person
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      <SettingsModal isOpen={isSettingsOpen} onClose={() => setIsSettingsOpen(false)} />
    </div>
  )
}

export default App
