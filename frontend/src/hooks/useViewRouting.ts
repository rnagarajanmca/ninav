import { useMemo } from 'react'

export function useViewRouting(activeView: string) {
  const viewTitle = useMemo(() => {
    switch (activeView) {
      case 'all':
        return 'All Photos'
      case 'faces':
        return 'People'
      case 'favorites':
        return 'Favorites'
      case 'timeline':
        return 'Timeline'
      case 'memories':
        return 'Memories'
      default:
        return 'All Photos'
    }
  }, [activeView])

  const viewSubtitle = useMemo(() => {
    switch (activeView) {
      case 'all':
        return 'Seamlessly browse every asset in your shared folder before layering on face clusters and smart albums.'
      case 'faces':
        return 'Browse discovered people clusters and drill into the faces assigned to each person.'
      case 'favorites':
        return 'All the images you loved in one dedicated board. Favorites stay synced across sessions.'
      case 'timeline':
        return '' // No subtitle for timeline view
      case 'memories':
        return 'Smart collections curated by events, places, and people. Relive your highlights automatically.'
      default:
        return 'Feature coming soon. Keep browsing in All Photos while we finish this workspace.'
    }
  }, [activeView])

  const isFavoritesView = activeView === 'favorites'
  const isTimelineView = activeView === 'timeline'
  const showGrid = activeView === 'all' || isFavoritesView || isTimelineView
  const showFaces = activeView === 'faces'

  return {
    viewTitle,
    viewSubtitle,
    isFavoritesView,
    isTimelineView,
    showGrid,
    showFaces,
  }
}
